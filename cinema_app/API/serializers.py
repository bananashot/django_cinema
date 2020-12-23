from rest_framework.serializers import ModelSerializer

from cinema_app.models import CinemaUser, Hall, Film, Session, Ticket


class UserSerializer(ModelSerializer):
    class Meta:
        model = CinemaUser
        fields = ['username', 'first_name', 'last_name']


class HallSerializer(ModelSerializer):
    class Meta:
        model = Hall
        fields = '__all__'


class FilmSerializer(ModelSerializer):
    class Meta:
        model = Film
        fields = '__all__'


class SessionSerializer(ModelSerializer):
    class Meta:
        model = Session
        fields = '__all__'


class TicketSerializer(ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
