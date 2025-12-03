import uuid

from django.db import models


class BaseModel(models.Model):
    """
    Base model
    """

    # default values for secure parameter management
    _secure_parameter_prefix = ""
    _secure_parameters: list[str] = []

    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
