from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from core.services import create_evidence, create_opportunity, get_workspace, run_assessment


class Command(BaseCommand):
    help = "Seed fictional demo data for development"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)

    def handle(self, *args, **options):
        user = User.objects.filter(username=options["username"]).first()
        if not user:
            raise CommandError("User not found")
        ws = get_workspace(user)
        opp = create_opportunity(
            ws,
            {
                "title": "[FICTIONAL] Missed handover recovery",
                "field": "Business operations",
                "problem": "Hypothesis: small service teams lose time recovering missing context.",
                "buyer": "Owner of a small service company",
                "reach": "Ask a professional contact for an introduction",
                "status": "inbox",
                "price": "100.00",
                "variable_cost": "15.00",
                "hours_per_sale": "2.00",
                "hourly_value": "25.00",
            },
        )
        create_evidence(
            ws,
            {
                "title": "[FICTIONAL] Forum discussion excerpt",
                "body": (
                    "Illustrative only — not validated demand. "
                    "Operators report context loss during shift changes."
                ),
                "source": "Fictional sample",
                "kind": "hypothesis",
                "stance": "context",
                "opportunity": str(opp.id),
            },
        )
        create_evidence(
            ws,
            {
                "title": "[FICTIONAL] Counterpoint",
                "body": "Some teams report existing tools already cover this workflow adequately.",
                "source": "Fictional sample",
                "kind": "observed",
                "stance": "challenges",
                "opportunity": str(opp.id),
            },
        )
        run_assessment(ws, opp)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded fictional demo data for {options['username']}")
        )
