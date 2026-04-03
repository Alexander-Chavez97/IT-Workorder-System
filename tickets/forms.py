"""
tickets/forms.py
================
Django form for ticket submission.
Priority is no longer selected by the employee — the routing engine
determines effective priority automatically from department, category,
sub-type, and keyword detection.
"""

from django import forms
from .routing import (
    DEPARTMENT_CHOICES,
    CATEGORY_CHOICES,
    SUBTYPE_CHOICES,
    ISSUE_TYPE_CHOICES,
)
from .models import Ticket


class TicketSubmitForm(forms.ModelForm):
    """
    Form used by employees to submit a new work order.
    The category → subtype → issue_type cascade is driven by JS in submit.html.
    Server-side validation still checks against the full flat choice lists.
    """

    department = forms.ChoiceField(
        choices=[("", "— Select your department —")] + list(DEPARTMENT_CHOICES),
        widget=forms.Select(attrs={"id": "f_dept"}),
    )
    category = forms.ChoiceField(
        choices=[("", "— Select a category —")] + list(CATEGORY_CHOICES),
        widget=forms.Select(attrs={"id": "f_cat", "onchange": "onCategoryChange()"}),
    )
    subtype = forms.ChoiceField(
        choices=SUBTYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"id": "f_sub", "onchange": "onSubtypeChange()"}),
    )
    issue_type = forms.ChoiceField(
        choices=ISSUE_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"id": "f_issue"}),
    )

    class Meta:
        model = Ticket
        fields = [
            "name", "employee_id", "department", "email",
            "category", "subtype", "issue_type",
            "title", "description",
            "asset_tag", "location", "phone_ext",
        ]
        widgets = {
            "name":        forms.TextInput(attrs={
                "placeholder": "e.g. Maria Gonzalez",
                "id": "f_name",
            }),
            "employee_id": forms.TextInput(attrs={
                "placeholder": "e.g. LRD-4821",
                "id": "f_empid",
            }),
            "email":       forms.EmailInput(attrs={
                "placeholder": "name@laredotx.gov",
                "id": "f_email",
            }),
            "title":       forms.TextInput(attrs={
                "placeholder": "One-line summary of the issue",
                "id": "f_title",
                "maxlength": "120",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "What happened, when it started, any error messages, steps already tried...",
                "id": "f_desc",
                "rows": 4,
            }),
            "asset_tag":   forms.TextInput(attrs={
                "placeholder": "e.g. LRD-PC-0042",
                "id": "f_asset",
            }),
            "location":    forms.TextInput(attrs={
                "placeholder": "e.g. City Hall, Rm 204",
                "id": "f_loc",
            }),
            "phone_ext":   forms.TextInput(attrs={
                "placeholder": "e.g. x3412",
                "id": "f_ext",
            }),
        }
