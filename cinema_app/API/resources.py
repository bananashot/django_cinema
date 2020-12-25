import math
from datetime import date, timedelta

from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from cinema_app.API.serializers import UserSerializer, TicketSerializer, SessionSerializer, FilmSerializer, \
    HallSerializer
from cinema_app.models import CinemaUser, Ticket, Film, Session, Hall
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS, ALLOWED_DAYS_BEFORE_EDITING


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
    permission_classes = [IsAuthenticated,
                          IsAdminUser
                          ]


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


class SessionViewSet(ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    http_method_names = ['get']


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

    def get_object(self):
        obj = super().get_object()
        return obj

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Ticket.objects.all()
        return Ticket.objects.filter(id=user.id)

    def perform_create(self, serializer):
        session_object = serializer.validated_data.get('ticket_for_session')
        hall_object = Hall.objects.get(id=session_object.hall_id)
        allowed_tickets = Hall.objects.get(id=session_object.hall_id).hall_capacity - session_object.purchased_tickets

        if session_object.purchased_tickets == hall_object.hall_capacity:
            msg = 'No seats left for the chosen session'
            raise serializers.ValidationError(msg)

        if serializer.validated_data.get('ordered_seats') > allowed_tickets:
            msg = 'You can order only at least {} tickets'.format(allowed_tickets)
            raise serializers.ValidationError({"ordered_seats": [msg]})

        serializer.validated_data['buyer'] = self.request.user
        serializer.save()
