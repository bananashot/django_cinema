from datetime import date, timedelta

from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView, ListView

from cinema_app.forms import SignUpForm, CreateHallForm, CreateSessionForm
from cinema_app.models import CinemaUser, Session, Hall

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
    form_class = CreateHallForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/'


class AvailableToEditHallView(ListView):
    model = Hall
    template_name = 'halls_to_edit.html'
    paginate_by = 10

    def get_queryset(self):
        halls_in_use = Ticket


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
    queryset = Session.objects.filter(start_datetime__contains=date.today()+timedelta(days=1))
    paginate_by = 10
