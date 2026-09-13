import getpass

from django.core.management.base import BaseCommand, CommandError

from core.services import ServiceError, create_workspace_user


class Command(BaseCommand):
    help = "Create a workspace owner account"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("--name", type=str, default="My workspace")

    def handle(self, *args, **options):
        password = getpass.getpass("Password: ")
        if not password:
            raise CommandError("Password required")
        try:
            ws = create_workspace_user(options["username"], password, options["name"])
            self.stdout.write(
                self.style.SUCCESS(f"Created workspace {ws.name} for {options['username']}")
            )
        except ServiceError as e:
            raise CommandError(e.message) from e
