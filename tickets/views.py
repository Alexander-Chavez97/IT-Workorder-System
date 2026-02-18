"""
tickets/views.py
================
Django views — the Controller layer in MVC.

Each view is responsible for:
  1. Receiving an HTTP request.
  2. Calling the RoutingEngine (Model) with form data.
  3. Persisting results to the Ticket model.
  4. Passing a context dict to the appropriate template (View).

Views deliberately contain no routing logic — all decisions live in routing.py.
"""

import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import TicketSubmitForm
from .models import Ticket, TicketStatus
from .routing import (
    RoutingEngine,
    TIER_META,
    SLA_MATRIX,
    CATEGORY_TEAMS,
    SUBTYPE_RULES,
    KEYWORD_RULES,
    DEPARTMENT_TIERS,
)


# ---------------------------------------------------------------------------
# SUBMIT VIEW
# ---------------------------------------------------------------------------

def submit_ticket(request):
    """
    GET  — display the blank submission form.
    POST — validate, run the routing engine, persist, redirect to success.
    """
    if request.method == "POST":
        form = TicketSubmitForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)

            # Run the routing engine
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

            # Write routing decision onto the ticket
            ticket.routing_tier            = result.tier
            ticket.routing_tier_label      = result.tier_label
            ticket.routing_team            = result.team
            ticket.routing_sla             = result.sla
            ticket.routing_effective_priority = result.effective_priority
            ticket.routing_was_modified    = result.was_modified
            ticket.routing_reasons         = json.dumps(result.reasons)
            ticket.routing_escalation_path = json.dumps(result.escalation_path)

            ticket.save()
            return redirect("ticket_success", ticket_id=ticket.ticket_id)
    else:
        form = TicketSubmitForm()

    return render(request, "tickets/submit.html", {"form": form})


def ticket_success(request, ticket_id):
    """
    Confirmation page shown after a successful submission.
    """
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
    return render(request, "tickets/success.html", {"ticket": ticket})


# ---------------------------------------------------------------------------
# LIVE ROUTING AJAX ENDPOINT
# ---------------------------------------------------------------------------

def live_route(request):
    """
    AJAX endpoint — called by the form's JS as the user types.
    Runs the routing engine and returns a JSON routing decision
    so the form can show a live preview without a page reload.
    """
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
# ADMIN QUEUE VIEW
# ---------------------------------------------------------------------------

def admin_queue(request):
    """
    Admin dashboard showing all tickets with filtering support.
    """
    tickets = Ticket.objects.all()

    # Filters from query params
    status_filter   = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")
    tier_filter     = request.GET.get("tier", "")

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(routing_effective_priority=int(priority_filter))
    if tier_filter:
        tickets = tickets.filter(routing_tier=tier_filter)

    # Stats for the dashboard (always computed over all tickets)
    all_tickets = Ticket.objects.all()
    stats = {
        "total":       all_tickets.count(),
        "open":        all_tickets.filter(status=TicketStatus.OPEN).count(),
        "in_progress": all_tickets.filter(status=TicketStatus.IN_PROGRESS).count(),
        "critical":    all_tickets.filter(routing_effective_priority=1).count(),
        "infra":       all_tickets.filter(routing_tier="CRITICAL_INFRA").count(),
        "open_count":  all_tickets.exclude(status=TicketStatus.CLOSED).count(),
    }

    context = {
        "tickets":         tickets,
        "stats":           stats,
        "status_filter":   status_filter,
        "priority_filter": priority_filter,
        "tier_filter":     tier_filter,
        "status_choices":  [("", "All Statuses")] + list(TicketStatus.choices),
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
# TICKET DETAIL VIEW
# ---------------------------------------------------------------------------

def ticket_detail(request, ticket_id):
    """
    Full detail view for a single ticket.
    Supports POST actions: escalate, resolve.
    """
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "escalate":
            curr = ticket.routing_effective_priority
            if curr > 1:
                new_priority = curr - 1
                result = RoutingEngine.compute(
                    dept=ticket.department,
                    category=ticket.category,
                    subtype=ticket.subtype,
                    user_priority=new_priority,
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
# ROUTING REFERENCE VIEW
# ---------------------------------------------------------------------------

def routing_reference(request):
    """
    Static reference page showing the full routing logic documentation.
    Passes the routing constants directly so the template can render them
    without hardcoding anything.
    """
    context = {
        "tier_meta":       TIER_META,
        "sla_matrix":      SLA_MATRIX,
        "category_teams":  CATEGORY_TEAMS,
        "subtype_rules":   SUBTYPE_RULES,
        "keyword_rules":   KEYWORD_RULES,
        "dept_tiers":      DEPARTMENT_TIERS,
    }
    return render(request, "tickets/routing_ref.html", context)
