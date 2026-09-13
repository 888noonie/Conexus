from __future__ import annotations

from core.models import (
    Assessment,
    AuditEvent,
    Evidence,
    Experiment,
    Opportunity,
    ResearchJob,
    SourceMonitor,
    Workspace,
)


def workspace_dict(ws: Workspace) -> dict:
    return {
        "id": str(ws.id),
        "name": ws.name,
        "monthly_income_target": _money(ws.monthly_income_target),
        "experiment_budget": _money(ws.experiment_budget),
        "weekly_hours": _money(ws.weekly_hours),
        "target_date": ws.target_date.isoformat() if ws.target_date else None,
        "focus_fields": ws.focus_fields,
        "constraints": ws.constraints,
    }


def opportunity_dict(opp: Opportunity) -> dict:
    return {
        "id": str(opp.id),
        "title": opp.title,
        "field": opp.field,
        "problem": opp.problem,
        "buyer": opp.buyer,
        "reach": opp.reach,
        "workaround": opp.workaround,
        "advantage": opp.advantage,
        "delivery": opp.delivery,
        "status": opp.status,
        "price": _money(opp.price),
        "variable_cost": _money(opp.variable_cost),
        "hours_per_sale": _money(opp.hours_per_sale),
        "hourly_value": _money(opp.hourly_value),
        "created_at": opp.created_at.isoformat(),
    }


def evidence_dict(ev: Evidence) -> dict:
    return {
        "id": str(ev.id),
        "title": ev.title,
        "body": ev.body,
        "url": ev.url,
        "source": ev.source,
        "kind": ev.kind,
        "stance": ev.stance,
        "opportunity": str(ev.opportunity_id) if ev.opportunity_id else None,
        "observed_at": ev.observed_at.isoformat(),
        "created_at": ev.created_at.isoformat(),
    }


def experiment_dict(exp: Experiment) -> dict:
    return {
        "id": str(exp.id),
        "opportunity": str(exp.opportunity_id),
        "hypothesis": exp.hypothesis,
        "action": exp.action,
        "success_criteria": exp.success_criteria,
        "stop_criteria": exp.stop_criteria,
        "budget": _money(exp.budget),
        "deadline": exp.deadline.isoformat(),
        "status": exp.status,
        "outcome": exp.outcome,
        "actual_spend": _money(exp.actual_spend),
        "revenue": _money(exp.revenue),
        "paying_customers": exp.paying_customers,
        "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
        "created_at": exp.created_at.isoformat(),
    }


def monitor_dict(m: SourceMonitor) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "adapter": m.adapter,
        "query": m.query,
        "feed_url": m.feed_url,
        "interval_hours": m.interval_hours,
        "enabled": m.enabled,
        "next_run_at": m.next_run_at.isoformat() if m.next_run_at else None,
    }


def job_dict(j: ResearchJob) -> dict:
    return {
        "id": str(j.id),
        "kind": j.kind,
        "status": j.status,
        "attempts": j.attempts,
        "error": j.error[:500] if j.error else "",
        "result": j.result,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        "created_at": j.created_at.isoformat(),
    }


def event_dict(e: AuditEvent) -> dict:
    return {
        "id": str(e.id),
        "action": e.action,
        "entity_id": str(e.entity_id) if e.entity_id else None,
        "detail": e.detail,
        "created_at": e.created_at.isoformat(),
    }


def assessment_dict(a: Assessment) -> dict:
    return {
        "id": str(a.id),
        "method": a.method,
        "report": a.report,
        "created_at": a.created_at.isoformat(),
    }


def _money(value) -> str | None:
    if value is None:
        return None
    return f"{value:.2f}"
