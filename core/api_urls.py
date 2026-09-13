from django.urls import path

from core import api

urlpatterns = [
    path("workspace/", api.workspace_api, name="api_workspace"),
    path("opportunities/", api.opportunities_api, name="api_opportunities"),
    path("opportunities/<uuid:pk>/", api.opportunity_detail_api, name="api_opportunity_detail"),
    path(
        "opportunities/<uuid:pk>/assess/", api.opportunity_assess_api, name="api_opportunity_assess"
    ),
    path(
        "opportunities/<uuid:pk>/assessments/",
        api.opportunity_assessments_api,
        name="api_opportunity_assessments",
    ),
    path(
        "opportunities/<uuid:pk>/review/", api.opportunity_review_api, name="api_opportunity_review"
    ),
    path(
        "opportunities/<uuid:pk>/experiments/",
        api.opportunity_experiment_api,
        name="api_opportunity_experiment",
    ),
    path("evidence/", api.evidence_api, name="api_evidence"),
    path("evidence/<uuid:pk>/link/", api.evidence_link_api, name="api_evidence_link"),
    path("experiments/", api.experiments_api, name="api_experiments"),
    path(
        "experiments/<uuid:pk>/outcome/", api.experiment_outcome_api, name="api_experiment_outcome"
    ),
    path("sources/", api.sources_api, name="api_sources"),
    path("sources/<uuid:pk>/run/", api.source_run_api, name="api_source_run"),
    path("sources/<uuid:pk>/toggle/", api.source_toggle_api, name="api_source_toggle"),
    path("jobs/", api.jobs_api, name="api_jobs"),
    path("events/", api.events_api, name="api_events"),
]
