from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from cinema_app.API.serializers import UserSerializer, TicketSerializer, SessionSerializer, FilmSerializer, \
    HallSerializer
from cinema_app.models import CinemaUser, Ticket, Film, Session, Hall


class UserViewSet(ModelViewSet):
    queryset = CinemaUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated,
                          ]


class HallViewSet(ModelViewSet):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    http_method_names = ['get']
    permission_classes = [permissions.IsAuthenticated,
                          ]


class FilmViewSet(ModelViewSet):
    queryset = Film.objects.all()
    serializer_class = FilmSerializer
    http_method_names = ['get']


class SessionViewSet(ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    http_method_names = ['get']


class TicketViewSet(ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated,
                          ]
