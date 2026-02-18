"""
tickets/models.py
=================
Database model for work order tickets.
Stores the user's submission plus the resolved routing decision.
"""

from django.db import models
from django.utils import timezone

from .routing import (
    DEPARTMENT_CHOICES,
    CATEGORY_CHOICES,
    SUBTYPE_CHOICES,
    PRIORITY_CHOICES,
    PRIORITY_LABELS,
    DeptTier,
)


class TicketStatus(models.TextChoices):
    OPEN        = "Open",        "Open"
    IN_PROGRESS = "In Progress", "In Progress"
    CLOSED      = "Closed",      "Closed"


class Ticket(models.Model):
    """
    Represents a single IT support work order.

    Fields prefixed with 'routing_' are populated by the RoutingEngine after
    submission and should not be edited directly by end users.
    """

    # ── Auto-generated identifier ─────────────────────────────────────────
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)

    # ── Requestor information (Tier 1 inputs) ────────────────────────────
    name       = models.CharField("Full Name",    max_length=120)
    employee_id = models.CharField("Employee ID", max_length=30)
    department  = models.CharField("Department",  max_length=80, choices=DEPARTMENT_CHOICES)
    email       = models.EmailField("Contact Email")

    # ── Issue details (Tier 2–4 inputs) ──────────────────────────────────
    category  = models.CharField("Category",    max_length=30,  choices=CATEGORY_CHOICES)
    subtype   = models.CharField("Sub-Type",    max_length=30,  choices=SUBTYPE_CHOICES, blank=True)
    title     = models.CharField("Brief Summary", max_length=120)
    description = models.TextField("Detailed Description", blank=True)
    asset_tag   = models.CharField("Asset Tag",   max_length=40, blank=True)
    location    = models.CharField("Location",    max_length=80, blank=True)
    phone_ext   = models.CharField("Phone Ext",   max_length=10, blank=True)

    # ── User-selected priority ────────────────────────────────────────────
    user_priority = models.IntegerField(
        "User-Selected Priority",
        choices=PRIORITY_CHOICES,
        default=4,
    )

    # ── Routing engine outputs (populated on save) ────────────────────────
    routing_tier            = models.CharField("Dept Tier",         max_length=30,  blank=True)
    routing_tier_label      = models.CharField("Tier Label",        max_length=60,  blank=True)
    routing_team            = models.CharField("Assigned Team",     max_length=100, blank=True)
    routing_sla             = models.CharField("SLA Target",        max_length=20,  blank=True)
    routing_effective_priority = models.IntegerField("Effective Priority", default=4)
    routing_was_modified    = models.BooleanField("Priority Auto-Adjusted", default=False)
    routing_reasons         = models.TextField("Routing Reasons (JSON)", blank=True)
    routing_escalation_path = models.TextField("Escalation Path (JSON)",  blank=True)

    # ── Status & timestamps ───────────────────────────────────────────────
    status     = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

    def __str__(self):
        return f"{self.ticket_id} — {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate ticket ID on first save
        if not self.ticket_id:
            from django.db.models import Max
            result = Ticket.objects.aggregate(max_id=Max("id"))
            next_num = (result["max_id"] or 0) + 1
            self.ticket_id = f"TKT-{next_num:04d}"
        super().save(*args, **kwargs)

    # ── Convenience properties for templates ─────────────────────────────

    @property
    def effective_priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.routing_effective_priority, "Unknown")

    @property
    def user_priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.user_priority, "Unknown")

    @property
    def priority_badge_class(self) -> str:
        return {1: "bp1", 2: "bp2", 3: "bp3", 4: "bp4"}.get(
            self.routing_effective_priority, "bp4"
        )

    @property
    def status_badge_class(self) -> str:
        return {
            "Open":        "bs-open",
            "In Progress": "bs-prog",
            "Closed":      "bs-clos",
        }.get(self.status, "")

    @property
    def tier_badge_class(self) -> str:
        return f"tier-{self.routing_tier}"

    @property
    def routing_reasons_list(self) -> list[str]:
        import json
        try:
            return json.loads(self.routing_reasons)
        except (ValueError, TypeError):
            return []

    @property
    def escalation_path_list(self) -> list[str]:
        import json
        try:
            return json.loads(self.routing_escalation_path)
        except (ValueError, TypeError):
            return []
