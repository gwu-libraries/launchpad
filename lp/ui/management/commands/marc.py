import pprint

from django.core.management.base import BaseCommand

from ui import voyager


class Command(BaseCommand):
    args = '<bibid>'
    help = 'get marc record for a given bibid'

    def handle(self, *args, **options):
        if len(args) >= 1:
            record = voyager.get_marc_blob(args[0])
            print record.as_json(indent=2)
