from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
    path("readyz/", views.readyz, name="readyz"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("", views.dashboard, name="dashboard"),
    path("brief/", views.brief_view, name="brief"),
    path("opportunities/", views.opportunity_list, name="opportunity_list"),
    path("opportunities/new/", views.opportunity_create, name="opportunity_create"),
    path("opportunities/<uuid:pk>/", views.opportunity_detail, name="opportunity_detail"),
    path("opportunities/<uuid:pk>/edit/", views.opportunity_edit, name="opportunity_edit"),
    path("opportunities/<uuid:pk>/assess/", views.opportunity_assess, name="opportunity_assess"),
    path("opportunities/<uuid:pk>/review/", views.opportunity_review, name="opportunity_review"),
    path("opportunities/<uuid:pk>/experiment/", views.experiment_start, name="experiment_start"),
    path("evidence/", views.evidence_list, name="evidence_list"),
    path("evidence/new/", views.evidence_create, name="evidence_create"),
    path("evidence/<uuid:pk>/link/", views.evidence_link, name="evidence_link"),
    path("experiments/", views.experiment_list, name="experiment_list"),
    path("experiments/<uuid:pk>/outcome/", views.experiment_outcome, name="experiment_outcome"),
    path("sources/", views.source_list, name="source_list"),
    path("sources/new/", views.source_create, name="source_create"),
    path("sources/<uuid:pk>/run/", views.source_run, name="source_run"),
    path("sources/<uuid:pk>/toggle/", views.source_toggle, name="source_toggle"),
    path("jobs/", views.job_list, name="job_list"),
    path("events/", views.event_list, name="event_list"),
    path("api/v1/", include("core.api_urls")),
]
