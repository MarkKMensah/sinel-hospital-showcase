from django.core.management.base import BaseCommand
from knox.models import AuthToken


class Command(BaseCommand):
    help = "Invalidate Knox API tokens for every user or one email address."

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument(
            "--all",
            action="store_true",
            help="Invalidate every API token.",
        )
        target.add_argument(
            "--email",
            help="Invalidate tokens belonging to one email address.",
        )

    def handle(self, *args, **options):
        tokens = AuthToken.objects.all()
        if options["email"]:
            tokens = tokens.filter(user__email_address=options["email"])

        count = tokens.count()
        tokens.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Invalidated {count} API token(s).")
        )
