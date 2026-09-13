from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from core.forms import (
    BriefForm,
    EvidenceForm,
    EvidenceLinkForm,
    ExperimentForm,
    OpportunityForm,
    OutcomeForm,
    SourceMonitorForm,
)
from core.models import Evidence, Experiment, Opportunity, SourceMonitor
from core.services import (
    ServiceError,
    check_rate_limit,
    create_evidence,
    create_monitor,
    create_opportunity,
    get_workspace,
    link_evidence,
    queue_collection,
    queue_review,
    record_outcome,
    run_assessment,
    start_experiment,
    toggle_monitor,
    update_brief,
    update_opportunity,
)


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def readyz(request):
    try:
        connection.ensure_connection()
        return HttpResponse("ready", content_type="text/plain")
    except Exception:
        return HttpResponse("not ready", status=503, content_type="text/plain")


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        if not check_rate_limit(request.user.id if request.user.is_authenticated else 0, 60):
            messages.error(request, "Too many requests. Try again shortly.")
            return render(request, "login.html")
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid credentials.")
    return render(request, "login.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if not settings.ALLOW_SIGNUP:
        return HttpResponse("Registration disabled", status=404)
    if request.method == "POST":
        from core.services import create_workspace_user

        try:
            create_workspace_user(
                request.POST.get("username", ""),
                request.POST.get("password", ""),
            )
            user = authenticate(
                request,
                username=request.POST.get("username"),
                password=request.POST.get("password"),
            )
            if user:
                login(request, user)
            return redirect("dashboard")
        except ServiceError as e:
            messages.error(request, e.message)
    return render(request, "signup.html")


def _rate_limited(request, limit=60):
    if not request.user.is_authenticated:
        return False
    return check_rate_limit(request.user.id, limit)


@login_required
def dashboard(request):
    ws = get_workspace(request.user)
    active = Experiment.objects.filter(workspace=ws, status=Experiment.STATUS_ACTIVE).first()
    return render(
        request,
        "dashboard.html",
        {
            "workspace": ws,
            "opportunity_count": ws.opportunities.count(),
            "evidence_count": ws.evidence.count(),
            "active_experiment": active,
            "recent_jobs": ws.jobs.order_by("-created_at")[:5],
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def brief_view(request):
    ws = get_workspace(request.user)
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("brief")
        form = BriefForm(request.POST)
        if form.is_valid():
            update_brief(ws, form.cleaned_data)
            messages.success(request, "Operating brief saved.")
            return redirect("brief")
    else:
        form = BriefForm(
            initial={
                "name": ws.name,
                "monthly_income_target": ws.monthly_income_target,
                "experiment_budget": ws.experiment_budget,
                "weekly_hours": ws.weekly_hours,
                "target_date": ws.target_date,
                "focus_fields": ws.focus_fields,
                "constraints": ws.constraints,
            }
        )
    return render(request, "brief.html", {"form": form, "workspace": ws})


@login_required
def opportunity_list(request):
    ws = get_workspace(request.user)
    opps = ws.opportunities.all()[:50]
    return render(request, "opportunity_list.html", {"opportunities": opps})


@login_required
@require_http_methods(["GET", "POST"])
def opportunity_create(request):
    ws = get_workspace(request.user)
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("opportunity_create")
        form = OpportunityForm(request.POST)
        if form.is_valid():
            create_opportunity(ws, form.cleaned_data)
            messages.success(request, "Opportunity created.")
            return redirect("opportunity_list")
    else:
        form = OpportunityForm(initial={"status": Opportunity.STATUS_INBOX})
    return render(request, "opportunity_form.html", {"form": form, "title": "New opportunity"})


@login_required
def opportunity_detail(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    assessments = opp.assessments.all()[:10]
    active_exp = Experiment.objects.filter(opportunity=opp, status=Experiment.STATUS_ACTIVE).first()
    return render(
        request,
        "opportunity_detail.html",
        {
            "opportunity": opp,
            "assessments": assessments,
            "evidence": opp.evidence.all()[:20],
            "active_experiment": active_exp,
            "ai_configured": bool(settings.LLM_BASE_URL and settings.LLM_MODEL),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def opportunity_edit(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("opportunity_edit", pk=pk)
        form = OpportunityForm(request.POST)
        if form.is_valid():
            try:
                update_opportunity(ws, opp, form.cleaned_data)
                messages.success(request, "Opportunity updated.")
                return redirect("opportunity_detail", pk=pk)
            except ServiceError as e:
                messages.error(request, e.message)
    else:
        form = OpportunityForm(
            initial={
                "title": opp.title,
                "field": opp.field,
                "problem": opp.problem,
                "buyer": opp.buyer,
                "reach": opp.reach,
                "workaround": opp.workaround,
                "advantage": opp.advantage,
                "delivery": opp.delivery,
                "status": opp.status,
                "price": opp.price,
                "variable_cost": opp.variable_cost,
                "hours_per_sale": opp.hours_per_sale,
                "hourly_value": opp.hourly_value,
            }
        )
    return render(request, "opportunity_form.html", {"form": form, "title": "Edit opportunity"})


@login_required
@require_http_methods(["POST"])
def opportunity_assess(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    run_assessment(ws, opp)
    messages.success(request, "Evidence checklist generated.")
    return redirect("opportunity_detail", pk=pk)


@login_required
@require_http_methods(["POST"])
def opportunity_review(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    try:
        queue_review(ws, opp)
        messages.success(request, "AI review queued.")
    except ServiceError as e:
        messages.error(request, e.message)
    return redirect("opportunity_detail", pk=pk)


@login_required
@require_http_methods(["GET", "POST"])
def experiment_start(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("experiment_start", pk=pk)
        form = ExperimentForm(request.POST)
        if form.is_valid():
            try:
                start_experiment(ws, opp, form.cleaned_data)
                messages.success(request, "Experiment started.")
                return redirect("experiment_list")
            except ServiceError as e:
                messages.error(request, e.message)
    else:
        form = ExperimentForm()
    return render(request, "experiment_form.html", {"form": form, "opportunity": opp})


@login_required
def evidence_list(request):
    ws = get_workspace(request.user)
    return render(request, "evidence_list.html", {"evidence": ws.evidence.all()[:50]})


@login_required
@require_http_methods(["GET", "POST"])
def evidence_create(request):
    ws = get_workspace(request.user)
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("evidence_create")
        form = EvidenceForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data.copy()
            if data.get("opportunity"):
                data["opportunity"] = str(data["opportunity"])
            try:
                create_evidence(ws, data)
                messages.success(request, "Evidence recorded.")
                return redirect("evidence_list")
            except ServiceError as e:
                messages.error(request, e.message)
    else:
        form = EvidenceForm()
    return render(request, "evidence_form.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def evidence_link(request, pk):
    ws = get_workspace(request.user)
    ev = get_object_or_404(Evidence, pk=pk, workspace=ws)
    if request.method == "POST":
        form = EvidenceLinkForm(request.POST)
        if form.is_valid():
            link_evidence(ws, ev, form.cleaned_data["opportunity"], form.cleaned_data["stance"])
            messages.success(request, "Evidence linked.")
            return redirect("evidence_list")
    else:
        form = EvidenceLinkForm()
    return render(
        request,
        "evidence_link.html",
        {"form": form, "evidence": ev, "opportunities": ws.opportunities.all()},
    )


@login_required
def experiment_list(request):
    ws = get_workspace(request.user)
    return render(
        request,
        "experiment_list.html",
        {"experiments": ws.experiments.all()[:50]},
    )


@login_required
@require_http_methods(["GET", "POST"])
def experiment_outcome(request, pk):
    ws = get_workspace(request.user)
    exp = get_object_or_404(Experiment, pk=pk, workspace=ws)
    if exp.status != Experiment.STATUS_ACTIVE:
        messages.error(request, "Outcome already recorded.")
        return redirect("experiment_list")
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("experiment_outcome", pk=pk)
        form = OutcomeForm(request.POST)
        if form.is_valid():
            try:
                record_outcome(ws, exp, form.cleaned_data)
                messages.success(request, "Outcome recorded.")
                return redirect("experiment_list")
            except ServiceError as e:
                messages.error(request, e.message)
    else:
        form = OutcomeForm()
    return render(request, "outcome_form.html", {"form": form, "experiment": exp})


@login_required
def source_list(request):
    ws = get_workspace(request.user)
    return render(request, "source_list.html", {"monitors": ws.monitors.all()})


@login_required
@require_http_methods(["GET", "POST"])
def source_create(request):
    ws = get_workspace(request.user)
    if request.method == "POST":
        if not _rate_limited(request):
            messages.error(request, "Rate limit exceeded.")
            return redirect("source_create")
        form = SourceMonitorForm(request.POST)
        if form.is_valid():
            try:
                create_monitor(ws, form.cleaned_data)
                messages.success(request, "Source monitor created.")
                return redirect("source_list")
            except ServiceError as e:
                messages.error(request, e.message)
    else:
        form = SourceMonitorForm()
    return render(request, "source_form.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def source_run(request, pk):
    ws = get_workspace(request.user)
    monitor = get_object_or_404(SourceMonitor, pk=pk, workspace=ws)
    try:
        queue_collection(ws, monitor)
        messages.success(request, "Collection queued.")
    except ServiceError as e:
        messages.error(request, e.message)
    return redirect("source_list")


@login_required
@require_http_methods(["POST"])
def source_toggle(request, pk):
    ws = get_workspace(request.user)
    monitor = get_object_or_404(SourceMonitor, pk=pk, workspace=ws)
    toggle_monitor(ws, monitor)
    return redirect("source_list")


@login_required
def job_list(request):
    ws = get_workspace(request.user)
    return render(request, "job_list.html", {"jobs": ws.jobs.all()[:50]})


@login_required
def event_list(request):
    ws = get_workspace(request.user)
    return render(request, "event_list.html", {"events": ws.events.all()[:50]})
