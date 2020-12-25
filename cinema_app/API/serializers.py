from django.db.models import Sum, ExpressionWrapper, DecimalField, F
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from cinema_app.models import CinemaUser, Hall, Film, Session, Ticket
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS


class UserSerializer(ModelSerializer):
    class Meta:
        model = CinemaUser
        fields = [
            'username',
            'first_name',
            'last_name',
        ]


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
    sorting_methods = serializers.SerializerMethodField()

    def get_sorting_methods(self, instance):

        if not self.context.get('sorting_methods'):
            sorting_args = []

            for method in SCHEDULE_SORTING_METHODS:
                sorting_args.append('?sort={}'.format(method))

            self.context['sorting_methods'] = sorting_args

        return self.context.get('sorting_methods')

    class Meta:
        model = Session
        fields = [
            'id',
            'session_price',
            'start_datetime',
            'film',
            'hall',
            'sorting_methods',
        ]


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
