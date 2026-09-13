from django.test import Client, TestCase

from core.services import create_workspace_user


class ViewTests(TestCase):
    def setUp(self):
        create_workspace_user("viewuser", "testpass123")
        self.client = Client()

    def test_login_required(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.url)

    def test_login_and_dashboard(self):
        logged_in = self.client.login(username="viewuser", password="testpass123")
        self.assertTrue(logged_in)
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dashboard")

    def test_healthz(self):
        resp = self.client.get("/healthz/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"ok")

    def test_readyz(self):
        resp = self.client.get("/readyz/")
        self.assertEqual(resp.status_code, 200)

    def test_signup_disabled(self):
        resp = self.client.get("/signup/")
        self.assertEqual(resp.status_code, 404)

    def test_csrf_on_post(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="viewuser", password="testpass123")
        resp = client.post("/brief/", {"name": "Test"})
        self.assertEqual(resp.status_code, 403)
