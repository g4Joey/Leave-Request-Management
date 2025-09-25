from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Set or replace a user's password. If the provided password looks like a Django hash, it will be applied directly."\
           " Otherwise it will be hashed."

    def add_arguments(self, parser):
        parser.add_argument('username', help='Username of the account to modify')
        parser.add_argument('password', help='New password (plain or already-hashed)')
        parser.add_argument('--force-plain', action='store_true', help='Force treating the password as plain text even if it resembles a hash')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        force_plain = options['force_plain']

        user = User.objects.filter(username=username).first()
        if not user:
            raise CommandError(f"User '{username}' not found")

        looks_hashed = (password.count('$') >= 3 or password.startswith('pbkdf2_'))
        if looks_hashed and not force_plain:
            # Assign directly
            user.password = password  # type: ignore[assignment]
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f"Applied hashed password to '{username}'."))
        else:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f"Set new password for '{username}'."))
