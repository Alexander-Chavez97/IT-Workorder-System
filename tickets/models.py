"""
tickets/models.py
=================
Database models:
  Employee  — city staff who can log in and submit tickets
  Ticket    — IT support work order with full routing metadata
"""

from django.db import models
from django.contrib.auth.hashers import make_password, check_password

from .routing import (
    DEPARTMENT_CHOICES,
    CATEGORY_CHOICES,
    SUBTYPE_CHOICES,
    ISSUE_TYPE_CHOICES,
    PRIORITY_CHOICES,
    PRIORITY_LABELS,
    DeptTier,
)


# ---------------------------------------------------------------------------
# EMPLOYEE MODEL
# ---------------------------------------------------------------------------

class Employee(models.Model):
    """
    Represents a City of Laredo employee who can authenticate and submit
    work orders.  Passwords are stored as Django-hashed strings (PBKDF2).
    """
    employee_id = models.CharField("Employee ID", max_length=30, unique=True)
    first_name  = models.CharField("First Name",  max_length=60)
    last_name   = models.CharField("Last Name",   max_length=60)
    email       = models.EmailField("Email",       unique=True)
    department  = models.CharField("Department",   max_length=80,
                                   choices=DEPARTMENT_CHOICES)
    password    = models.CharField("Password Hash", max_length=256)
    is_active   = models.BooleanField("Active", default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering    = ["last_name", "first_name"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def set_password(self, raw: str):
        self.password = make_password(raw)

    def check_password(self, raw: str) -> bool:
        return check_password(raw, self.password)


# ---------------------------------------------------------------------------
# TICKET MODEL
# ---------------------------------------------------------------------------

class TicketStatus(models.TextChoices):
    OPEN        = "Open",        "Open"
    IN_PROGRESS = "In Progress", "In Progress"
    CLOSED      = "Closed",      "Closed"


class Ticket(models.Model):
    """
    A single IT support work order.
    Fields prefixed with 'routing_' are populated by RoutingEngine on save.
    The submitter FK links to Employee (nullable so old tickets stay valid).
    """

    # Auto-generated identifier
    ticket_id   = models.CharField(max_length=20, unique=True, editable=False)

    # Link to authenticated employee (set by the login session on submit)
    submitter   = models.ForeignKey(
        Employee, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
        verbose_name="Submitted By",
    )

    # Requestor display fields (pre-filled from Employee on GET, kept for history)
    name        = models.CharField("Full Name",    max_length=120)
    employee_id = models.CharField("Employee ID",  max_length=30)
    department  = models.CharField("Department",   max_length=80,
                                   choices=DEPARTMENT_CHOICES)
    email       = models.EmailField("Contact Email")

    # Issue classification (cascade: category → subtype → issue_type)
    category    = models.CharField("Category",    max_length=30,
                                   choices=CATEGORY_CHOICES)
    subtype     = models.CharField("Sub-Type",    max_length=30,
                                   choices=SUBTYPE_CHOICES, blank=True)
    issue_type  = models.CharField("Issue Type",  max_length=40,
                                   choices=ISSUE_TYPE_CHOICES, blank=True)

    # Free-text fields scanned by keyword engine
    title       = models.CharField("Brief Summary",      max_length=120)
    description = models.TextField("Detailed Description", blank=True)

    # Optional asset / location info
    asset_tag   = models.CharField("Asset Tag",  max_length=40, blank=True)
    location    = models.CharField("Location",   max_length=80, blank=True)
    phone_ext   = models.CharField("Phone Ext",  max_length=10, blank=True)

    # User priority selection
    user_priority = models.IntegerField(
        "User-Selected Priority",
        choices=PRIORITY_CHOICES, default=4,
    )

    # Routing engine outputs
    routing_tier               = models.CharField("Dept Tier",         max_length=30,  blank=True)
    routing_tier_label         = models.CharField("Tier Label",        max_length=60,  blank=True)
    routing_team               = models.CharField("Assigned Team",     max_length=100, blank=True)
    routing_sla                = models.CharField("SLA Target",        max_length=20,  blank=True)
    routing_effective_priority = models.IntegerField("Effective Priority", default=4)
    routing_was_modified       = models.BooleanField("Priority Auto-Adjusted", default=False)
    routing_reasons            = models.TextField("Routing Reasons (JSON)", blank=True)
    routing_escalation_path    = models.TextField("Escalation Path (JSON)",  blank=True)

    # Status & timestamps
    status       = models.CharField(max_length=20, choices=TicketStatus.choices,
                                    default=TicketStatus.OPEN)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

    def __str__(self):
        return f"{self.ticket_id} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            from django.db.models import Max
            result = Ticket.objects.aggregate(max_id=Max("id"))
            next_num = (result["max_id"] or 0) + 1
            self.ticket_id = f"TKT-{next_num:04d}"
        super().save(*args, **kwargs)

    # ── Template convenience properties ──────────────────────────────────

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
    def routing_reasons_list(self) -> list:
        import json
        try:
            return json.loads(self.routing_reasons)
        except (ValueError, TypeError):
            return []

    @property
    def escalation_path_list(self) -> list:
        import json
        try:
            return json.loads(self.routing_escalation_path)
        except (ValueError, TypeError):
            return []
