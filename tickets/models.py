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

class EmployeeRole(models.TextChoices):
    DEPT  = "dept",  "Department Employee"
    IST   = "ist",   "IST Staff"
    ADMIN = "admin", "IST Admin"


class Employee(models.Model):
    """
    Represents a City of Laredo employee who can authenticate and submit
    work orders.  Passwords are stored as Django-hashed strings (PBKDF2).

    Roles:
      dept  — regular city department staff; can submit tickets and track them
      ist   — IST support staff; can also view the admin queue and ticket detail
      admin — IST administrator; same access as ist plus user management
    """
    employee_id = models.CharField("Employee ID", max_length=30, unique=True)
    first_name  = models.CharField("First Name",  max_length=60)
    last_name   = models.CharField("Last Name",   max_length=60)
    email       = models.EmailField("Email",       unique=True)
    department  = models.CharField("Department",   max_length=80,
                                   choices=DEPARTMENT_CHOICES)
    role        = models.CharField("Role", max_length=10,
                                   choices=EmployeeRole.choices,
                                   default=EmployeeRole.DEPT)
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

    # 5 W's — additional context fields
    affected_users  = models.TextField(
        "Who Else Is Affected",
        blank=True,
        help_text="List other employees, teams, or systems impacted by this issue.",
    )
    when_started    = models.CharField(
        "When Did This Start",
        max_length=120, blank=True,
        help_text="e.g. 'This morning around 9am', 'Since last Friday', 'Just now'",
    )
    business_impact = models.TextField(
        "Business Impact / Why It Matters",
        blank=True,
        help_text="Describe the operational impact — what work is blocked, who is waiting, any deadlines affected.",
    )

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


# ---------------------------------------------------------------------------
# TICKET HISTORY MODEL
# ---------------------------------------------------------------------------

class HistoryAction(models.TextChoices):
    CREATED   = "Created",   "Created"
    ESCALATED = "Escalated", "Escalated"
    RESOLVED  = "Resolved",  "Resolved"
    REOPENED  = "Reopened",  "Reopened"
    NOTE      = "Note",      "Note Added"
    ASSIGNED  = "Assigned",  "Reassigned"


class TicketHistory(models.Model):
    """
    Immutable audit trail for a ticket.
    One row is appended for every significant event — never edited or deleted.
    """
    ticket      = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="history"
    )
    action      = models.CharField(
        max_length=20, choices=HistoryAction.choices
    )
    note        = models.TextField("Note", blank=True)
    changed_by  = models.CharField("Changed By", max_length=120, blank=True)

    # Snapshot of priority before/after for escalation events
    priority_before = models.IntegerField(null=True, blank=True)
    priority_after  = models.IntegerField(null=True, blank=True)

    # Snapshot of assigned team for reassignment events
    team_before = models.CharField(max_length=100, blank=True)
    team_after  = models.CharField(max_length=100, blank=True)

    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Ticket History Entry"
        verbose_name_plural = "Ticket History"

    def __str__(self):
        return f"{self.ticket.ticket_id} — {self.action} at {self.timestamp:%Y-%m-%d %H:%M}"

    @property
    def priority_before_label(self):
        return PRIORITY_LABELS.get(self.priority_before, "") if self.priority_before else ""

    @property
    def priority_after_label(self):
        return PRIORITY_LABELS.get(self.priority_after, "") if self.priority_after else ""
    
# ---------------------------------------------------------------------------
# TICKET ATTACHMENT MODEL
# ---------------------------------------------------------------------------

def attachment_upload_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"{instance.ticket.ticket_id}_{instance.pk or 'new'}{ext}"
    return f"attachments/{instance.ticket.ticket_id}/{safe_name}"


class TicketAttachment(models.Model):
    ticket      = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="attachments"
    )
    file        = models.ImageField(upload_to=attachment_upload_path)
    filename    = models.CharField(max_length=255, blank=True)
    uploaded_by = models.CharField(max_length=120, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self):
        return f"{self.ticket.ticket_id} — {self.filename}"

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            import os
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    @property
    def is_image(self):
        return self.filename.lower().endswith(
            ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        )