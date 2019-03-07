import json

from django.db import models
from django.utils import timezone


class Notification(models.Model):
    topic = models.CharField(max_length=200)
    message = models.TextField(blank=True)

    read = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-created', )

    def json(self):
        return json.loads(self.message)
