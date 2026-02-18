"""
tickets/admin.py
================
Registers the Ticket model with Django's built-in admin interface,
providing a fallback management UI out of the box.
"""

from django.contrib import admin
from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_id", "department", "routing_tier", "category",
        "title", "routing_effective_priority", "routing_team",
        "routing_sla", "status", "submitted_at",
    ]
    list_filter  = ["status", "routing_tier", "routing_effective_priority", "department"]
    search_fields = ["ticket_id", "name", "title", "department"]
    readonly_fields = [
        "ticket_id", "routing_tier", "routing_tier_label", "routing_team",
        "routing_sla", "routing_effective_priority", "routing_was_modified",
        "routing_reasons", "routing_escalation_path", "submitted_at", "updated_at",
    ]

    fieldsets = [
        ("Ticket Identity",   {"fields": ["ticket_id", "status"]}),
        ("Requestor",         {"fields": ["name", "employee_id", "department", "email"]}),
        ("Issue Details",     {"fields": ["category", "subtype", "title", "description", "asset_tag", "location", "phone_ext"]}),
        ("Priority",          {"fields": ["user_priority"]}),
        ("Routing Decision",  {"fields": [
            "routing_tier", "routing_tier_label", "routing_team",
            "routing_sla", "routing_effective_priority",
            "routing_was_modified", "routing_reasons", "routing_escalation_path",
        ]}),
        ("Timestamps",        {"fields": ["submitted_at", "updated_at"]}),
    ]
