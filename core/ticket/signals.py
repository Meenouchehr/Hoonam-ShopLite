from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from django.utils.translation import gettext as _
import os

from ticket.serializers import *


@receiver(pre_save, sender=TicketModel)
def pre_save_ticket(sender, instance, *args, **kwargs):
    if instance.id:
        instance.old_status = instance.__class__.objects.get(id=instance.id).status


@receiver(post_save, sender=TicketModel)
def post_save_ticket(sender, instance=None, created=False, **kwargs):
    if instance.kind == "responder":
        if created or (
            hasattr(instance, "old_status") and (instance.old_status != instance.status)
        ):
            _parent = instance.parent
            if _parent:
                _parent.status = instance.status
                _parent.save()
