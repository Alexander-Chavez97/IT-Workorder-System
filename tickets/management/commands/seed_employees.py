"""
tickets/management/commands/seed_employees.py
=============================================
Populates the database with realistic fake employees and sample tickets.

Usage:
    python manage.py seed_employees          # create if not exists
    python manage.py seed_employees --reset  # wipe and recreate
"""

import json
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Employee, Ticket, TicketStatus
from tickets.routing import RoutingEngine


FAKE_EMPLOYEES = [
    # (employee_id, first, last, email, department, password)
    ("LRD-1001", "Maria",    "Gonzalez",  "m.gonzalez@laredotx.gov",  "Finance",               "Laredo2024!"),
    ("LRD-1002", "Carlos",   "Ramirez",   "c.ramirez@laredotx.gov",   "Police Department",     "Laredo2024!"),
    ("LRD-1003", "Sofia",    "Herrera",   "s.herrera@laredotx.gov",   "City Clerk",            "Laredo2024!"),
    ("LRD-1004", "James",    "Williams",  "j.williams@laredotx.gov",  "Public Works",          "Laredo2024!"),
    ("LRD-1005", "Ana",      "Torres",    "a.torres@laredotx.gov",    "Health Department",     "Laredo2024!"),
    ("LRD-1006", "Roberto",  "Salinas",   "r.salinas@laredotx.gov",   "Fire Department",       "Laredo2024!"),
    ("LRD-1007", "Linda",    "Martinez",  "l.martinez@laredotx.gov",  "Parks & Recreation",    "Laredo2024!"),
    ("LRD-1008", "David",    "Nguyen",    "d.nguyen@laredotx.gov",    "Utilities",             "Laredo2024!"),
    ("LRD-1009", "Patricia", "Lopez",     "p.lopez@laredotx.gov",     "Planning & Zoning",     "Laredo2024!"),
    ("LRD-1010", "Miguel",   "Castillo",  "m.castillo@laredotx.gov",  "City Manager's Office", "Laredo2024!"),
    ("LRD-1011", "Jessica",  "Flores",    "j.flores@laredotx.gov",    "Finance",               "Laredo2024!"),
    ("LRD-1012", "Fernando", "Reyes",     "f.reyes@laredotx.gov",     "Police Department",     "Laredo2024!"),
    ("LRD-1013", "Melissa",  "Garza",     "m.garza@laredotx.gov",     "Health Department",     "Laredo2024!"),
    ("LRD-1014", "Steven",   "Morales",   "s.morales@laredotx.gov",   "Public Works",          "Laredo2024!"),
    ("LRD-1015", "Diana",    "Vasquez",   "d.vasquez@laredotx.gov",   "City Clerk",            "Laredo2024!"),
    ("LRD-1016", "Hector",   "Jimenez",   "h.jimenez@laredotx.gov",   "Fire Department",       "Laredo2024!"),
    ("LRD-1017", "Rachel",   "Cruz",      "r.cruz@laredotx.gov",      "Parks & Recreation",    "Laredo2024!"),
    ("LRD-1018", "Antonio",  "Mendoza",   "a.mendoza@laredotx.gov",   "Utilities",             "Laredo2024!"),
    ("LRD-1019", "Vanessa",  "Perez",     "v.perez@laredotx.gov",     "Planning & Zoning",     "Laredo2024!"),
    ("LRD-1020", "Eduardo",  "Ramos",     "e.ramos@laredotx.gov",     "City Manager's Office", "Laredo2024!"),
    # IST Admin account
    ("IST-ADMIN", "IST",     "Admin",     "ist.admin@laredotx.gov",   "City Manager's Office", "ISTadmin2024!"),
]

SAMPLE_TICKETS = [
    {
        "emp_id": "LRD-1001",
        "category": "hardware", "subtype": "no_boot", "issue_type": "wont_power_on",
        "title": "Desktop will not turn on after weekend",
        "description": "Computer was working fine Friday. Came in Monday and it won't power on at all. Power button does nothing.",
        "priority": 3, "status": "In Progress",
    },
    {
        "emp_id": "LRD-1002",
        "category": "network", "subtype": "complete_outage", "issue_type": "dept_outage",
        "title": "Entire detective division has no network access",
        "description": "All computers on the 3rd floor detective division lost internet and internal network access. Cannot access RMS or dispatch systems.",
        "priority": 3, "status": "Open",
    },
    {
        "emp_id": "LRD-1003",
        "category": "email", "subtype": "no_login", "issue_type": "password_issue",
        "title": "Cannot log into Outlook — locked out",
        "description": "Getting 'account locked' message when trying to open Outlook. Tried resetting password through portal but still locked.",
        "priority": 3, "status": "Open",
    },
    {
        "emp_id": "LRD-1007",
        "category": "software", "subtype": "app_crash", "issue_type": "app_freezes",
        "title": "Parks scheduling software crashes on launch",
        "description": "RecTrac crashes immediately after login screen every time since the update last Tuesday.",
        "priority": 3, "status": "Open",
    },
    {
        "emp_id": "LRD-1018",
        "category": "security", "subtype": "data_loss", "issue_type": "suspected_breach",
        "title": "SCADA system showing unauthorized access alert",
        "description": "Water treatment SCADA console is showing an unauthorized access alert from an unknown IP. Need immediate investigation.",
        "priority": 2, "status": "Open",
    },
    {
        "emp_id": "LRD-1010",
        "category": "hardware", "subtype": "display", "issue_type": "no_display_output",
        "title": "Monitor not displaying anything after move",
        "description": "Moved office over the weekend. Reconnected everything but monitor stays black. The PC appears to be on.",
        "priority": 3, "status": "Open",
    },
    {
        "emp_id": "LRD-1005",
        "category": "software", "subtype": "no_login", "issue_type": "account_locked",
        "title": "EMR system account locked — patients waiting",
        "description": "Cannot access the Electronic Medical Records system. Error says account is disabled. Have patients in waiting room.",
        "priority": 2, "status": "In Progress",
    },
    {
        "emp_id": "LRD-1011",
        "category": "data", "subtype": "data_loss", "issue_type": "report_wrong",
        "title": "Budget report showing wrong totals for Q3",
        "description": "Q3 budget summary report is showing totals that don't match our spreadsheets. Possible data import issue after the server maintenance.",
        "priority": 3, "status": "Open",
    },
]


class Command(BaseCommand):
    help = "Seed the database with fake employees and sample tickets for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing employees and tickets before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Ticket.objects.all().delete()
            Employee.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing employees and tickets."))

        # ── Create employees ─────────────────────────────────────────────
        created_emps = 0
        emp_map = {}

        for emp_id, first, last, email, dept, raw_pw in FAKE_EMPLOYEES:
            emp, created = Employee.objects.get_or_create(
                employee_id=emp_id,
                defaults={
                    "first_name": first,
                    "last_name":  last,
                    "email":      email,
                    "department": dept,
                },
            )
            if created:
                emp.set_password(raw_pw)
                emp.save()
                created_emps += 1
            emp_map[emp_id] = emp

        self.stdout.write(self.style.SUCCESS(
            f"  Employees: {created_emps} created, {len(FAKE_EMPLOYEES) - created_emps} already existed."
        ))

        # ── Create sample tickets ────────────────────────────────────────
        created_tix = 0

        for t in SAMPLE_TICKETS:
            emp = emp_map.get(t["emp_id"])
            if not emp:
                continue

            text = t["title"] + " " + t["description"]
            result = RoutingEngine.compute(
                dept=emp.department,
                category=t["category"],
                subtype=t.get("subtype", ""),
                user_priority=t["priority"],
                text=text,
            )

            ticket = Ticket(
                submitter=emp,
                name=emp.full_name,
                employee_id=emp.employee_id,
                department=emp.department,
                email=emp.email,
                category=t["category"],
                subtype=t.get("subtype", ""),
                issue_type=t.get("issue_type", ""),
                title=t["title"],
                description=t["description"],
                user_priority=t["priority"],
                status=t["status"],
                routing_tier=result.tier,
                routing_tier_label=result.tier_label,
                routing_team=result.team,
                routing_sla=result.sla,
                routing_effective_priority=result.effective_priority,
                routing_was_modified=result.was_modified,
                routing_reasons=json.dumps(result.reasons),
                routing_escalation_path=json.dumps(result.escalation_path),
            )
            ticket.save()
            created_tix += 1

        self.stdout.write(self.style.SUCCESS(f"  Tickets:   {created_tix} created."))
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("── Seed complete. Test credentials ──"))
        self.stdout.write("  All employees:  password = Laredo2024!")
        self.stdout.write("  IST Admin:      IST-ADMIN / ISTadmin2024!")
        self.stdout.write("  Example login:  LRD-1001 / m.gonzalez@laredotx.gov / Laredo2024!")
