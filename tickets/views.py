"""
tickets/views.py
================
Django views — the Controller layer in MVC.

New in this version:
  - employee_login / employee_logout — session-based authentication
  - login_required decorator — guards submit, success, and routing pages
  - submit_ticket pre-fills form from logged-in employee's profile
  - export_tickets — generates CSV, XLSX, or PDF of the current queue
"""

import csv
import io
import json
from functools import wraps

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse

from .forms import TicketSubmitForm
from .models import Employee, Ticket, TicketStatus
from .routing import (
    RoutingEngine,
    TIER_META,
    SLA_MATRIX,
    CATEGORY_TEAMS,
    SUBTYPE_RULES,
    KEYWORD_RULES,
    DEPARTMENT_TIERS,
    ISSUE_CASCADE,
    PRIORITY_LABELS,
)


# ---------------------------------------------------------------------------
# AUTH HELPERS
# ---------------------------------------------------------------------------

def login_required(view_fn):
    """Redirect unauthenticated requests to the login page."""
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("employee_id"):
            return redirect("employee_login")
        return view_fn(request, *args, **kwargs)
    return wrapper


def _get_logged_in_employee(request):
    """Return the Employee object for the current session, or None."""
    emp_pk = request.session.get("employee_pk")
    if emp_pk:
        try:
            return Employee.objects.get(pk=emp_pk, is_active=True)
        except Employee.DoesNotExist:
            pass
    return None


# ---------------------------------------------------------------------------
# EMPLOYEE LOGIN / LOGOUT
# ---------------------------------------------------------------------------

def employee_login(request):
    """
    GET  — show login form.
    POST — validate employee_id + email + password against Employee table.
    """
    # Already logged in → go to submit form
    if request.session.get("employee_pk"):
        return redirect("submit_ticket")

    error = ""

    if request.method == "POST":
        emp_id   = request.POST.get("employee_id", "").strip()
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        try:
            emp = Employee.objects.get(employee_id=emp_id, is_active=True)
            if emp.email.lower() == email and emp.check_password(password):
                # Store minimal session data
                request.session["employee_pk"] = emp.pk
                request.session["employee_id"] = emp.employee_id
                request.session["employee_name"] = emp.full_name
                request.session.set_expiry(28800)   # 8-hour session
                return redirect("submit_ticket")
            else:
                error = "Invalid Employee ID, email, or password."
        except Employee.DoesNotExist:
            error = "Invalid Employee ID, email, or password."

    return render(request, "tickets/login.html", {"error": error})


def employee_logout(request):
    """Clear the session and redirect to login."""
    request.session.flush()
    return redirect("employee_login")


# ---------------------------------------------------------------------------
# SUBMIT TICKET
# ---------------------------------------------------------------------------

@login_required
def submit_ticket(request):
    """
    GET  — display form pre-filled from the employee's profile.
    POST — validate, run routing engine, persist, redirect to success.
    """
    emp = _get_logged_in_employee(request)

    if request.method == "POST":
        form = TicketSubmitForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.submitter = emp

            combined_text = (
                form.cleaned_data.get("title", "") + " " +
                form.cleaned_data.get("description", "")
            )
            result = RoutingEngine.compute(
                dept=form.cleaned_data["department"],
                category=form.cleaned_data["category"],
                subtype=form.cleaned_data.get("subtype", ""),
                user_priority=int(form.cleaned_data["user_priority"]),
                text=combined_text,
            )

            ticket.routing_tier               = result.tier
            ticket.routing_tier_label         = result.tier_label
            ticket.routing_team               = result.team
            ticket.routing_sla                = result.sla
            ticket.routing_effective_priority = result.effective_priority
            ticket.routing_was_modified       = result.was_modified
            ticket.routing_reasons            = json.dumps(result.reasons)
            ticket.routing_escalation_path    = json.dumps(result.escalation_path)

            ticket.save()
            return redirect("ticket_success", ticket_id=ticket.ticket_id)
    else:
        # Pre-fill name / employee_id / department / email from Employee profile
        initial = {}
        if emp:
            initial = {
                "name":        emp.full_name,
                "employee_id": emp.employee_id,
                "department":  emp.department,
                "email":       emp.email,
            }
        form = TicketSubmitForm(initial=initial)

    cascade_json = json.dumps({
        cat: {
            "subtypes":    data["subtypes"],
            "issue_types": data["issue_types"],
        }
        for cat, data in ISSUE_CASCADE.items()
    })

    return render(request, "tickets/submit.html", {
        "form":         form,
        "cascade_json": cascade_json,
        "employee":     emp,
    })


@login_required
def ticket_success(request, ticket_id):
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    return render(request, "tickets/success.html", {"ticket": ticket})


# ---------------------------------------------------------------------------
# LIVE ROUTING AJAX ENDPOINT
# ---------------------------------------------------------------------------

@login_required
def live_route(request):
    dept     = request.GET.get("dept", "")
    category = request.GET.get("category", "")
    subtype  = request.GET.get("subtype", "")
    priority = int(request.GET.get("priority", 4))
    text     = request.GET.get("text", "")

    if not dept or not category:
        return JsonResponse({"ready": False})

    result = RoutingEngine.compute(dept, category, subtype, priority, text)

    return JsonResponse({
        "ready":              True,
        "team":               result.team,
        "sla":                result.sla,
        "effective_priority": result.effective_priority,
        "priority_label":     result.priority_label,
        "tier":               result.tier,
        "tier_label":         result.tier_label,
        "tier_icon":          result.tier_icon,
        "suggested_priority": result.suggested_priority,
        "was_modified":       result.was_modified,
        "escalation_path":    result.escalation_path,
        "reasons":            result.reasons,
    })


# ---------------------------------------------------------------------------
# ADMIN QUEUE
# ---------------------------------------------------------------------------

def admin_queue(request):
    """Admin dashboard — no login guard so IT staff can access directly."""
    tickets = Ticket.objects.select_related("submitter").all()

    status_filter   = request.GET.get("status",   "")
    priority_filter = request.GET.get("priority", "")
    tier_filter     = request.GET.get("tier",     "")

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(routing_effective_priority=int(priority_filter))
    if tier_filter:
        tickets = tickets.filter(routing_tier=tier_filter)

    all_tickets = Ticket.objects.all()
    stats = {
        "total":       all_tickets.count(),
        "open":        all_tickets.filter(status=TicketStatus.OPEN).count(),
        "in_progress": all_tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
        "critical":    all_tickets.filter(routing_effective_priority=1).count(),
        "infra":       all_tickets.filter(routing_tier="CRITICAL_INFRA").count(),
    }

    context = {
        "tickets":          tickets,
        "stats":            stats,
        "status_filter":    status_filter,
        "priority_filter":  priority_filter,
        "tier_filter":      tier_filter,
        "status_choices":   [("", "All Statuses")] + list(TicketStatus.choices),
        "priority_choices": [
            ("", "All Priorities"),
            ("1", "Critical"), ("2", "High"), ("3", "Medium"), ("4", "Low"),
        ],
        "tier_choices": [
            ("", "All Dept Tiers"),
            ("CRITICAL_INFRA", "Critical Infra"),
            ("EXECUTIVE",      "Executive"),
            ("PUBLIC_SAFETY",  "Public Safety"),
            ("STANDARD",       "Standard"),
        ],
    }
    return render(request, "tickets/admin_queue.html", context)


# ---------------------------------------------------------------------------
# TICKET DETAIL
# ---------------------------------------------------------------------------

def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "escalate" and ticket.routing_effective_priority > 1:
            new_pri = ticket.routing_effective_priority - 1
            result  = RoutingEngine.compute(
                dept=ticket.department,
                category=ticket.category,
                subtype=ticket.subtype,
                user_priority=new_pri,
                text=ticket.title + " " + ticket.description,
            )
            ticket.routing_effective_priority = result.effective_priority
            ticket.routing_team               = result.team
            ticket.routing_sla                = result.sla
            ticket.routing_reasons            = json.dumps(result.reasons)
            ticket.routing_escalation_path    = json.dumps(result.escalation_path)
            ticket.routing_was_modified       = True
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.save()

        elif action == "resolve":
            ticket.status = TicketStatus.CLOSED
            ticket.save()

        return redirect("ticket_detail", ticket_id=ticket_id)

    return render(request, "tickets/ticket_detail.html", {"ticket": ticket})


# ---------------------------------------------------------------------------
# EXPORT REPORTS
# ---------------------------------------------------------------------------

def _get_export_queryset(request):
    """Apply same filters as admin_queue, return a queryset."""
    qs = Ticket.objects.select_related("submitter").all()
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    if request.GET.get("priority"):
        qs = qs.filter(routing_effective_priority=int(request.GET["priority"]))
    if request.GET.get("tier"):
        qs = qs.filter(routing_tier=request.GET["tier"])
    return qs


EXPORT_COLUMNS = [
    ("ticket_id",               "Ticket ID"),
    ("submitted_at",            "Submitted"),
    ("name",                    "Employee Name"),
    ("employee_id",             "Employee ID"),
    ("department",              "Department"),
    ("routing_tier_label",      "Dept Tier"),
    ("category",                "Category"),
    ("subtype",                 "Sub-Type"),
    ("issue_type",              "Issue Type"),
    ("title",                   "Summary"),
    ("routing_effective_priority", "Eff. Priority"),
    ("routing_team",            "Assigned Team"),
    ("routing_sla",             "SLA Target"),
    ("status",                  "Status"),
    ("routing_was_modified",    "Auto-Adjusted"),
]


def _ticket_row(ticket):
    return [
        ticket.ticket_id,
        ticket.submitted_at.strftime("%Y-%m-%d %H:%M"),
        ticket.name,
        ticket.employee_id,
        ticket.department,
        ticket.routing_tier_label,
        ticket.category,
        ticket.subtype,
        ticket.issue_type,
        ticket.title,
        PRIORITY_LABELS.get(ticket.routing_effective_priority, ""),
        ticket.routing_team,
        ticket.routing_sla,
        ticket.status,
        "Yes" if ticket.routing_was_modified else "No",
    ]


def export_csv(request):
    tickets = _get_export_queryset(request)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="laredo_ist_tickets.csv"'

    writer = csv.writer(response)
    writer.writerow([col[1] for col in EXPORT_COLUMNS])
    for ticket in tickets:
        writer.writerow(_ticket_row(ticket))

    return response


def export_xlsx(request):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        return HttpResponse("openpyxl not installed. Run: pip install openpyxl", status=500)

    tickets = _get_export_queryset(request)

    wb = Workbook()
    ws = wb.active
    ws.title = "Work Orders"

    # ── Colour palette
    NAVY   = "08111F"
    GOLD   = "C9A84C"
    WHITE  = "EEF2F8"
    GREY   = "1E3358"

    # ── Title row
    ws.merge_cells("A1:O1")
    title_cell = ws["A1"]
    title_cell.value = "City of Laredo IST — Work Order Export"
    title_cell.font      = Font(name="Calibri", bold=True, size=14, color=WHITE)
    title_cell.fill      = PatternFill("solid", fgColor=NAVY)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # ── Header row
    header_fill   = PatternFill("solid", fgColor=GREY)
    header_font   = Font(name="Calibri", bold=True, size=10, color=GOLD)
    header_border = Border(
        bottom=Side(style="thin", color=GOLD),
        right=Side(style="thin", color="2A3A55"),
    )

    for col_idx, (_, label) in enumerate(EXPORT_COLUMNS, start=1):
        cell = ws.cell(row=2, column=col_idx, value=label)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.border    = header_border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 32

    # ── Data rows — zebra striping
    PRIORITY_COLOURS = {"Critical": "3D0C0C", "High": "3D2700", "Medium": "0E1E35", "Low": "111B2B"}
    EVEN_FILL = PatternFill("solid", fgColor="0F1E35")
    ODD_FILL  = PatternFill("solid", fgColor="162845")
    data_font = Font(name="Calibri", size=10, color=WHITE)

    for row_idx, ticket in enumerate(tickets, start=3):
        row_data = _ticket_row(ticket)
        fill = EVEN_FILL if row_idx % 2 == 0 else ODD_FILL

        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font      = data_font
            cell.fill      = fill
            cell.alignment = Alignment(vertical="center", wrap_text=False)

        # Highlight priority cell
        pri_label = row_data[10]   # column index of Eff. Priority
        pri_cell  = ws.cell(row=row_idx, column=11)
        pri_colour = PRIORITY_COLOURS.get(pri_label, "111B2B")
        pri_cell.fill = PatternFill("solid", fgColor=pri_colour)
        pri_cell.font = Font(name="Calibri", bold=True, size=10, color=GOLD)

    # ── Column widths
    col_widths = [12, 16, 22, 14, 22, 20, 12, 16, 18, 40, 14, 28, 10, 12, 14]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── Freeze header rows
    ws.freeze_panes = "A3"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="laredo_ist_tickets.xlsx"'
    return response


def export_pdf(request):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, HRFlowable,
        )
    except ImportError:
        return HttpResponse("reportlab not installed. Run: pip install reportlab", status=500)

    from django.utils import timezone as tz

    tickets = list(_get_export_queryset(request))

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.6*inch,  bottomMargin=0.5*inch,
    )

    # ── Colours
    NAVY  = colors.HexColor("#08111F")
    GOLD  = colors.HexColor("#C9A84C")
    STEEL = colors.HexColor("#1E3358")
    WHITE = colors.white
    P1C   = colors.HexColor("#4A1010")
    P2C   = colors.HexColor("#4A2800")
    P3C   = colors.HexColor("#0E2040")
    P4C   = colors.HexColor("#16263E")

    PRI_COLOURS = {"Critical": P1C, "High": P2C, "Medium": P3C, "Low": P4C}

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"],
        textColor=WHITE, backColor=NAVY,
        fontSize=15, spaceAfter=4, spaceBefore=0,
        leftIndent=6,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        textColor=GOLD, fontSize=9, spaceAfter=10,
    )

    story = []

    # ── Document header
    story.append(Paragraph("City of Laredo — IST Work Order Report", title_style))
    story.append(Paragraph(
        f"Generated: {tz.localtime().strftime('%B %d, %Y at %I:%M %p')}  ·  "
        f"Total records: {len(tickets)}",
        sub_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=8))

    # ── Table
    pdf_cols = ["ID", "Date", "Employee", "Department", "Category",
                "Sub-Type", "Summary", "Priority", "Team", "SLA", "Status"]

    table_data = [pdf_cols]

    for ticket in tickets:
        pri_label = PRIORITY_LABELS.get(ticket.routing_effective_priority, "")
        table_data.append([
            ticket.ticket_id,
            ticket.submitted_at.strftime("%m/%d/%Y"),
            ticket.name,
            ticket.department[:18],
            ticket.category.capitalize(),
            (ticket.subtype or "—")[:14],
            ticket.title[:38] + ("…" if len(ticket.title) > 38 else ""),
            pri_label,
            ticket.routing_team[:22],
            ticket.routing_sla,
            ticket.status,
        ])

    col_widths_pdf = [
        0.75*inch, 0.75*inch, 1.3*inch, 1.45*inch, 0.8*inch,
        0.9*inch, 2.5*inch, 0.7*inch, 1.6*inch, 0.6*inch, 0.75*inch,
    ]

    tbl = Table(table_data, colWidths=col_widths_pdf, repeatRows=1)

    tbl_style = TableStyle([
        # Header
        ("BACKGROUND",   (0, 0), (-1, 0),  STEEL),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  GOLD),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
        ("BOTTOMPADDING",(0, 0), (-1, 0),  8),
        ("TOPPADDING",   (0, 0), (-1, 0),  8),
        # Data rows
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 7.5),
        ("TEXTCOLOR",    (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#0F1E35"), colors.HexColor("#162845")]),
        ("TOPPADDING",   (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#1E3358")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ])

    # Colour-code priority cells
    for row_idx, ticket in enumerate(tickets, start=1):
        pri = PRIORITY_LABELS.get(ticket.routing_effective_priority, "")
        c   = PRI_COLOURS.get(pri, P4C)
        tbl_style.add("BACKGROUND", (7, row_idx), (7, row_idx), c)
        tbl_style.add("TEXTCOLOR",  (7, row_idx), (7, row_idx), GOLD)
        tbl_style.add("FONTNAME",   (7, row_idx), (7, row_idx), "Helvetica-Bold")

    tbl.setStyle(tbl_style)
    story.append(tbl)

    # ── Page footer callback
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, landscape(letter)[0], 0.4*inch, fill=True, stroke=False)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GOLD)
        canvas.drawString(0.5*inch, 0.15*inch, "City of Laredo — Information Systems & Technology")
        canvas.drawRightString(
            landscape(letter)[0] - 0.5*inch, 0.15*inch,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="laredo_ist_tickets.pdf"'
    return response


# ---------------------------------------------------------------------------
# ROUTING REFERENCE
# ---------------------------------------------------------------------------

@login_required
def routing_reference(request):
    context = {
        "tier_meta":      TIER_META,
        "sla_matrix":     SLA_MATRIX,
        "category_teams": CATEGORY_TEAMS,
        "subtype_rules":  SUBTYPE_RULES,
        "keyword_rules":  KEYWORD_RULES,
        "dept_tiers":     DEPARTMENT_TIERS,
    }
    return render(request, "tickets/routing_ref.html", context)
