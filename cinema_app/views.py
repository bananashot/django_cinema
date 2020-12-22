from datetime import date, timedelta

from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.utils.timezone import now
from django.views.generic import CreateView, ListView, UpdateView

from cinema_app.forms import SignUpForm, HallForm, CreateSessionForm
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


class ScheduleTomorrowView(ListView):
    model = Session
    template_name = 'sessions_tomorrow.html'
    queryset = Session.objects.filter(start_datetime__contains=date.today() + timedelta(days=1))
    paginate_by = 10
