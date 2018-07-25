from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem


class Melding(models.Model):
    lokatie_plaats = models.CharField(max_length=100)
    lokatie_postcode = models.CharField(max_length=7)
    lokatie_huisnummer = models.CharField(max_length=10)
    lokatie_huisnummer_toevoeging = models.CharField(max_length=20, blank=True)

    onderwerp = models.CharField(max_length=200)
    toelichting = models.TextField(blank=True)

    created = models.DateTimeField(auto_now_add=True)
    completed = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('vergunningsaanvraag')
        verbose_name_plural = _('vergunningsaanvragen')
        ordering = ['-created']

    def get_lokatie_display(self):
        return '{} {} {}, {}'.format(
            self.lokatie_postcode,
            self.lokatie_huisnummer,
            self.lokatie_huisnummer_toevoeging,
            self.lokatie_plaats,
        )

    def save(self, *args, **kwargs):
        if self.pk and self.zaakstatus in [ZaakStatus.toegewezen, ZaakStatus.afgewezen]:
            self.completed = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.pk)