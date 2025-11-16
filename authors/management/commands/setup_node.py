from django.core.management.base import BaseCommand
from django.conf import settings
from authors.models import Author, RemoteNode
import os


class Command(BaseCommand):
    help = 'Setup node configuration for federation'

    def add_arguments(self, parser):
        parser.add_argument('--base-url', type=str, help='Base URL of this node')
        parser.add_argument('--service-username', type=str, help='Service username for node-to-node communication')
        parser.add_argument('--service-password', type=str, help='Service password for node-to-node communication')
        parser.add_argument('--current-username', type=str, help='Current user username to update host/url')

    def handle(self, *args, **options):
        base_url = options.get('base_url') or os.environ.get('BASE_URL')
        service_username = options.get('service_username') or os.environ.get('NODE_SERVICE_USER')
        service_password = options.get('service_password') or os.environ.get('NODE_SERVICE_PASSWORD')
        current_username = options.get('current_username')

        if not all([base_url, service_username, service_password, current_username]):
            self.stdout.write(
                self.style.ERROR(
                    'Missing required parameters. Use --base-url, --service-username, '
                    '--service-password, and --current-username or set environment variables '
                    'BASE_URL, NODE_SERVICE_USER, NODE_SERVICE_PASSWORD'
                )
            )
            return

        # Create/update service user
        service_user, created = Author.objects.get_or_create(username=service_username)
        service_user.set_password(service_password)
        service_user.displayName = f"Node Service User ({service_username})"
        service_user.save()

        # Update current user's host and url
        try:
            current_user = Author.objects.get(username=current_username)
            current_user.host = base_url.rstrip("/")
            current_user.url = f"{base_url.rstrip('/')}/api/authors/{current_user.id}/"
            current_user.save(update_fields=["host", "url"])
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated user {current_username} with host and URL'
                )
            )
        except Author.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'User {current_username} does not exist'
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully configured node: {base_url}\n'
                f'Service user: {service_username}\n'
                f'Current user: {current_username}'
            )
        )