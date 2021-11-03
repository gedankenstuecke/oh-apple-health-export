from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import AppleHealthUser


@receiver(user_logged_in)
def create_applehealth_user(sender, request, user, **kwargs):
    AppleHealthUser.objects.get_or_create(oh_member=user.openhumansmember)
