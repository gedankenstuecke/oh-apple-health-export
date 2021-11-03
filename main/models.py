from django.db import models
import uuid
from openhumans.models import OpenHumansMember

ENDPOINT_TOKEN_LEN = 10


def generate_endpoint_token():
    return str(uuid.uuid1())


class AppleHealthUser(models.Model):
    oh_member = models.OneToOneField(OpenHumansMember,
                                     on_delete=models.CASCADE)
    endpoint_token = models.CharField(max_length=36,
                                      unique=True,
                                      default=generate_endpoint_token)
