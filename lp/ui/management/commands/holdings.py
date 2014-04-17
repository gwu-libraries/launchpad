import json

from ui import db
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<bibid>'
    help = 'gett the holdings data for a given bibid'

    def handle(self, *args, **options):
        if len(args) >= 1:
            bibid = args[0]
            print json.dumps(db.get_availability(bibid), indent=2)
