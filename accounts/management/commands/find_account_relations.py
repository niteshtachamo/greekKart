import sys
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import ForeignKey
from accounts.models import Account

class Command(BaseCommand):
    help = 'Find related objects referencing Account instances'

    def add_arguments(self, parser):
        parser.add_argument(
            '--account_id',
            type=int,
            help='ID of the Account instance to check relations for. If omitted, checks all Account instances.'
        )

    def handle(self, *args, **options):
        account_id = options.get('account_id')
        if account_id:
            try:
                account = Account.objects.get(id=account_id)
            except Account.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Account with id {account_id} does not exist.'))
                sys.exit(1)
            accounts = [account]
        else:
            accounts = Account.objects.all()

        related_found = False

        for model in apps.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, ForeignKey) and field.remote_field.model == Account:
                    related_name = field.get_accessor_name()
                    for account in accounts:
                        related_manager = getattr(account, related_name, None)
                        if related_manager:
                            count = related_manager.count() if hasattr(related_manager, 'count') else 1
                            if count > 0:
                                related_found = True
                                self.stdout.write(f'Model {model.__name__} has {count} related objects referencing Account id={account.id} via field "{field.name}".')

        if not related_found:
            self.stdout.write('No related objects referencing the specified Account(s) were found.')
