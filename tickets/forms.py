"""
tickets/forms.py
================
Django form for ticket submission.
Choices are imported directly from routing.py so the form and routing engine
always stay in sync — no duplication.
"""

from django import forms

from .routing import (
    DEPARTMENT_CHOICES,
    CATEGORY_CHOICES,
    SUBTYPE_CHOICES,
    PRIORITY_CHOICES,
)
from .models import Ticket


class TicketSubmitForm(forms.ModelForm):
    """
    Form used by employees to submit a new work order.
    Maps directly to the Ticket model fields that belong to the user.
    """

    department = forms.ChoiceField(
        choices=[("", "— Select Department —")] + list(DEPARTMENT_CHOICES),
        widget=forms.Select(attrs={"id": "f_dept", "onchange": "liveRoute()"}),
    )
    category = forms.ChoiceField(
        choices=[("", "— Select Category —")] + list(CATEGORY_CHOICES),
        widget=forms.Select(attrs={"id": "f_cat", "onchange": "liveRoute()"}),
    )
    subtype = forms.ChoiceField(
        choices=SUBTYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"id": "f_sub", "onchange": "liveRoute()"}),
    )
    user_priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        initial=4,
        widget=forms.RadioSelect(attrs={"onchange": "liveRoute()"}),
    )

    class Meta:
        model = Ticket
        fields = [
            "name", "employee_id", "department", "email",
            "category", "subtype", "title", "description",
            "asset_tag", "location", "phone_ext", "user_priority",
        ]
        widgets = {
            "name":        forms.TextInput(attrs={"placeholder": "e.g. Maria Gonzalez", "id": "f_name"}),
            "employee_id": forms.TextInput(attrs={"placeholder": "e.g. LRD-4821",       "id": "f_empid"}),
            "email":       forms.EmailInput(attrs={"placeholder": "name@laredotx.gov",   "id": "f_email"}),
            "title":       forms.TextInput(attrs={
                "placeholder": "One-line summary of the issue",
                "id": "f_title", "maxlength": "120", "oninput": "liveRoute()",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "What happened, when it started, any error messages, steps already tried...",
                "id": "f_desc", "rows": 4, "oninput": "liveRoute()",
            }),
            "asset_tag":   forms.TextInput(attrs={"placeholder": "e.g. LRD-PC-0042", "id": "f_asset"}),
            "location":    forms.TextInput(attrs={"placeholder": "e.g. City Hall, Rm 204", "id": "f_loc"}),
            "phone_ext":   forms.TextInput(attrs={"placeholder": "e.g. x3412", "id": "f_ext"}),
        }
