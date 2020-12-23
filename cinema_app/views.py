from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import ExpressionWrapper, Sum, DecimalField, F
from django.http import HttpResponseRedirect
from django.utils.timezone import now
from django.views.generic import CreateView, ListView, UpdateView, TemplateView

from cinema_app.forms import SignUpForm, HallForm, CreateSessionForm, TicketPurchaseForm
from cinema_app.models import CinemaUser, Session, Hall, Ticket
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS, ALLOWED_DAYS_BEFORE_EDITING

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


class AdminToolsView(LoginRequiredMixin, TemplateView):
    template_name = 'admin_tools.html'


class CreateHallView(LoginRequiredMixin, CreateView):
    model = Hall
    form_class = HallForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/'


class AvailableToEditHallView(LoginRequiredMixin, ListView):
    model = Hall
    template_name = 'halls_to_edit.html'
    queryset = Hall.objects.all()
    paginate_by = 10

    def get_queryset(self):
        halls_in_use = Ticket.objects.filter(
            ticket_for_session__start_datetime__gt=now() - timedelta(
                days=ALLOWED_DAYS_BEFORE_EDITING)).values_list(
            'ticket_for_session__hall__id')
        halls_to_render = Hall.objects.exclude(id__in=halls_in_use)

        return halls_to_render


class EditHallView(LoginRequiredMixin, UpdateView):
    model = Hall
    form_class = HallForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/halls_list/'

    def get_initial(self):
        if self.request.session.get('hall_color') and self.request.session.get('hall_capacity'):
            self.initial['hall_color'] = self.request.session.get('hall_color')
            self.initial['hall_capacity'] = self.request.session.get('hall_capacity')

            del self.request.session['hall_color']
            del self.request.session['hall_capacity']

        return self.initial.copy()

    def form_valid(self, form):
        hall_form = form.save(commit=False)

        halls_in_use = Ticket.objects.filter(
            ticket_for_session__start_datetime__gt=now() - timedelta(
                days=ALLOWED_DAYS_BEFORE_EDITING)).values_list(
            'ticket_for_session__hall__id', flat=True)

        if hall_form.id in halls_in_use:
            self.request.session.update(self.initial)

            msg = 'This hall is already in use'
            messages.error(self.request, msg)

            return HttpResponseRedirect('/admin_tools/halls_list/edit/{}/'.format(hall_form.id))

        hall_names = Hall.objects.exclude(id=hall_form.id).values_list('hall_color', flat=True)

        if hall_form.hall_color in hall_names:
            self.request.session.update(self.initial)

            msg = 'This name is already used for another hall'
            messages.error(self.request, msg)

            return HttpResponseRedirect('/admin_tools/halls_list/edit/{}/'.format(hall_form.id))

        hall_form.save()

        return super().form_valid(form)


class CreateSessionView(LoginRequiredMixin, CreateView):
    model = Session
    form_class = CreateSessionForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/'


class SessionListWithoutTicketsView(LoginRequiredMixin, ListView):
    model = Session
    template_name = 'no_tickets_session.html'
    paginate_by = 10

    def get_queryset(self):
        queryset = Session.objects.filter(start_datetime__gt=now() + timedelta(days=ALLOWED_DAYS_BEFORE_EDITING))
        sessions_without_tickets = [obj for obj in queryset if not obj.purchased_tickets]

        return sessions_without_tickets


class ScheduleSortingMixin:

    @staticmethod
    def schedule_sorting(query_to_sort, obj_request, sort_key, sorting_methods):
        if obj_request.GET.get(sort_key) in sorting_methods:

            if obj_request.GET[sort_key] == sorting_methods[0]:
                return query_to_sort.order_by('start_datetime', 'session_price')

            if obj_request.GET[sort_key] == sorting_methods[1]:
                return query_to_sort.order_by('-start_datetime', 'session_price')

            if obj_request.GET[sort_key] == sorting_methods[2]:
                return query_to_sort.order_by('session_price', 'start_datetime')

            if obj_request.GET[sort_key] == sorting_methods[3]:
                return query_to_sort.order_by('-session_price', 'start_datetime')

            return query_to_sort


class ScheduleTodayView(ListView, ScheduleSortingMixin):
    model = Session
    template_name = 'sessions_today.html'
    queryset = Session.objects.filter(start_datetime__contains=date.today())
    paginate_by = 10

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['sort_methods'] = SCHEDULE_SORTING_METHODS
        context.update({'form': TicketPurchaseForm})
        return context

    def get_queryset(self):
        sorting_result = self.schedule_sorting(self.queryset, self.request, 'sort', SCHEDULE_SORTING_METHODS)

        return sorting_result


class ScheduleTomorrowView(ListView, ScheduleSortingMixin):
    model = Session
    template_name = 'sessions_tomorrow.html'
    queryset = Session.objects.filter(
        start_datetime__contains=date.today() + timedelta(days=ALLOWED_DAYS_BEFORE_EDITING))
    paginate_by = 10

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['sort_methods'] = SCHEDULE_SORTING_METHODS
        context.update({'form': TicketPurchaseForm})
        return context

    def get_queryset(self):
        sorting_result = self.schedule_sorting(self.queryset, self.request, 'sort', SCHEDULE_SORTING_METHODS)

        return sorting_result


class OrderTicketView(LoginRequiredMixin, CreateView):
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

        session_id = int(self.request.GET['session'])
        session_object = Session.objects.get(id=session_id)
        hall_object = Hall.objects.get(id=session_object.hall_id)
        allowed_tickets = getattr(Hall.objects.get(id=session_object.hall_id),
                                  'hall_capacity') - session_object.purchased_tickets

        if session_object.purchased_tickets == hall_object.hall_capacity:

            msg = 'No seats left for the chosen session'
            messages.error(self.request, msg)

            if session_object.start_datetime.date() == date.today():
                return HttpResponseRedirect('/schedule_today/')

            return HttpResponseRedirect('/schedule_tomorrow/')

        if order.ordered_seats > allowed_tickets:
            self.request.session['old_value'] = order.ordered_seats

            msg = 'You can order only at least {} tickets'.format(allowed_tickets)
            messages.error(self.request, msg)

            return HttpResponseRedirect('/order_ticket/?session={}'.format(session_id))

        order.buyer = self.request.user
        order.ticket_for_session = session_object

        order.save()

        return super().form_valid(form)


class PurchasedTicketsListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'purchased_ticket_list.html'
    queryset = Ticket.objects.all().order_by('-ticket_for_session__start_datetime')
    paginate_by = 10

    def get_queryset(self):
        return self.queryset.filter(buyer=self.request.user)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)

        total_amount = self.queryset.values('ticket_for_session__session_price', 'ordered_seats').aggregate(
            total_sum=Sum(ExpressionWrapper(F('ticket_for_session__session_price') * F('ordered_seats'),
                                            output_field=DecimalField())))

        context['total_amount'] = total_amount['total_sum']

        return context
