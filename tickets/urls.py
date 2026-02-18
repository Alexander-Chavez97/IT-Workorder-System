"""
tickets/urls.py
===============
URL patterns for the tickets app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Employee-facing
    path("",                        views.submit_ticket,    name="submit_ticket"),
    path("success/<str:ticket_id>/",views.ticket_success,   name="ticket_success"),

    # AJAX live routing endpoint
    path("api/route/",              views.live_route,        name="live_route"),

    # Admin
    path("admin-queue/",            views.admin_queue,       name="admin_queue"),
    path("ticket/<str:ticket_id>/", views.ticket_detail,     name="ticket_detail"),
    path("routing-reference/",      views.routing_reference, name="routing_reference"),
]
