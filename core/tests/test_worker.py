from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from core.models import ResearchJob
from core.services import create_monitor, create_workspace_user, queue_collection


class WorkerTests(TestCase):
    def setUp(self):
        self.ws = create_workspace_user("worker", "testpass123")
        self.monitor = create_monitor(
            self.ws,
            {"name": "HN", "adapter": "hackernews", "query": "python", "interval_hours": 24},
        )

    @patch("core.research.fetch_hackernews")
    def test_process_collection(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "external_id": "123",
                "title": "Test story",
                "url": "https://example.com/1",
                "body": "Content",
                "source": "Hacker News",
            }
        ]
        job = queue_collection(self.ws, self.monitor)
        from core.research import process_job

        process_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, ResearchJob.STATUS_QUEUED)
        from core.management.commands.worker import Command

        cmd = Command()
        with patch.object(cmd, "_claim_job", return_value=job):
            job.status = ResearchJob.STATUS_QUEUED
            job.save()
        process_job(job)
        job.status = ResearchJob.STATUS_SUCCEEDED
        job.finished_at = timezone.now()
        job.save()
        self.assertEqual(self.ws.evidence.count(), 1)

    def test_job_claim(self):
        queue_collection(self.ws, self.monitor)
        from core.management.commands.worker import Command

        cmd = Command()
        claimed = cmd._claim_job()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.status, ResearchJob.STATUS_RUNNING)
        self.assertIsNotNone(claimed.claim_token)
