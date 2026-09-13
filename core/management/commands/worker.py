import time
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import ResearchJob, SourceMonitor
from core.research import process_job


class Command(BaseCommand):
    help = "Process research jobs and schedule source monitors"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run one iteration then exit")

    def handle(self, *args, **options):
        if options["once"]:
            self._schedule_monitors()
            self._process_one()
            return
        self.stdout.write("Worker started")
        while True:
            self._schedule_monitors()
            processed = self._process_one()
            if not processed:
                time.sleep(5)

    def _schedule_monitors(self):
        now = timezone.now()
        monitors = SourceMonitor.objects.filter(enabled=True, next_run_at__lte=now)
        for monitor in monitors:
            if ResearchJob.objects.filter(
                monitor=monitor,
                status__in=[ResearchJob.STATUS_QUEUED, ResearchJob.STATUS_RUNNING],
            ).exists():
                continue
            ResearchJob.objects.create(
                workspace=monitor.workspace,
                monitor=monitor,
                kind=ResearchJob.KIND_COLLECTION,
                status=ResearchJob.STATUS_QUEUED,
                available_at=now,
            )

    def _process_one(self) -> bool:
        job = self._claim_job()
        if not job:
            return False
        try:
            process_job(job)
            job.status = ResearchJob.STATUS_SUCCEEDED
            job.finished_at = timezone.now()
            job.lease_until = None
            job.save()
        except Exception as exc:
            job.attempts += 1
            job.error = str(exc)[:1000]
            if job.attempts >= settings.MAX_COLLECTION_RETRIES:
                job.status = ResearchJob.STATUS_FAILED
                job.finished_at = timezone.now()
            else:
                job.status = ResearchJob.STATUS_QUEUED
                job.available_at = timezone.now() + timezone.timedelta(minutes=job.attempts * 2)
            job.lease_until = None
            job.claim_token = None
            job.save()
        return True

    def _claim_job(self) -> ResearchJob | None:
        now = timezone.now()
        with transaction.atomic():
            job = (
                ResearchJob.objects.select_for_update(skip_locked=True)
                .filter(
                    status=ResearchJob.STATUS_QUEUED,
                    available_at__lte=now,
                )
                .order_by("available_at")
                .first()
            )
            if not job:
                return None
            token = uuid.uuid4()
            job.status = ResearchJob.STATUS_RUNNING
            job.claim_token = token
            job.lease_until = now + timezone.timedelta(seconds=settings.JOB_LEASE_SECONDS)
            job.attempts += 1
            job.save()
            return job
