import hashlib
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="workspace")
    name = models.CharField(max_length=120)
    monthly_income_target = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    experiment_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    weekly_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    target_date = models.DateField(null=True, blank=True)
    focus_fields = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Opportunity(models.Model):
    STATUS_INBOX = "inbox"
    STATUS_PARKED = "parked"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_INBOX, "Investigating"),
        (STATUS_PARKED, "Parked"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="opportunities")
    title = models.CharField(max_length=200)
    field = models.CharField(max_length=120)
    problem = models.TextField()
    buyer = models.TextField(blank=True)
    reach = models.TextField(blank=True)
    workaround = models.TextField(blank=True)
    advantage = models.TextField(blank=True)
    delivery = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INBOX)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    variable_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hours_per_sale = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    hourly_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "-created_at"]),
            models.Index(fields=["workspace", "status"]),
        ]

    def __str__(self):
        return self.title


class Evidence(models.Model):
    KIND_OBSERVED = "observed"
    KIND_INFERRED = "inferred"
    KIND_HYPOTHESIS = "hypothesis"
    KIND_UNKNOWN = "unknown"
    KIND_COUNTERFACTUAL = "counterfactual"
    KIND_CHOICES = [
        (KIND_OBSERVED, "Observed"),
        (KIND_INFERRED, "Inferred"),
        (KIND_HYPOTHESIS, "Hypothesis"),
        (KIND_UNKNOWN, "Unknown"),
        (KIND_COUNTERFACTUAL, "Counterfactual"),
    ]

    STANCE_SUPPORTS = "supports"
    STANCE_CHALLENGES = "challenges"
    STANCE_CONTEXT = "context"
    STANCE_CHOICES = [
        (STANCE_SUPPORTS, "Supports"),
        (STANCE_CHALLENGES, "Challenges"),
        (STANCE_CONTEXT, "Context"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="evidence")
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name="evidence"
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    url = models.URLField(blank=True, max_length=500)
    source = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_OBSERVED)
    stance = models.CharField(max_length=20, choices=STANCE_CHOICES, default=STANCE_CONTEXT)
    fingerprint = models.CharField(max_length=64)
    observed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "fingerprint"],
                name="unique_workspace_evidence",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "-observed_at"]),
            models.Index(fields=["workspace", "opportunity"]),
        ]

    @staticmethod
    def compute_fingerprint(url="", body="", adapter="", external_id=""):
        raw = f"{adapter}|{external_id}|{url}|{body}".encode()
        return hashlib.sha256(raw).hexdigest()

    def __str__(self):
        return self.title


class Assessment(models.Model):
    METHOD_RULES = "rules-v1"
    METHOD_AI = "ai-draft"
    METHOD_CHOICES = [
        (METHOD_RULES, "Rules v1"),
        (METHOD_AI, "AI draft"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="assessments"
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    report = models.JSONField()
    input_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Experiment(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_STOPPED = "stopped"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_STOPPED, "Stopped"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="experiments")
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.PROTECT, related_name="experiments"
    )
    hypothesis = models.TextField()
    action = models.TextField()
    success_criteria = models.TextField()
    stop_criteria = models.TextField()
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    snapshot = models.JSONField(default=dict)
    outcome = models.TextField(blank=True)
    actual_spend = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    paying_customers = models.PositiveIntegerField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace"],
                condition=Q(status="active"),
                name="one_active_experiment",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "-created_at"]),
        ]


class SourceMonitor(models.Model):
    ADAPTER_HN = "hackernews"
    ADAPTER_RSS = "rss"
    ADAPTER_CHOICES = [
        (ADAPTER_HN, "Hacker News"),
        (ADAPTER_RSS, "RSS"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="monitors")
    name = models.CharField(max_length=120)
    adapter = models.CharField(max_length=20, choices=ADAPTER_CHOICES)
    query = models.CharField(max_length=200, blank=True)
    feed_url = models.URLField(blank=True, max_length=500)
    interval_hours = models.PositiveIntegerField(default=24)
    enabled = models.BooleanField(default=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["enabled", "next_run_at"]),
            models.Index(fields=["workspace"]),
        ]


class ResearchJob(models.Model):
    KIND_COLLECTION = "collection"
    KIND_REVIEW = "review"
    KIND_CHOICES = [
        (KIND_COLLECTION, "Collection"),
        (KIND_REVIEW, "Review"),
    ]

    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="jobs")
    monitor = models.ForeignKey(
        SourceMonitor, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs"
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name="jobs"
    )
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    attempts = models.PositiveIntegerField(default=0)
    available_at = models.DateTimeField()
    lease_until = models.DateTimeField(null=True, blank=True)
    claim_token = models.UUIDField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["workspace", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["monitor"],
                condition=Q(status__in=["queued", "running"], kind="collection"),
                name="one_pending_monitor_job",
            ),
            models.UniqueConstraint(
                fields=["opportunity"],
                condition=Q(status__in=["queued", "running"], kind="review"),
                name="one_pending_review_job",
            ),
        ]


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="events")
    action = models.CharField(max_length=80)
    entity_id = models.UUIDField(null=True, blank=True)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "-created_at"]),
        ]


class RateBucket(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    window = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
