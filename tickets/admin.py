from django.contrib import admin
from .models import Employee, Ticket


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display  = ["employee_id", "full_name", "department", "email", "is_active", "created_at"]
    list_filter   = ["department", "is_active"]
    search_fields = ["employee_id", "first_name", "last_name", "email"]
    readonly_fields = ["created_at"]
    fields = ["employee_id", "first_name", "last_name", "email", "department", "is_active", "created_at"]

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "Name"


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_id", "department", "routing_tier", "category",
        "title", "routing_effective_priority", "routing_team",
        "routing_sla", "status", "submitted_at",
    ]
    list_filter   = ["status", "routing_tier", "routing_effective_priority", "department"]
    search_fields = ["ticket_id", "name", "title", "department"]
    readonly_fields = [
        "ticket_id", "submitter", "routing_tier", "routing_tier_label",
        "routing_team", "routing_sla", "routing_effective_priority",
        "routing_was_modified", "routing_reasons", "routing_escalation_path",
        "submitted_at", "updated_at",
    ]
