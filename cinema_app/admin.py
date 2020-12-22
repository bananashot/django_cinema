from django.contrib import admin

from cinema_app.models import CinemaUser, Film, Hall, Session, Ticket

admin.site.register(CinemaUser)
admin.site.register(Film)
admin.site.register(Hall)
admin.site.register(Session)
admin.site.register(Ticket)
