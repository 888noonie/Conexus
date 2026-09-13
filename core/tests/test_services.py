from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Experiment
from core.research import run_ai_review
from core.services import (
    ServiceError,
    create_evidence,
    create_monitor,
    create_opportunity,
    create_workspace_user,
    get_workspace,
    queue_collection,
    record_outcome,
    run_assessment,
    start_experiment,
    update_brief,
    update_opportunity,
)


class WorkspaceTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123", "Test workspace")
        self.user = User.objects.get(username="founder")

    def test_get_workspace(self):
        ws = get_workspace(self.user)
        self.assertEqual(ws.name, "Test workspace")

    def test_update_brief(self):
        update_brief(
            self.ws,
            {
                "name": "Updated",
                "experiment_budget": "100.00",
                "weekly_hours": "10.00",
            },
        )
        self.ws.refresh_from_db()
        self.assertEqual(self.ws.name, "Updated")
        self.assertEqual(self.ws.experiment_budget, Decimal("100.00"))


class OpportunityTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123")
        self.user = User.objects.get(username="founder")

    def _create_opp(self):
        return create_opportunity(
            self.ws,
            {
                "title": "Test opp",
                "field": "SaaS",
                "problem": "A problem",
                "buyer": "Small business owner",
                "reach": "LinkedIn outreach",
                "status": "inbox",
            },
        )

    def test_create_opportunity(self):
        opp = self._create_opp()
        self.assertEqual(opp.title, "Test opp")

    def test_foreign_opportunity_returns_404(self):
        other = create_workspace_user("other", "testpass123")
        opp = self._create_opp()
        with self.assertRaises(ServiceError) as ctx:
            update_opportunity(other, opp, {"title": "Hacked"})
        self.assertEqual(ctx.exception.status, 404)


class EvidenceTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123")

    def test_deduplication(self):
        create_evidence(self.ws, {"title": "A", "body": "Same content"})
        with self.assertRaises(ServiceError) as ctx:
            create_evidence(self.ws, {"title": "B", "body": "Same content"})
        self.assertEqual(ctx.exception.status, 409)

    def test_invalid_url(self):
        with self.assertRaises(ServiceError):
            create_evidence(self.ws, {"title": "A", "body": "B", "url": "ftp://bad.com"})


class ExperimentTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123")
        update_brief(self.ws, {"experiment_budget": "200.00", "weekly_hours": "20.00"})
        self.opp = create_opportunity(
            self.ws,
            {
                "title": "Test",
                "field": "SaaS",
                "problem": "Problem",
                "buyer": "Buyer",
                "reach": "Reach",
                "status": "inbox",
            },
        )

    def test_start_experiment(self):
        exp = start_experiment(
            self.ws,
            self.opp,
            {
                "hypothesis": "They will pay",
                "action": "Offer pilot",
                "success_criteria": "One sale",
                "stop_criteria": "No sale by deadline",
                "budget": "50.00",
                "deadline": date.today() + timedelta(days=30),
            },
        )
        self.assertEqual(exp.status, Experiment.STATUS_ACTIVE)
        self.assertIn("opportunity", exp.snapshot)

    def test_one_active_experiment(self):
        start_experiment(
            self.ws,
            self.opp,
            {
                "hypothesis": "H1",
                "action": "A1",
                "success_criteria": "S1",
                "stop_criteria": "T1",
                "budget": "50.00",
                "deadline": date.today() + timedelta(days=30),
            },
        )
        opp2 = create_opportunity(
            self.ws,
            {
                "title": "Second",
                "field": "SaaS",
                "problem": "P",
                "buyer": "B",
                "reach": "R",
                "status": "inbox",
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            start_experiment(
                self.ws,
                opp2,
                {
                    "hypothesis": "H2",
                    "action": "A2",
                    "success_criteria": "S2",
                    "stop_criteria": "T2",
                    "budget": "50.00",
                    "deadline": date.today() + timedelta(days=30),
                },
            )
        self.assertEqual(ctx.exception.status, 409)

    def test_budget_exceeds_limit(self):
        with self.assertRaises(ServiceError):
            start_experiment(
                self.ws,
                self.opp,
                {
                    "hypothesis": "H",
                    "action": "A",
                    "success_criteria": "S",
                    "stop_criteria": "T",
                    "budget": "500.00",
                    "deadline": date.today() + timedelta(days=30),
                },
            )

    def test_record_outcome(self):
        exp = start_experiment(
            self.ws,
            self.opp,
            {
                "hypothesis": "H",
                "action": "A",
                "success_criteria": "S",
                "stop_criteria": "T",
                "budget": "50.00",
                "deadline": date.today() + timedelta(days=30),
            },
        )
        record_outcome(
            self.ws,
            exp,
            {
                "status": "completed",
                "outcome": "No sales",
                "actual_spend": "10.00",
                "revenue": "0.00",
                "paying_customers": 0,
            },
        )
        exp.refresh_from_db()
        self.assertEqual(exp.status, Experiment.STATUS_COMPLETED)
        with self.assertRaises(ServiceError):
            record_outcome(
                self.ws,
                exp,
                {
                    "status": "completed",
                    "outcome": "Again",
                    "actual_spend": "0.00",
                    "revenue": "0.00",
                    "paying_customers": 0,
                },
            )

    def test_block_edit_during_active_experiment(self):
        start_experiment(
            self.ws,
            self.opp,
            {
                "hypothesis": "H",
                "action": "A",
                "success_criteria": "S",
                "stop_criteria": "T",
                "budget": "50.00",
                "deadline": date.today() + timedelta(days=30),
            },
        )
        with self.assertRaises(ServiceError):
            update_opportunity(self.ws, self.opp, {"title": "Changed"})


class AssessmentTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123")
        self.opp = create_opportunity(
            self.ws,
            {
                "title": "Test",
                "field": "SaaS",
                "problem": "Problem",
                "status": "inbox",
            },
        )

    def test_rules_assessment(self):
        assessment = run_assessment(self.ws, self.opp)
        checks = {item["check"] for item in assessment.report["items"]}
        self.assertIn("buyer", checks)
        self.assertIn("evidence", checks)


class MonitorTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123")

    def test_max_monitors(self):
        from django.conf import settings

        for i in range(settings.MAX_MONITORS_PER_WORKSPACE):
            create_monitor(
                self.ws,
                {"name": f"M{i}", "adapter": "hackernews", "query": "test", "interval_hours": 24},
            )
        with self.assertRaises(ServiceError):
            create_monitor(
                self.ws,
                {"name": "Extra", "adapter": "hackernews", "query": "test", "interval_hours": 24},
            )

    def test_pending_collection_job(self):
        monitor = create_monitor(
            self.ws,
            {"name": "HN", "adapter": "hackernews", "query": "django", "interval_hours": 24},
        )
        queue_collection(self.ws, monitor)
        with self.assertRaises(ServiceError) as ctx:
            queue_collection(self.ws, monitor)
        self.assertEqual(ctx.exception.status, 409)


class AIReviewTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("founder", "testpass123")
        self.opp = create_opportunity(
            self.ws,
            {
                "title": "Test",
                "field": "SaaS",
                "problem": "Problem",
                "status": "inbox",
            },
        )
        self.ev = create_evidence(
            self.ws,
            {"title": "Note", "body": "Some evidence", "opportunity": str(self.opp.id)},
        )

    def test_valid_citations(self):
        mock = f"Review draft citing [{self.ev.id}] as support."
        assessment = run_ai_review(self.opp, mock_response=mock)
        self.assertEqual(assessment.method, "ai-draft")

    def test_invalid_citations(self):
        import uuid

        fake_id = str(uuid.uuid4())
        mock = f"Review citing [{fake_id}] incorrectly."
        with self.assertRaises(ValueError):
            run_ai_review(self.opp, mock_response=mock)
