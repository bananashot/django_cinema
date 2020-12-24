from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from cinema_app.models import CinemaUser, Hall, Film, Session, Ticket
from cinema_app.schedule_settings import SCHEDULE_SORTING_METHODS


class UserSerializer(ModelSerializer):
    class Meta:
        model = CinemaUser
        fields = ['username', 'first_name', 'last_name']


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
    class Meta:
        model = Session
        fields = '__all__'


class TicketSerializer(ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'ticket_for_session',
            'ordered_seats',
            'buyer',
        ]

    def validate_ordered_seats(self, attrs):
        if attrs < 1:
            raise serializers.ValidationError('You need to order at least 1 ticket')

        return attrs
