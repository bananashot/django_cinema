from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from cinema_app.schedule_settings import SCHEDULE_DIVIDE_MULTIPLIER, BREAK_BETWEEN_FILMS_MINUTES


class CinemaUser(AbstractUser):

    def __str__(self):
        return self.username


class Film(models.Model):
    film_name = models.CharField(max_length=120, blank=False)
    film_description = models.TextField(blank=False, default='New film description')
    film_duration_minutes = models.PositiveIntegerField(blank=False, validators=[MinValueValidator(1)])

    @property
    def schedule_minutes(self):
        film_hours = self.film_duration_minutes // 60
        film_minutes = self.film_duration_minutes % 60
        temp_minute_result = 0
        schedule_mult = SCHEDULE_DIVIDE_MULTIPLIER

        if film_minutes:
            if film_minutes > schedule_mult * round(film_minutes / schedule_mult):
                temp_minute_result = schedule_mult * round(film_minutes / schedule_mult) + schedule_mult
            else:
                temp_minute_result = schedule_mult * round(film_minutes / schedule_mult)

        if film_hours:
            return film_hours * 60 + temp_minute_result
        else:
            return temp_minute_result

    def __str__(self):
        return self.film_name


class Hall(models.Model):
    hall_color = models.CharField(max_length=120, blank=False)
    hall_capacity = models.PositiveIntegerField(blank=False, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.hall_color


class Session(models.Model):
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE)
    session_price = models.DecimalField(blank=False, decimal_places=2, max_digits=12,
                                        validators=[MinValueValidator(0.01)])
    start_datetime = models.DateTimeField(blank=False)

    @property
    def end_datetime(self):
        return self.start_datetime + timedelta(minutes=self.film.schedule_minutes)

    @property
    def film_end_with_break(self):
        return self.end_datetime + timedelta(minutes=BREAK_BETWEEN_FILMS_MINUTES)

    @property
    def purchased_tickets(self):
        list_of_purchased_tickets = Ticket.objects.filter(ticket_for_session_id=self.id).values_list('ordered_seats',
                                                                                                     flat=True)
        return sum(list_of_purchased_tickets)

    def __str__(self):
        return '%s - %s - %s' % (self.film.film_name, self.start_datetime, self.purchased_tickets)


class Ticket(models.Model):
    buyer = models.ForeignKey(CinemaUser, on_delete=models.CASCADE)
    ticket_for_session = models.ForeignKey(Session, on_delete=models.CASCADE)
    ordered_seats = models.PositiveIntegerField(blank=False, validators=[MinValueValidator(1)])

    def __str__(self):
        return '%s - %s' % (self.ticket_for_session.film.film_name, self.ticket_for_session.start_datetime)

