from django.db.models.signals import post_save
from django.dispatch import receiver


# @receiver(post_save, sender=VergunningsAanvraag)
# def create_dummy_aanvraag(sender, instance, **kwargs):
#     if instance.zaakstatus in [ZaakStatus.toegewezen, ZaakStatus.afgewezen]:
#         VergunningsAanvraagFactory.create()