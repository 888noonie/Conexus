from django.core.management.base import BaseCommand

from core.services import prune_rate_limits


class Command(BaseCommand):
    help = "Remove rate limit buckets older than two days"

    def handle(self, *args, **options):
        prune_rate_limits()
        self.stdout.write(self.style.SUCCESS("Rate limit buckets pruned"))
