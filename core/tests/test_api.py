import json
from datetime import date, timedelta

from django.test import Client, TestCase

from core.services import create_workspace_user, update_brief


class APITests(TestCase):
    def setUp(self):
        create_workspace_user("apiuser", "testpass123")
        self.client = Client(enforce_csrf_checks=True)
        self.client.login(username="apiuser", password="testpass123")

    def _csrf_headers(self):
        resp = self.client.get("/login/")
        token = resp.cookies["csrftoken"].value
        return {"HTTP_X_CSRFTOKEN": token}

    def test_workspace_get(self):
        resp = self.client.get("/api/v1/workspace/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("name", data)

    def test_workspace_update(self):
        resp = self.client.post(
            "/api/v1/workspace/",
            data=json.dumps(
                {"name": "API Workspace", "experiment_budget": "150.00", "weekly_hours": "15.00"}
            ),
            content_type="application/json",
            **self._csrf_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["name"], "API Workspace")

    def test_unauthenticated(self):
        client = Client()
        resp = client.get("/api/v1/workspace/")
        self.assertEqual(resp.status_code, 401)

    def test_create_opportunity(self):
        resp = self.client.post(
            "/api/v1/opportunities/",
            data=json.dumps(
                {
                    "title": "API opp",
                    "field": "Tech",
                    "problem": "A problem",
                    "status": "inbox",
                }
            ),
            content_type="application/json",
            **self._csrf_headers(),
        )
        self.assertEqual(resp.status_code, 201)

    def test_foreign_id_404(self):
        import uuid

        resp = self.client.get(f"/api/v1/opportunities/{uuid.uuid4()}/")
        self.assertEqual(resp.status_code, 404)

    def test_experiment_flow(self):
        from django.contrib.auth.models import User

        from core.services import get_workspace

        ws = get_workspace(User.objects.get(username="apiuser"))
        update_brief(ws, {"experiment_budget": "100.00", "weekly_hours": "10.00"})
        opp_resp = self.client.post(
            "/api/v1/opportunities/",
            data=json.dumps(
                {
                    "title": "Exp opp",
                    "field": "Tech",
                    "problem": "P",
                    "buyer": "B",
                    "reach": "R",
                    "status": "inbox",
                }
            ),
            content_type="application/json",
            **self._csrf_headers(),
        )
        opp_id = opp_resp.json()["id"]
        exp_resp = self.client.post(
            f"/api/v1/opportunities/{opp_id}/experiments/",
            data=json.dumps(
                {
                    "hypothesis": "H",
                    "action": "A",
                    "success_criteria": "S",
                    "stop_criteria": "T",
                    "budget": "50.00",
                    "deadline": (date.today() + timedelta(days=30)).isoformat(),
                }
            ),
            content_type="application/json",
            **self._csrf_headers(),
        )
        self.assertEqual(exp_resp.status_code, 201)

    def test_malformed_json(self):
        resp = self.client.post(
            "/api/v1/workspace/",
            data="not json",
            content_type="application/json",
            **self._csrf_headers(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_wrong_content_type(self):
        resp = self.client.post(
            "/api/v1/workspace/",
            data="name=test",
            content_type="text/plain",
            **self._csrf_headers(),
        )
        self.assertEqual(resp.status_code, 415)
