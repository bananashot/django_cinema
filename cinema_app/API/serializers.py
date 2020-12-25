from datetime import date, timedelta

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from cinema_app.models import CinemaUser, Hall, Film, Session, Ticket
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS, ALLOWED_DAYS_BEFORE_EDITING


class UserSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CinemaUser
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
            'password2',
        ]

    def validate(self, attrs):
        add_attrs = super().validate(attrs)
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Passwords are not equal."})

        return add_attrs


class HallSerializer(ModelSerializer):
    class Meta:
        model = Hall
        fields = '__all__'

    def validate_hall_color(self, attrs):
        if not attrs.isalpha():
            raise serializers.ValidationError("Use only letters")

        return attrs


class FilmSerializer(ModelSerializer):
    class Meta:
        model = Film
        fields = '__all__'


class SessionSerializer(ModelSerializer):
    sorting_methods = serializers.SerializerMethodField(read_only=True)
    available_tickets = serializers.SerializerMethodField(read_only=True)

    def get_sorting_methods(self, instance):

        if not self.context.get('sorting_methods'):
            sorting_args = []

            for method in SCHEDULE_SORTING_METHODS:
                sorting_args.append('?sort={}'.format(method))

            self.context['sorting_methods'] = sorting_args

        return self.context.get('sorting_methods')

    def get_available_tickets(self, instance):

        current_session = instance
        available_tickets = Hall.objects.get(
            id=current_session.hall_id).hall_capacity - current_session.purchased_tickets

        return available_tickets

    class Meta:
        model = Session
        fields = [
            'id',
            'session_price',
            'start_datetime',
            'film',
            'hall',
            'available_tickets',
            'sorting_methods',
        ]


class SessionCreateSerializer(ModelSerializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True, format='%h:%m')

    class Meta:
        model = Session
        fields = [
            'film',
            'hall',
            'session_price',
            'start_date',
            'end_date',
            'start_time',
        ]

    def validate_start_date(self, start_date):
        edit = (date.today() + timedelta(days=ALLOWED_DAYS_BEFORE_EDITING))
        if start_date < edit:
            msg = 'You can create or edit sessions only {} day(s) beforehand'.format(ALLOWED_DAYS_BEFORE_EDITING)
            raise serializers.ValidationError(msg)
        return start_date

    def validate(self, attrs):
        add_attrs = super().validate()
        start_date = attrs['start_date']
        end_date = attrs['end_date']

        if end_date < start_date:
            msg = 'Session end date should be the same as a start date or later'
            raise serializers.ValidationError({"end_date": msg})

        return add_attrs


class SessionEditSerializer(ModelSerializer):
    start_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True, format='%h:%m')

    class Meta:
        model = Session
        fields = [
            'film',
            'hall',
            'session_price',
            'start_date',
            'start_time',
        ]

    def validate_start_date(self, start_date):
        edit = (date.today() + timedelta(days=ALLOWED_DAYS_BEFORE_EDITING))
        if start_date < edit:
            msg = 'You can create or edit sessions only {} day(s) beforehand'.format(ALLOWED_DAYS_BEFORE_EDITING)
            raise serializers.ValidationError(msg)
        return start_date


class TicketSerializer(ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(read_only=True)
    account_total = serializers.SerializerMethodField()

    def get_account_total(self, instance):
        spent_total = self.context['total']
        return spent_total

    class Meta:
        model = Ticket
        fields = [
            'ticket_for_session',
            'ordered_seats',
            'buyer',
            'account_total',
        ]

    def validate_ordered_seats(self, attrs):
        if attrs < 1:
            raise serializers.ValidationError('You need to order at least 1 ticket')

        return attrs
