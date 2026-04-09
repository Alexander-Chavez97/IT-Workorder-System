"""
tickets/urls.py
===============
URL patterns for the tickets app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── Authentication
    path("login/",   views.employee_login,  name="employee_login"),
    path("logout/",  views.employee_logout, name="employee_logout"),

    # ── Employee-facing (login required)
    path("",                         views.submit_ticket,   name="submit_ticket"),
    path("success/<str:ticket_id>/", views.ticket_success,  name="ticket_success"),

    # ── AJAX live routing endpoint
    path("api/route/",               views.live_route,       name="live_route"),

    # ── Ticket lookup (employee read-only)
    path("track/",                      views.ticket_lookup,    name="ticket_lookup"),

    # ── Admin queue & detail
    path("admin-queue/",             views.admin_queue,      name="admin_queue"),
    path("ticket/<str:ticket_id>/",  views.ticket_detail,    name="ticket_detail"),

    # ── Exports (CSV / XLSX / PDF)
    path("export/csv/",              views.export_csv,       name="export_csv"),
    path("export/xlsx/",             views.export_xlsx,      name="export_xlsx"),
    path("export/pdf/",              views.export_pdf,       name="export_pdf"),

    path("manage_employees/", views.manage_employees, name="manage_employees"),

    path("manage_employees/<int:employee_id>/", views.employee_detail, name="employee_detail"),

    path("manage_employees/export/csv/", views.export_employees_csv, name="export_employees_csv"),
    path("manage_employees/export/xlsx/", views.export_employees_xlsx, name="export_employees_xlsx"),
    path("manage_employees/export/pdf/", views.export_employees_pdf, name="export_employees_pdf"),

]