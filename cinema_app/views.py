from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import ExpressionWrapper, Sum, DecimalField, F
from django.http import HttpResponseRedirect
from django.utils.timezone import now
from django.views.generic import CreateView, ListView, UpdateView

from cinema_app.forms import SignUpForm, HallForm, CreateSessionForm, TicketPurchaseForm
from cinema_app.models import CinemaUser, Session, Hall, Ticket
from cinema_app.schedule_settings import EDITING_HOURS_UNTIL_SESSION

User = get_user_model()


class Registration(CreateView):
    model = CinemaUser
    form_class = SignUpForm
    template_name = 'registration.html'
    success_url = '/'


class Login(LoginView):
    template_name = 'login.html'


class Logout(LoginRequiredMixin, LogoutView):

    def get(self, request, *args, **kwargs):
        logout(request.user)
        return super().get(request, *args, **kwargs)


class ProductList(ListView):
    model = Session
    template_name = 'products.html'
    paginate_by = 5
    queryset = Session.objects.all()

    # def get_context_data(self, *, object_list=None, **kwargs):
    #     context = super().get_context_data(object_list=object_list, **kwargs)
    #     context.update({'form': PurchaseForm})
    #     return context


class CreateHallView(CreateView):
    model = Hall
    form_class = HallForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/'


class AvailableToEditHallView(ListView):
    model = Hall
    template_name = 'halls_to_edit.html'
    queryset = Hall.objects.all()
    paginate_by = 10

    def get_queryset(self):
        halls_in_use = Ticket.objects.filter(
            ticket_for_session__start_datetime__gt=now() + timedelta(hours=EDITING_HOURS_UNTIL_SESSION)).values_list(
            'ticket_for_session__hall__id')
        halls_to_render = Hall.objects.exclude(id__in=halls_in_use)

        return halls_to_render


class EditHallView(UpdateView):
    model = Hall
    form_class = HallForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/halls_list/'


class CreateSessionView(CreateView):
    model = Session
    form_class = CreateSessionForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/'


class ScheduleTodayView(ListView):
    model = Session
    template_name = 'sessions_today.html'
    queryset = Session.objects.filter(start_datetime__contains=date.today())
    paginate_by = 10

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update({'form': TicketPurchaseForm})
        return context


class ScheduleTomorrowView(ListView):
    model = Session
    template_name = 'sessions_tomorrow.html'
    queryset = Session.objects.filter(start_datetime__contains=date.today() + timedelta(days=1))
    paginate_by = 10

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context.update({'form': TicketPurchaseForm})
        return context


class OrderTicketView(CreateView):
    model = Ticket
    form_class = TicketPurchaseForm
    template_name = 'order_ticket.html'
    success_url = '/order_history/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_id = int(self.request.GET['session'])
        session_object = Session.objects.get(id=session_id)

        context['film'] = session_object.film.film_name
        context['description'] = session_object.film.film_description
        context['start'] = session_object.start_datetime
        context['price'] = session_object.session_price

        return context

    def get_initial(self):
        if self.request.session.get('old_value'):
            self.initial['ordered_seats'] = self.request.session.get('old_value')
            del self.request.session['old_value']

        return self.initial.copy()

    def form_valid(self, form):
        order = form.save(commit=False)

        self.request.session['old_value'] = order.ordered_seats

        session_id = int(self.request.GET['session'])
        session_object = Session.objects.get(id=session_id)
        allowed_tickets = getattr(Hall.objects.get(id=session_object.hall_id),
                                  'hall_capacity') - session_object.purchased_tickets

        if order.ordered_seats > allowed_tickets:
            msg = 'You can order only at least {} tickets'.format(allowed_tickets)
            messages.error(self.request, msg)

            return HttpResponseRedirect('/order_ticket/?session={}'.format(session_id))

        order.buyer = self.request.user
        order.ticket_for_session = session_object

        order.save()

        return super().form_valid(form)


class PurchasedTicketsListView(ListView):
    model = Ticket
    template_name = 'purchased_ticket_list.html'
    queryset = Ticket.objects.all()
    paginate_by = 10

    def get_queryset(self):
        return Ticket.objects.filter(buyer=self.request.user)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)

        total_amount = self.queryset.values('ticket_for_session__session_price', 'ordered_seats').aggregate(
            total_sum=Sum(ExpressionWrapper(F('ticket_for_session__session_price') * F('ordered_seats'),
                                            output_field=DecimalField())))

        context['total_amount'] = total_amount['total_sum']

        return context
