from django.contrib.auth import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from cinema import settings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


@receiver(user_logged_in)
def admin_unlimited_session(sender, user, request, **kwargs):
    if user.is_superuser:
        request.session.set_expiry(0)
