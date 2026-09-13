from django import forms

from core.models import Evidence, Opportunity, SourceMonitor


class BriefForm(forms.Form):
    name = forms.CharField(max_length=120)
    monthly_income_target = forms.DecimalField(required=False, max_digits=12, decimal_places=2)
    experiment_budget = forms.DecimalField(required=False, max_digits=12, decimal_places=2)
    weekly_hours = forms.DecimalField(required=False, max_digits=6, decimal_places=2)
    target_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    focus_fields = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    constraints = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))


class OpportunityForm(forms.Form):
    title = forms.CharField(max_length=200)
    field = forms.CharField(max_length=120)
    problem = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    buyer = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    reach = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    workaround = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    advantage = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    delivery = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    status = forms.ChoiceField(choices=Opportunity.STATUS_CHOICES)
    price = forms.DecimalField(required=False, max_digits=12, decimal_places=2)
    variable_cost = forms.DecimalField(required=False, max_digits=12, decimal_places=2)
    hours_per_sale = forms.DecimalField(required=False, max_digits=8, decimal_places=2)
    hourly_value = forms.DecimalField(required=False, max_digits=12, decimal_places=2)


class EvidenceForm(forms.Form):
    title = forms.CharField(max_length=200)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 5}))
    url = forms.URLField(required=False)
    source = forms.CharField(required=False, max_length=200)
    kind = forms.ChoiceField(choices=Evidence.KIND_CHOICES)
    stance = forms.ChoiceField(choices=Evidence.STANCE_CHOICES)
    opportunity = forms.UUIDField(required=False)


class EvidenceLinkForm(forms.Form):
    opportunity = forms.UUIDField()
    stance = forms.ChoiceField(choices=Evidence.STANCE_CHOICES)


class ExperimentForm(forms.Form):
    hypothesis = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    action = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    success_criteria = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
    stop_criteria = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}))
    budget = forms.DecimalField(max_digits=12, decimal_places=2)
    deadline = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


class OutcomeForm(forms.Form):
    status = forms.ChoiceField(choices=[("completed", "Completed"), ("stopped", "Stopped")])
    outcome = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    actual_spend = forms.DecimalField(max_digits=12, decimal_places=2)
    revenue = forms.DecimalField(max_digits=12, decimal_places=2)
    paying_customers = forms.IntegerField(min_value=0)


class SourceMonitorForm(forms.Form):
    name = forms.CharField(max_length=120)
    adapter = forms.ChoiceField(choices=SourceMonitor.ADAPTER_CHOICES)
    query = forms.CharField(required=False, max_length=200)
    feed_url = forms.URLField(required=False)
    interval_hours = forms.IntegerField(min_value=1, initial=24)
