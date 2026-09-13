from __future__ import annotations

import hashlib
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from core.models import (
    Assessment,
    AuditEvent,
    Evidence,
    Experiment,
    Opportunity,
    RateBucket,
    ResearchJob,
    SourceMonitor,
    Workspace,
)


class ServiceError(Exception):
    def __init__(self, message: str, status: int = 422):
        self.message = message
        self.status = status
        super().__init__(message)


def get_workspace(user: User) -> Workspace:
    try:
        return user.workspace
    except Workspace.DoesNotExist:
        raise ServiceError("No workspace found", 404) from None


def audit(workspace: Workspace, action: str, entity_id=None, detail: dict | None = None):
    AuditEvent.objects.create(
        workspace=workspace,
        action=action,
        entity_id=entity_id,
        detail=detail or {},
    )


def _parse_decimal(value, field_name: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ServiceError(f"{field_name}: invalid decimal value") from None


def update_brief(workspace: Workspace, data: dict[str, Any]) -> Workspace:
    workspace.name = data.get("name", workspace.name) or workspace.name
    workspace.monthly_income_target = _parse_decimal(
        data.get("monthly_income_target"), "monthly_income_target"
    )
    workspace.experiment_budget = _parse_decimal(data.get("experiment_budget"), "experiment_budget")
    workspace.weekly_hours = _parse_decimal(data.get("weekly_hours"), "weekly_hours")
    if data.get("target_date"):
        workspace.target_date = data["target_date"]
    workspace.focus_fields = data.get("focus_fields", workspace.focus_fields) or ""
    workspace.constraints = data.get("constraints", workspace.constraints) or ""
    workspace.save()
    audit(workspace, "brief.updated", workspace.id)
    return workspace


def create_opportunity(workspace: Workspace, data: dict[str, Any]) -> Opportunity:
    required = ["title", "field", "problem", "status"]
    for field in required:
        if not data.get(field):
            raise ServiceError(f"{field}: required")
    opp = Opportunity.objects.create(
        workspace=workspace,
        title=data["title"],
        field=data["field"],
        problem=data["problem"],
        buyer=data.get("buyer", ""),
        reach=data.get("reach", ""),
        workaround=data.get("workaround", ""),
        advantage=data.get("advantage", ""),
        delivery=data.get("delivery", ""),
        status=data["status"],
        price=_parse_decimal(data.get("price"), "price"),
        variable_cost=_parse_decimal(data.get("variable_cost"), "variable_cost"),
        hours_per_sale=_parse_decimal(data.get("hours_per_sale"), "hours_per_sale"),
        hourly_value=_parse_decimal(data.get("hourly_value"), "hourly_value"),
    )
    audit(workspace, "opportunity.created", opp.id)
    return opp


def update_opportunity(workspace: Workspace, opp: Opportunity, data: dict[str, Any]) -> Opportunity:
    if opp.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    if Experiment.objects.filter(opportunity=opp, status=Experiment.STATUS_ACTIVE).exists():
        raise ServiceError("Cannot edit opportunity with active experiment")
    for field in [
        "title",
        "field",
        "problem",
        "buyer",
        "reach",
        "workaround",
        "advantage",
        "delivery",
        "status",
    ]:
        if field in data:
            setattr(opp, field, data[field] or "")
    for money_field in ["price", "variable_cost", "hours_per_sale", "hourly_value"]:
        if money_field in data:
            setattr(opp, money_field, _parse_decimal(data[money_field], money_field))
    opp.save()
    audit(workspace, "opportunity.updated", opp.id)
    return opp


def create_evidence(workspace: Workspace, data: dict[str, Any]) -> Evidence:
    title = data.get("title", "").strip()
    body = data.get("body", "").strip()
    if not title or not body:
        raise ServiceError("title and body: required")
    url = data.get("url", "")
    if url and not url.startswith(("http://", "https://")):
        raise ServiceError("url: must be http or https")
    opportunity = None
    if data.get("opportunity"):
        opportunity = Opportunity.objects.filter(
            workspace=workspace, id=data["opportunity"]
        ).first()
        if not opportunity:
            raise ServiceError("opportunity: not found", 404)
    observed_at = data.get("observed_at") or timezone.now()
    fingerprint = Evidence.compute_fingerprint(url=url, body=body)
    if Evidence.objects.filter(workspace=workspace, fingerprint=fingerprint).exists():
        raise ServiceError("Duplicate evidence record", 409)
    ev = Evidence.objects.create(
        workspace=workspace,
        opportunity=opportunity,
        title=title,
        body=body,
        url=url,
        source=data.get("source", ""),
        kind=data.get("kind", Evidence.KIND_OBSERVED),
        stance=data.get("stance", Evidence.STANCE_CONTEXT),
        fingerprint=fingerprint,
        observed_at=observed_at,
    )
    audit(workspace, "evidence.created", ev.id)
    return ev


def link_evidence(workspace: Workspace, ev: Evidence, opportunity_id, stance: str) -> Evidence:
    if ev.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    opp = Opportunity.objects.filter(workspace=workspace, id=opportunity_id).first()
    if not opp:
        raise ServiceError("opportunity: not found", 404)
    ev.opportunity = opp
    ev.stance = stance
    ev.save()
    audit(workspace, "evidence.linked", ev.id, {"opportunity": str(opp.id), "stance": stance})
    return ev


def run_assessment(workspace: Workspace, opp: Opportunity) -> Assessment:
    if opp.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    evidence = list(opp.evidence.all())
    items = []
    if not opp.buyer.strip():
        items.append({"check": "buyer", "status": "missing", "detail": "No identifiable buyer"})
    if not opp.reach.strip():
        items.append({"check": "reach", "status": "missing", "detail": "No route to reach buyer"})
    if not evidence:
        items.append({"check": "evidence", "status": "missing", "detail": "No linked evidence"})
    challenging = [e for e in evidence if e.stance == Evidence.STANCE_CHALLENGES]
    if not challenging:
        items.append(
            {
                "check": "counterevidence",
                "status": "missing",
                "detail": "No challenging evidence recorded",
            }
        )
    if opp.price is None and opp.variable_cost is None:
        items.append(
            {"check": "economics", "status": "unknown", "detail": "No contribution estimates"}
        )
    if workspace.constraints and workspace.constraints.strip():
        items.append(
            {"check": "constraints", "status": "noted", "detail": workspace.constraints[:200]}
        )
    if workspace.experiment_budget is None:
        items.append(
            {
                "check": "budget",
                "status": "missing",
                "detail": "Operating brief has no experiment budget",
            }
        )
    report = {"items": items, "generated_at": timezone.now().isoformat()}
    snapshot = {
        "opportunity_id": str(opp.id),
        "evidence_count": len(evidence),
        "brief_budget": str(workspace.experiment_budget) if workspace.experiment_budget else None,
    }
    assessment = Assessment.objects.create(
        opportunity=opp,
        method=Assessment.METHOD_RULES,
        report=report,
        input_snapshot=snapshot,
    )
    audit(workspace, "assessment.created", assessment.id, {"opportunity": str(opp.id)})
    return assessment


def _build_experiment_snapshot(workspace: Workspace, opp: Opportunity) -> dict:
    evidence = list(opp.evidence.all()[:200])
    return {
        "opportunity": {
            "id": str(opp.id),
            "title": opp.title,
            "field": opp.field,
            "problem": opp.problem,
            "buyer": opp.buyer,
            "reach": opp.reach,
            "workaround": opp.workaround,
            "advantage": opp.advantage,
            "delivery": opp.delivery,
            "price": str(opp.price) if opp.price is not None else None,
            "variable_cost": str(opp.variable_cost) if opp.variable_cost is not None else None,
        },
        "brief": {
            "experiment_budget": str(workspace.experiment_budget)
            if workspace.experiment_budget
            else None,
            "weekly_hours": str(workspace.weekly_hours) if workspace.weekly_hours else None,
            "constraints": workspace.constraints,
        },
        "evidence": [
            {"id": str(e.id), "title": e.title, "stance": e.stance, "kind": e.kind}
            for e in evidence
        ],
        "assessments": list(
            opp.assessments.order_by("-created_at")[:5].values("id", "method", "created_at")
        ),
    }


@transaction.atomic
def start_experiment(workspace: Workspace, opp: Opportunity, data: dict[str, Any]) -> Experiment:
    if opp.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    Workspace.objects.select_for_update().get(id=workspace.id)
    if Experiment.objects.filter(workspace=workspace, status=Experiment.STATUS_ACTIVE).exists():
        raise ServiceError("An active experiment already exists", 409)
    if not opp.buyer.strip():
        raise ServiceError("buyer: required before experiment")
    if not opp.reach.strip():
        raise ServiceError("reach: required before experiment")
    if workspace.experiment_budget is None:
        raise ServiceError("experiment_budget: set operating brief first")
    if workspace.weekly_hours is None:
        raise ServiceError("weekly_hours: set operating brief first")
    budget = _parse_decimal(data.get("budget"), "budget")
    if budget is None:
        raise ServiceError("budget: required")
    if budget > workspace.experiment_budget:
        raise ServiceError("budget: exceeds workspace limit")
    deadline = data.get("deadline")
    if not deadline:
        raise ServiceError("deadline: required")
    if isinstance(deadline, str):
        from django.utils.dateparse import parse_date

        parsed_deadline = parse_date(deadline)
        if not parsed_deadline:
            raise ServiceError("deadline: invalid date")
        deadline = parsed_deadline
    if deadline < date.today():
        raise ServiceError("deadline: must not be in the past")
    for field in ["hypothesis", "action", "success_criteria", "stop_criteria"]:
        if not data.get(field, "").strip():
            raise ServiceError(f"{field}: required")
    snapshot = _build_experiment_snapshot(workspace, opp)
    exp = Experiment.objects.create(
        workspace=workspace,
        opportunity=opp,
        hypothesis=data["hypothesis"],
        action=data["action"],
        success_criteria=data["success_criteria"],
        stop_criteria=data["stop_criteria"],
        budget=budget,
        deadline=deadline,
        snapshot=snapshot,
    )
    audit(workspace, "experiment.started", exp.id)
    return exp


@transaction.atomic
def record_outcome(workspace: Workspace, exp: Experiment, data: dict[str, Any]) -> Experiment:
    if exp.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    if exp.status != Experiment.STATUS_ACTIVE:
        raise ServiceError("Experiment is not active")
    status = data.get("status")
    if status not in (Experiment.STATUS_COMPLETED, Experiment.STATUS_STOPPED):
        raise ServiceError("status: must be completed or stopped")
    outcome = data.get("outcome", "").strip()
    if not outcome:
        raise ServiceError("outcome: required")
    actual_spend = _parse_decimal(data.get("actual_spend"), "actual_spend")
    revenue = _parse_decimal(data.get("revenue"), "revenue")
    paying_customers = data.get("paying_customers")
    if actual_spend is None or revenue is None or paying_customers is None:
        raise ServiceError("actual_spend, revenue, and paying_customers: required")
    exp.status = status
    exp.outcome = outcome
    exp.actual_spend = actual_spend
    exp.revenue = revenue
    exp.paying_customers = int(paying_customers)
    exp.completed_at = timezone.now()
    exp.save()
    audit(workspace, "experiment.outcome", exp.id, {"status": status})
    return exp


def create_monitor(workspace: Workspace, data: dict[str, Any]) -> SourceMonitor:
    count = SourceMonitor.objects.filter(workspace=workspace).count()
    if count >= settings.MAX_MONITORS_PER_WORKSPACE:
        raise ServiceError("Maximum monitors reached", 422)
    adapter = data.get("adapter")
    if adapter not in (SourceMonitor.ADAPTER_HN, SourceMonitor.ADAPTER_RSS):
        raise ServiceError("adapter: invalid")
    interval = int(data.get("interval_hours", 24))
    if interval < 1:
        raise ServiceError("interval_hours: minimum is 1")
    feed_url = data.get("feed_url", "")
    if adapter == SourceMonitor.ADAPTER_RSS:
        if not feed_url:
            raise ServiceError("feed_url: required for RSS")
        if feed_url not in settings.RSS_FEEDS:
            raise ServiceError("feed_url: not in approved RSS_FEEDS list")
    monitor = SourceMonitor.objects.create(
        workspace=workspace,
        name=data.get("name", "Monitor"),
        adapter=adapter,
        query=data.get("query", ""),
        feed_url=feed_url,
        interval_hours=interval,
        enabled=True,
        next_run_at=timezone.now(),
    )
    audit(workspace, "monitor.created", monitor.id)
    return monitor


def toggle_monitor(workspace: Workspace, monitor: SourceMonitor) -> SourceMonitor:
    if monitor.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    monitor.enabled = not monitor.enabled
    if monitor.enabled and not monitor.next_run_at:
        monitor.next_run_at = timezone.now()
    monitor.save()
    audit(workspace, "monitor.toggled", monitor.id, {"enabled": monitor.enabled})
    return monitor


def _daily_job_count(workspace: Workspace) -> int:
    since = timezone.now() - timedelta(hours=24)
    return ResearchJob.objects.filter(workspace=workspace, created_at__gte=since).count()


def _check_job_quota(workspace: Workspace):
    if _daily_job_count(workspace) >= settings.DEFAULT_DAILY_JOB_LIMIT:
        raise ServiceError("Daily research job limit reached", 429)


def queue_collection(workspace: Workspace, monitor: SourceMonitor) -> ResearchJob:
    if monitor.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    _check_job_quota(workspace)
    if ResearchJob.objects.filter(
        monitor=monitor, status__in=[ResearchJob.STATUS_QUEUED, ResearchJob.STATUS_RUNNING]
    ).exists():
        raise ServiceError("Collection already pending", 409)
    job = ResearchJob.objects.create(
        workspace=workspace,
        monitor=monitor,
        kind=ResearchJob.KIND_COLLECTION,
        status=ResearchJob.STATUS_QUEUED,
        available_at=timezone.now(),
    )
    audit(workspace, "job.queued", job.id, {"kind": "collection"})
    return job


def queue_review(workspace: Workspace, opp: Opportunity) -> ResearchJob:
    if opp.workspace_id != workspace.id:
        raise ServiceError("Not found", 404)
    if not settings.LLM_BASE_URL or not settings.LLM_MODEL:
        raise ServiceError("AI review not configured", 422)
    _check_job_quota(workspace)
    if ResearchJob.objects.filter(
        opportunity=opp,
        kind=ResearchJob.KIND_REVIEW,
        status__in=[ResearchJob.STATUS_QUEUED, ResearchJob.STATUS_RUNNING],
    ).exists():
        raise ServiceError("Review already pending", 409)
    job = ResearchJob.objects.create(
        workspace=workspace,
        opportunity=opp,
        kind=ResearchJob.KIND_REVIEW,
        status=ResearchJob.STATUS_QUEUED,
        available_at=timezone.now(),
    )
    audit(workspace, "job.queued", job.id, {"kind": "review"})
    return job


def create_workspace_user(username: str, password: str, name: str = "My workspace") -> Workspace:
    if User.objects.filter(username=username).exists():
        raise ServiceError("Username already exists", 409)
    user = User.objects.create_user(username=username, password=password)
    workspace = Workspace.objects.create(owner=user, name=name)
    audit(workspace, "workspace.created", workspace.id)
    return workspace


def _hash_rate_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def check_rate_limit(user_id: int, limit: int, window_seconds: int = 60) -> bool:
    now = timezone.now()
    window_start = now.replace(second=0, microsecond=0)
    if window_seconds == 60:
        key_raw = f"user:{user_id}:{window_start.isoformat()}"
    else:
        key_raw = f"user:{user_id}:{int(now.timestamp()) // window_seconds}"
    key = _hash_rate_key(key_raw)
    with transaction.atomic():
        bucket, created = RateBucket.objects.select_for_update().get_or_create(
            key=key,
            defaults={"window": window_start, "count": 0},
        )
        if bucket.count >= limit:
            return False
        bucket.count += 1
        bucket.save()
    return True


def prune_rate_limits():
    cutoff = timezone.now() - timedelta(days=2)
    RateBucket.objects.filter(updated_at__lt=cutoff).delete()
