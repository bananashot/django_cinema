import math
from datetime import date, timedelta, datetime

import pytz
from braces.views import SuperuserRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import ExpressionWrapper, Sum, DecimalField, F
from django.http import HttpResponseRedirect
from django.utils.timezone import now
from django.views.generic import CreateView, ListView, UpdateView, TemplateView

from cinema.settings import TIME_ZONE
from cinema_app.forms import SignUpForm, HallForm, CreateSessionForm, TicketPurchaseForm, EditSessionForm
from cinema_app.models import CinemaUser, Session, Hall, Ticket, Film
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS, ALLOWED_DAYS_BEFORE_EDITING, \
    BREAK_BETWEEN_FILMS_MINUTES

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


class SessionScheduleUtilityMixin:

    @staticmethod
    def schedule_sorting(query_to_sort, obj_request, sort_key, sorting_methods):

        if obj_request.GET[sort_key] == sorting_methods[0]:
            return query_to_sort.order_by('start_datetime', 'session_price')

        if obj_request.GET[sort_key] == sorting_methods[1]:
            return query_to_sort.order_by('-start_datetime', 'session_price')

        if obj_request.GET[sort_key] == sorting_methods[2]:
            return query_to_sort.order_by('session_price', 'start_datetime')

        if obj_request.GET[sort_key] == sorting_methods[3]:
            return query_to_sort.order_by('-session_price', 'start_datetime')

        return query_to_sort

    @staticmethod
    def check_session_overlap(existing_session_dict, session_to_create_dict, start_time_name, end_time_name):

        latest_start = max(existing_session_dict.get(start_time_name), session_to_create_dict.get(start_time_name))
        earliest_end = min(existing_session_dict.get(end_time_name), session_to_create_dict.get(end_time_name))

        if earliest_end >= latest_start:
            delta = math.floor((earliest_end - latest_start).seconds / 60)

            return delta

        delta = 0

        return delta


class ProductList(ListView):
    model = Session
    template_name = 'products.html'
    paginate_by = 20
    queryset = Session.objects.all()


class AdminToolsView(SuperuserRequiredMixin, TemplateView):
    template_name = 'admin_tools.html'


class CreateHallView(SuperuserRequiredMixin, CreateView):
    model = Hall
    form_class = HallForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/'

    def get_initial(self):
        if self.request.session.get('hall_color') and self.request.session.get('hall_capacity'):
            self.initial['hall_color'] = self.request.session.get('hall_color')
            self.initial['hall_capacity'] = self.request.session.get('hall_capacity')

            del self.request.session['hall_color']
            del self.request.session['hall_capacity']

        return self.initial.copy()

    def form_valid(self, form):
        hall_form = form.save(commit=False)

        hall_names = Hall.objects.values_list('hall_color', flat=True)

        if hall_form.hall_color in hall_names:
            self.request.session.update(form.cleaned_data)

            msg = 'This name is already used for another hall'
            messages.warning(self.request, msg)

            return HttpResponseRedirect('/admin_tools/create_hall/')

        return super().form_valid(form)


class AvailableToEditHallView(SuperuserRequiredMixin, ListView):
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


class EditHallView(SuperuserRequiredMixin, UpdateView):
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

        return super().form_valid(form)


class CreateSessionView(SuperuserRequiredMixin, CreateView, SessionScheduleUtilityMixin):
    model = Session
    form_class = CreateSessionForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/create_session/'

    def form_valid(self, form):
        new_session = form.save(commit=False)

        film_duration = Film.objects.get(id=new_session.film_id).schedule_minutes
        hall_for_session = form.cleaned_data['hall']

        new_session_start_date = form.cleaned_data['session_date_start']
        new_session_end_date = form.cleaned_data['session_date_end']
        new_session_start_time = form.cleaned_data['session_start_time']

        days_in_new_session = []

        """Creates a list for each day between dates in form"""
        for day in range((new_session_end_date - new_session_start_date).days + 1):
            day_obj = new_session_start_date + timedelta(days=day)
            days_in_new_session.append(day_obj)

        """Searches for possible conflicting session on each day"""
        for day in days_in_new_session:
            ids_of_conflicting_sessions = Session.objects.filter(start_datetime__date=day,
                                                                 hall=new_session.hall_id).values_list('id', flat=True)

            starting_datetime_new_session = datetime.combine(day, new_session_start_time)

            """Required for multiple creation to model and not editing of only 1 field"""
            new_session.id, new_session.pk = None, None

            if not ids_of_conflicting_sessions:
                new_session.start_datetime = starting_datetime_new_session
                new_session.save()

                msg = 'Session on {} in hall {} is created'.format(starting_datetime_new_session, hall_for_session)
                messages.success(self.request, msg)

            else:

                for session_id in ids_of_conflicting_sessions:
                    session_instance = Session.objects.get(id=session_id)

                    existing_session = {}
                    session_to_create = {}

                    ending_time_with_break = starting_datetime_new_session + timedelta(
                        minutes=film_duration + BREAK_BETWEEN_FILMS_MINUTES)

                    """Required to add timezone variable to datetime received from form"""
                    local_time = pytz.timezone(TIME_ZONE)

                    existing_session['start_datetime'] = session_instance.start_datetime
                    existing_session['end_datetime'] = session_instance.film_end_with_break
                    session_to_create['start_datetime'] = local_time.localize(starting_datetime_new_session)
                    session_to_create['end_datetime'] = local_time.localize(ending_time_with_break)

                    overlap = self.check_session_overlap(existing_session, session_to_create, 'start_datetime',
                                                         'end_datetime')

                    """Is overlap is greater than 0, then films in this hall are overlapping"""
                    if overlap:

                        msg = 'Session on {} overlapping another session in hall {} for {} minute(s)'.format(
                            starting_datetime_new_session, hall_for_session, overlap)
                        messages.warning(self.request, msg)

                    else:

                        new_session.start_datetime = starting_datetime_new_session
                        new_session.save()

                        msg = 'Session on {} in hall {} is created'.format(starting_datetime_new_session,
                                                                           hall_for_session)
                        messages.success(self.request, msg)

        return HttpResponseRedirect(self.success_url)


class SessionListWithoutTicketsView(SuperuserRequiredMixin, ListView, SessionScheduleUtilityMixin):
    model = Session
    template_name = 'no_tickets_session.html'
    paginate_by = 10

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['sort_methods'] = SCHEDULE_SORTING_METHODS
        return context

    def get_queryset(self):
        queryset = Session.objects.filter(
            start_datetime__gt=now() + timedelta(days=ALLOWED_DAYS_BEFORE_EDITING)).order_by('start_datetime')

        if self.request.GET.get('sort') in SCHEDULE_SORTING_METHODS:
            queryset = self.schedule_sorting(queryset, self.request, 'sort', SCHEDULE_SORTING_METHODS)

        sessions_without_tickets = [obj for obj in queryset if not obj.purchased_tickets]

        return sessions_without_tickets


class EditSessionView(SuperuserRequiredMixin, UpdateView, SessionScheduleUtilityMixin):
    model = Session
    form_class = EditSessionForm
    template_name = 'create_form.html'
    success_url = '/admin_tools/session_list/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_instance = context.get('session')

        context['form'].initial['session_date_start'] = session_instance.start_datetime.date()
        context['form'].initial['session_start_time'] = session_instance.start_datetime.time().strftime('%H:%M')

        return context

    def form_valid(self, form):
        session_editing = form.save(commit=False)

        film_duration = Film.objects.get(id=session_editing.film_id).schedule_minutes
        hall_for_session = form.cleaned_data['hall']

        new_session_start_date = form.cleaned_data['session_date_start']
        new_session_start_time = form.cleaned_data['session_start_time']
        starting_datetime_new_session = datetime.combine(new_session_start_date, new_session_start_time)

        ids_of_conflicting_sessions = Session.objects.filter(start_datetime__date=new_session_start_date,
                                                             hall=session_editing.hall_id).exclude(
            id=session_editing.id).values_list('id', flat=True)

        if not ids_of_conflicting_sessions:
            session_editing.start_datetime = starting_datetime_new_session
            session_editing.save()

            msg = 'Session on {} in hall {} is created'.format(starting_datetime_new_session, hall_for_session)
            messages.success(self.request, msg)

        else:

            for session_id in ids_of_conflicting_sessions:
                session_instance = Session.objects.get(id=session_id)

                existing_session = {}
                session_to_create = {}

                ending_time_with_break = starting_datetime_new_session + timedelta(
                    minutes=film_duration + BREAK_BETWEEN_FILMS_MINUTES)

                """Required to add timezone variable to datetime received from form"""
                local_time = pytz.timezone(TIME_ZONE)

                existing_session['start_datetime'] = session_instance.start_datetime
                existing_session['end_datetime'] = session_instance.film_end_with_break
                session_to_create['start_datetime'] = local_time.localize(starting_datetime_new_session)
                session_to_create['end_datetime'] = local_time.localize(ending_time_with_break)

                overlap = self.check_session_overlap(existing_session, session_to_create, 'start_datetime',
                                                     'end_datetime')

                """Is overlap is greater than 0, then films in this hall are overlapping"""
                if overlap:

                    msg = 'Session on {} overlapping another session in hall {} for {} minute(s)'.format(
                        starting_datetime_new_session, hall_for_session, overlap)
                    messages.warning(self.request, msg)

                else:

                    session_editing.start_datetime = starting_datetime_new_session
                    session_editing.save()

                    msg = 'Session on {} in hall {} is created'.format(starting_datetime_new_session,
                                                                       hall_for_session)
                    messages.success(self.request, msg)

        return HttpResponseRedirect(self.success_url)


class ScheduleTodayView(ListView, SessionScheduleUtilityMixin):
    model = Session
    template_name = 'sessions_today.html'
    queryset = Session.objects.filter(start_datetime__contains=date.today())
    paginate_by = 10

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['sort_methods'] = SCHEDULE_SORTING_METHODS
        return context

    def get_queryset(self):
        if self.request.GET.get('sort') in SCHEDULE_SORTING_METHODS:
            sorting_result = self.schedule_sorting(self.queryset, self.request, 'sort', SCHEDULE_SORTING_METHODS)
            return sorting_result

        return self.queryset


class ScheduleTomorrowView(ListView, SessionScheduleUtilityMixin):
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
        if self.request.GET.get('sort') in SCHEDULE_SORTING_METHODS:
            sorting_result = self.schedule_sorting(self.queryset, self.request, 'sort', SCHEDULE_SORTING_METHODS)
            return sorting_result

        return self.queryset


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
        allowed_tickets = Hall.objects.get(id=session_object.hall_id).hall_capacity - session_object.purchased_tickets

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
    paginate_by = 10

    def get_queryset(self):
        queryset = Ticket.objects.filter(buyer=self.request.user).order_by('-ticket_for_session__start_datetime')
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)

        total_amount = self.get_queryset().values('ticket_for_session__session_price', 'ordered_seats').aggregate(
            total_sum=Sum(ExpressionWrapper(F('ticket_for_session__session_price') * F('ordered_seats'),
                                            output_field=DecimalField())))

        context['total_amount'] = total_amount['total_sum']

        return context
