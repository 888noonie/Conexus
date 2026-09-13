#!/usr/bin/env python
"""Browser smoke test for Conexus HTML workflow."""

import os
import subprocess
import sys
import time
import uuid
from datetime import date, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conexus.settings")
os.environ.setdefault("CONEXUS_ENV", "development")

import django  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402

from core.services import create_workspace_user  # noqa: E402


def run_smoke(viewport_width=1280, viewport_height=800):
    username = f"smoke_{uuid.uuid4().hex[:8]}"
    password = "smoke-test-pass"
    create_workspace_user(username, password, "Smoke test workspace")

    env = os.environ.copy()
    env["DATABASE_URL"] = ""
    env["DJANGO_SETTINGS_MODULE"] = "conexus.settings"
    env["CONEXUS_ENV"] = "development"

    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8765", "--noreload"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
            base = "http://127.0.0.1:8765"

            page.goto(f"{base}/login/")
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_url(f"{base}/")

            assert "Dashboard" in page.content()

            page.goto(f"{base}/brief/")
            page.fill('input[name="name"]', "Smoke workspace")
            page.fill('input[name="experiment_budget"]', "100")
            page.fill('input[name="weekly_hours"]', "10")
            page.click('button[type="submit"]')

            page.goto(f"{base}/opportunities/new/")
            page.fill('input[name="title"]', "Smoke opportunity")
            page.fill('input[name="field"]', "Testing")
            page.fill('textarea[name="problem"]', "A test problem")
            page.fill('textarea[name="buyer"]', "Test buyer")
            page.fill('textarea[name="reach"]', "Test reach")
            page.click('button[type="submit"]')

            page.goto(f"{base}/evidence/new/")
            page.fill('input[name="title"]', "Smoke evidence")
            page.fill('textarea[name="body"]', "Test evidence body")
            page.click('button[type="submit"]')

            page.goto(f"{base}/opportunities/")
            page.click('a[href*="/opportunities/"]')
            page.click('button:has-text("Run checklist")')

            page.click('a:has-text("Start experiment")')
            page.fill('textarea[name="hypothesis"]', "Test hypothesis")
            page.fill('textarea[name="action"]', "Test action")
            page.fill('textarea[name="success_criteria"]', "Success")
            page.fill('textarea[name="stop_criteria"]', "Stop")
            page.fill('input[name="budget"]', "50")
            deadline = (date.today() + timedelta(days=30)).isoformat()
            page.fill('input[name="deadline"]', deadline)
            page.click('button[type="submit"]')

            page.goto(f"{base}/experiments/")
            assert "active" in page.content().lower()

            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 5")
            assert not overflow, f"Horizontal overflow at {viewport_width}px"

            browser.close()
    finally:
        server.terminate()
        server.wait()
        User.objects.filter(username=username).delete()


if __name__ == "__main__":
    run_smoke(1280, 800)
    print("Desktop smoke test passed")
    run_smoke(375, 667)
    print("Mobile smoke test passed")
