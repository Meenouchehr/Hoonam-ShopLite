from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ticket.viewsets import *

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r"ticket", TicketViewSet)


api_urls = [
    path("", include(router.urls)),
]
