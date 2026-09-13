import json
from functools import wraps

from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import (
    Evidence,
    Experiment,
    Opportunity,
    SourceMonitor,
)
from core.serializers import (
    assessment_dict,
    event_dict,
    evidence_dict,
    experiment_dict,
    job_dict,
    monitor_dict,
    opportunity_dict,
    workspace_dict,
)
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


def api_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def api_rate_limit(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not check_rate_limit(request.user.id, 60):
                return JsonResponse({"error": "Rate limit exceeded"}, status=429)
        else:
            if not check_rate_limit(request.user.id, 120):
                return JsonResponse({"error": "Rate limit exceeded"}, status=429)
        return view(request, *args, **kwargs)

    return wrapper


def parse_json(request):
    if request.content_type and "application/json" not in request.content_type:
        return None, JsonResponse({"error": "Content-Type must be application/json"}, status=415)
    try:
        body = request.body.decode() or "{}"
        return json.loads(body), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Malformed JSON"}, status=400)


def paginate(queryset, request):
    page_num = request.GET.get("page", "1")
    try:
        page_num = int(page_num)
        if page_num < 1:
            raise ValueError
    except ValueError:
        return None, JsonResponse({"error": "Invalid page number"}, status=400)
    paginator = Paginator(queryset, settings.PAGE_SIZE)
    if page_num > paginator.num_pages and paginator.count > 0:
        page = paginator.page(paginator.num_pages)
        items = []
        next_page = None
    elif paginator.count == 0:
        items = []
        next_page = None
    else:
        page = paginator.page(page_num)
        items = list(page.object_list)
        next_page = page_num + 1 if page.has_next() else None
    return {"count": paginator.count, "next_page": next_page, "items": items}, None


def validation_error_response(exc: ServiceError):
    return JsonResponse({"errors": [exc.message]}, status=exc.status)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET", "POST"])
def workspace_api(request):
    ws = get_workspace(request.user)
    if request.method == "GET":
        return JsonResponse(workspace_dict(ws))
    data, err = parse_json(request)
    if err:
        return err
    try:
        update_brief(ws, data)
        return JsonResponse(workspace_dict(ws))
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET", "POST"])
def opportunities_api(request):
    ws = get_workspace(request.user)
    if request.method == "GET":
        result, err = paginate(ws.opportunities.all(), request)
        if err:
            return err
        result["items"] = [opportunity_dict(o) for o in result["items"]]
        return JsonResponse(result)
    data, err = parse_json(request)
    if err:
        return err
    try:
        opp = create_opportunity(ws, data)
        return JsonResponse(opportunity_dict(opp), status=201)
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET", "POST"])
def opportunity_detail_api(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    if request.method == "GET":
        return JsonResponse(opportunity_dict(opp))
    data, err = parse_json(request)
    if err:
        return err
    try:
        opp = update_opportunity(ws, opp, data)
        return JsonResponse(opportunity_dict(opp))
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def opportunity_assess_api(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    assessment = run_assessment(ws, opp)
    return JsonResponse(assessment_dict(assessment), status=201)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET"])
def opportunity_assessments_api(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    items = [assessment_dict(a) for a in opp.assessments.all()[:50]]
    return JsonResponse({"count": len(items), "next_page": None, "items": items})


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def opportunity_review_api(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    try:
        job = queue_review(ws, opp)
        return JsonResponse(job_dict(job), status=202)
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def opportunity_experiment_api(request, pk):
    ws = get_workspace(request.user)
    opp = get_object_or_404(Opportunity, pk=pk, workspace=ws)
    data, err = parse_json(request)
    if err:
        return err
    try:
        exp = start_experiment(ws, opp, data)
        return JsonResponse(experiment_dict(exp), status=201)
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET", "POST"])
def evidence_api(request):
    ws = get_workspace(request.user)
    if request.method == "GET":
        result, err = paginate(ws.evidence.all(), request)
        if err:
            return err
        result["items"] = [evidence_dict(e) for e in result["items"]]
        return JsonResponse(result)
    data, err = parse_json(request)
    if err:
        return err
    try:
        ev = create_evidence(ws, data)
        return JsonResponse(evidence_dict(ev), status=201)
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def evidence_link_api(request, pk):
    ws = get_workspace(request.user)
    ev = get_object_or_404(Evidence, pk=pk, workspace=ws)
    data, err = parse_json(request)
    if err:
        return err
    try:
        ev = link_evidence(ws, ev, data.get("opportunity"), data.get("stance", "context"))
        return JsonResponse(evidence_dict(ev))
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET"])
def experiments_api(request):
    ws = get_workspace(request.user)
    result, err = paginate(ws.experiments.all(), request)
    if err:
        return err
    result["items"] = [experiment_dict(e) for e in result["items"]]
    return JsonResponse(result)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def experiment_outcome_api(request, pk):
    ws = get_workspace(request.user)
    exp = get_object_or_404(Experiment, pk=pk, workspace=ws)
    data, err = parse_json(request)
    if err:
        return err
    try:
        exp = record_outcome(ws, exp, data)
        return JsonResponse(experiment_dict(exp))
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET", "POST"])
def sources_api(request):
    ws = get_workspace(request.user)
    if request.method == "GET":
        result, err = paginate(ws.monitors.all(), request)
        if err:
            return err
        result["items"] = [monitor_dict(m) for m in result["items"]]
        return JsonResponse(result)
    data, err = parse_json(request)
    if err:
        return err
    try:
        monitor = create_monitor(ws, data)
        return JsonResponse(monitor_dict(monitor), status=201)
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def source_run_api(request, pk):
    ws = get_workspace(request.user)
    monitor = get_object_or_404(SourceMonitor, pk=pk, workspace=ws)
    try:
        job = queue_collection(ws, monitor)
        return JsonResponse(job_dict(job), status=202)
    except ServiceError as e:
        return validation_error_response(e)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["POST"])
def source_toggle_api(request, pk):
    ws = get_workspace(request.user)
    monitor = get_object_or_404(SourceMonitor, pk=pk, workspace=ws)
    monitor = toggle_monitor(ws, monitor)
    return JsonResponse(monitor_dict(monitor))


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET"])
def jobs_api(request):
    ws = get_workspace(request.user)
    result, err = paginate(ws.jobs.all(), request)
    if err:
        return err
    result["items"] = [job_dict(j) for j in result["items"]]
    return JsonResponse(result)


@csrf_exempt
@api_login_required
@api_rate_limit
@require_http_methods(["GET"])
def events_api(request):
    ws = get_workspace(request.user)
    result, err = paginate(ws.events.all(), request)
    if err:
        return err
    result["items"] = [event_dict(e) for e in result["items"]]
    return JsonResponse(result)
