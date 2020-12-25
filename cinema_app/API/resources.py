import copy
import math
from datetime import date, timedelta, datetime

import pytz
from django.db.models import Sum, ExpressionWrapper, F, DecimalField
from django.utils import timezone
from django.utils.timezone import now
from rest_framework import serializers, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from cinema.settings import TIME_ZONE, DATE_INPUT_FORMATS
from cinema_app.API.serializers import UserSerializer, TicketSerializer, SessionSerializer, FilmSerializer, \
    HallSerializer, SessionCreateSerializer, SessionEditSerializer
from cinema_app.models import CinemaUser, Ticket, Film, Session, Hall
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS, ALLOWED_DAYS_BEFORE_EDITING, \
    BREAK_BETWEEN_FILMS_MINUTES


class SessionScheduleUtilityAPIMixin:

    @staticmethod
    def schedule_sorting(query_to_sort, current_sorting_value, sorting_methods):

        if current_sorting_value == sorting_methods[0]:
            return query_to_sort.order_by('start_datetime', 'session_price')

        if current_sorting_value == sorting_methods[1]:
            return query_to_sort.order_by('-start_datetime', 'session_price')

        if current_sorting_value == sorting_methods[2]:
            return query_to_sort.order_by('session_price', 'start_datetime')

        if current_sorting_value == sorting_methods[3]:
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


class UserViewSet(ModelViewSet):
    queryset = CinemaUser.objects.all()
    serializer_class = UserSerializer
    http_method_names = ['post']

    def perform_create(self, serializer):
        del serializer.validated_data['password2']

        serializer.save()


class HallViewSet(ModelViewSet):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    http_method_names = ['get', 'post', 'patch']
    permission_classes = [IsAuthenticated,
                          IsAdminUser,
                          ]

    def perform_create(self, serializer):
        hall_names = Hall.objects.values_list('hall_color', flat=True)

        if serializer.validated_data['hall_color'] in hall_names:
            msg = 'This name is already used for another hall'
            raise serializers.ValidationError({"hall_color": [msg]})

        serializer.save()

    def perform_update(self, serializer):
        pk = int(self.kwargs['pk'])
        hall_names = Hall.objects.exclude(id=pk).values_list('hall_color', flat=True)

        if serializer.validated_data['hall_color'] in hall_names:
            msg = 'This name is already used for another hall'
            raise serializers.ValidationError({"hall_color": [msg]})

        halls_in_use = Ticket.objects.filter(
            ticket_for_session__start_datetime__gt=now() - timedelta(days=ALLOWED_DAYS_BEFORE_EDITING)).values_list(
            'ticket_for_session__hall__id', flat=True)

        if pk in halls_in_use:
            msg = 'This hall is already in use'
            raise serializers.ValidationError({"hall_color": [msg]})

        serializer.save()


class FilmViewSet(ModelViewSet):
    queryset = Film.objects.all()
    serializer_class = FilmSerializer
    http_method_names = ['get']


class SessionViewSet(ModelViewSet, SessionScheduleUtilityAPIMixin):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    http_method_names = ['get', 'post', 'patch']
    permission_classes = [IsAuthenticated,
                          IsAdminUser,
                          ]

    def get_serializer_class(self):

        if self.action == "create":
            return SessionCreateSerializer
        if self.action == "update":
            return SessionEditSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        new_session_data = serializer.validated_data

        film_id = new_session_data['film'].id

        try:
            Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            msg = 'There is no film with this id'
            raise serializers.ValidationError({"film_id": msg})

        hall_id = new_session_data['hall'].id

        try:
            Film.objects.get(id=hall_id)
        except Film.DoesNotExist:
            msg = 'There is no hall with this id'
            raise serializers.ValidationError({"hall_id": msg})

        days_in_new_session = []
        start_date = copy.deepcopy(new_session_data['start_date'])
        end_date = copy.deepcopy(new_session_data['end_date'])
        start_time = copy.deepcopy(new_session_data['start_time'])

        del new_session_data['start_date']
        del new_session_data['end_date']
        del new_session_data['start_time']

        messages = []

        hall_name = Hall.objects.get(id=hall_id).hall_color
        film_duration = Film.objects.get(id=film_id).film_duration_minutes

        """Creates a list for each day between dates in form"""
        for day in range((end_date - start_date).days + 1):
            day_obj = start_date + timedelta(days=day)
            days_in_new_session.append(day_obj)

        """Searches for possible conflicting session on each day"""
        for day in days_in_new_session:
            ids_of_conflicting_sessions = Session.objects.filter(start_datetime__date=day, hall=hall_id
                                                                 ).order_by('start_datetime'
                                                                            ).values_list('id', flat=True)

            starting_datetime_new_session = datetime.combine(day, start_time)

            """Required for multiple creation to model and not editing of only 1 field"""
            new_session_data['id'], new_session_data['pk'] = None, None

            if not ids_of_conflicting_sessions:
                new_session_data['start_datetime'] = starting_datetime_new_session

                serializer.save()

                msg = {"created": True, "Start_date": starting_datetime_new_session, "Hall": hall_name,
                       "Overlap_minutes": 0}
                messages.append(msg)

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

                        msg = {"created": False, "Start_date": starting_datetime_new_session, "Hall": hall_name,
                               "Overlap_minutes": overlap}
                        messages.append(msg)

                    else:

                        new_session_data['start_datetime'] = starting_datetime_new_session
                        serializer.save()

                        msg = {"created": True, "Start_date": starting_datetime_new_session, "Hall": hall_name,
                               "Overlap_minutes": overlap}
                        messages.append(msg)

        message_dict = dict(enumerate(message for message in messages))
        self.kwargs['messages'] = message_dict

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.kwargs.get('messages'), status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        new_session_data = serializer.validated_data

        film_id = new_session_data['film'].id

        try:
            Film.objects.get(id=film_id)
        except Film.DoesNotExist:
            msg = 'There is no film with this id'
            raise serializers.ValidationError({"film_id": msg})

        hall_id = new_session_data['hall'].id

        try:
            Film.objects.get(id=hall_id)
        except Film.DoesNotExist:
            msg = 'There is no hall with this id'
            raise serializers.ValidationError({"hall_id": msg})

        edit_session_id = self.kwargs['pk']

        try:
            Session.objects.filter(
                start_datetime__date__gt=date.today() + timedelta(days=ALLOWED_DAYS_BEFORE_EDITING)).get(
                id=edit_session_id)
        except Session.DoesNotExist:
            msg = 'There is no session with this id or this session has already started'
            raise serializers.ValidationError({"hall_id": msg})

        start_date = datetime.strptime(serializer.initial_data['start_date'], DATE_INPUT_FORMATS)
        start_time = datetime.strptime(serializer.initial_data['start_time'], '%H:%M').time()

        hall_name = Hall.objects.get(id=hall_id).hall_color
        film_duration = Film.objects.get(id=film_id).film_duration_minutes

        ids_of_conflicting_sessions = Session.objects.filter(start_datetime__date=start_date,
                                                             hall=hall_id).exclude(id=edit_session_id).values_list('id',
                                                                                                                   flat=True)

        starting_datetime_new_session = datetime.combine(start_date, start_time)

        if not ids_of_conflicting_sessions:
            new_session_data['start_datetime'] = starting_datetime_new_session

            serializer.save()

            msg = {"updated": True, "Start_date": starting_datetime_new_session, "Hall": hall_name,
                   "Overlap_minutes": 0}
            return Response(msg)

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

                    msg = {"updated": False, "Start_date": starting_datetime_new_session, "Hall": hall_name,
                           "Overlap_minutes": overlap}
                    return Response(msg)

                else:

                    new_session_data['start_datetime'] = starting_datetime_new_session
                    serializer.save()

                    msg = {"updated": True, "Start_date": starting_datetime_new_session, "Hall": hall_name,
                           "Overlap_minutes": overlap}
                    return Response(msg)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)


class ScheduleTodayView(ModelViewSet, SessionScheduleUtilityAPIMixin):
    queryset = Session.objects.filter(start_datetime__date=date.today())
    serializer_class = SessionSerializer
    http_method_names = ['get']

    def get_queryset(self):
        sorting = self.request.query_params.get('sort')

        if sorting and (sorting in SCHEDULE_SORTING_METHODS):
            sorted_queryset = self.schedule_sorting(self.queryset, sorting, SCHEDULE_SORTING_METHODS)
            return sorted_queryset

        return self.queryset


class ScheduleTomorrowView(ModelViewSet, SessionScheduleUtilityAPIMixin):
    queryset = Session.objects.filter(start_datetime__date=date.today() + timedelta(days=1))
    serializer_class = SessionSerializer
    http_method_names = ['get']

    def get_queryset(self):
        sorting = self.request.query_params.get('sort')

        if sorting and (sorting in SCHEDULE_SORTING_METHODS):
            sorted_queryset = self.schedule_sorting(self.queryset, sorting, SCHEDULE_SORTING_METHODS)
            return sorted_queryset

        return self.queryset


class TicketViewSet(ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    http_method_names = ['get', 'post']
    permission_classes = [IsAuthenticated,
                          ]

    def get_queryset(self):
        user = self.request.user
        return Ticket.objects.filter(buyer_id=user.id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        total = Ticket.objects.filter(buyer=self.request.user).aggregate(total_sum=Sum(
            ExpressionWrapper(F('ticket_for_session__session_price') * F('ordered_seats'),
                              output_field=DecimalField()
                              )))
        context['total'] = total.get('total_sum')
        return context

    def perform_create(self, serializer):
        session_object = serializer.validated_data.get('ticket_for_session')

        if session_object.start_datetime < timezone.now():
            msg = "The start of this session has already happened"
            raise serializers.ValidationError({"ticket_for_session": msg})

        sessions_today = Session.objects.filter(start_datetime__date=date.today()).values_list('id', flat=True)
        sessions_tomorrow = Session.objects.filter(start_datetime__date=date.today() + timedelta(days=1)).values_list(
            'id', flat=True)
        allowed_session_ids = list(sessions_today) + list(sessions_tomorrow)

        if session_object.id not in allowed_session_ids:
            msg = "This session is not in today or tomorrow schedule, choose from {}".format(allowed_session_ids)
            raise serializers.ValidationError({"ticket_for_session": msg})

        hall_object = Hall.objects.get(id=session_object.hall_id)

        if session_object.purchased_tickets == hall_object.hall_capacity:
            msg = 'No seats left for the chosen session'
            raise serializers.ValidationError(msg)

        allowed_tickets = Hall.objects.get(id=session_object.hall_id).hall_capacity - session_object.purchased_tickets

        if serializer.validated_data.get('ordered_seats') > allowed_tickets:
            msg = 'You can order only at least {} tickets'.format(allowed_tickets)
            raise serializers.ValidationError({"ordered_seats": [msg]})

        serializer.validated_data['buyer'] = self.request.user
        serializer.save()
