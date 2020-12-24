from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from cinema_app.API.serializers import UserSerializer, TicketSerializer, SessionSerializer, FilmSerializer, \
    HallSerializer
from cinema_app.models import CinemaUser, Ticket, Film, Session, Hall


class UserViewSet(ModelViewSet):
    queryset = CinemaUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated,
                          IsAdminUser
                          ]


class HallViewSet(ModelViewSet):
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    http_method_names = ['get', 'post']
    permission_classes = [IsAuthenticated,
                          ]

    def create(self, request, *args, **kwargs):
        response = super().create(request)

        return response


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
    http_method_names = ['get', 'post']
    permission_classes = [IsAuthenticated,
                          ]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Ticket.objects.all()
        return Ticket.objects.filter(id=user.id)



    def perform_create(self, serializer):
        serializer.validated_data['buyer'] = self.request.user
        serializer.save()
