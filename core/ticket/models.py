from django.db import models
from django.conf import settings

# Create your models here.

TICKET_STATUS_CHOICE = (
    ("wait", "wait"),
    ("review", "review"),
    ("done", "done"),
)


class MultiImageModel(models.Model):

    ticket = models.ForeignKey(
        "TicketModel", on_delete=models.CASCADE, related_name="ticket_image", null=True
    )
    image = models.ImageField(upload_to="images/")
    # status = models.SmallIntegerField(choices=STATUS_CHOICE, default=1)
    # name    = models.CharField(max_length=255)
    # default = models.BooleanField(default=False)
    class Meta:
        db_table = "tbl_multiimage"
        managed = True
        verbose_name = "ticket_image"
        verbose_name_plural = "ticket_images"
        ordering = ["-id"]


class TicketModel(models.Model):
    KIND_CHOICE = (
        ("actor", "actor"),
        ("responder", "responder"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    subject = models.CharField(max_length=130, blank=True)
    content = models.TextField(blank=True)
    date = models.DateTimeField(auto_now=True)
    kind = models.CharField(choices=KIND_CHOICE, max_length=10, default="actor")
    is_refrence = models.BooleanField(default=False)
    refrence = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_refrence",
        null=True,
    )
    refrence_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_refrence_by",
        null=True,
    )
    parent = models.ForeignKey(
        "TicketModel", on_delete=models.CASCADE, related_name="subtickets", null=True
    )
    status = models.CharField(
        choices=TICKET_STATUS_CHOICE, max_length=6, default="wait"
    )

    class Meta:
        db_table = "tbl_ticket"
        managed = True
        verbose_name = "ticket"
        verbose_name_plural = "tickets"
        ordering = ["-id"]


class TicketStatusModel(models.Model):
    ticket = models.ForeignKey(
        "TicketModel", on_delete=models.CASCADE, related_name="ticket_status"
    )
    status = models.CharField(choices=TICKET_STATUS_CHOICE, max_length=6)
    date = models.DateTimeField(auto_now=True)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_operator",
        null=True,
    )

    class Meta:
        db_table = "tbl_ticket_status"
        managed = True
        verbose_name = "ticket_status"
        verbose_name_plural = "ticket_status"
