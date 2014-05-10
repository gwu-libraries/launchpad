import json

from ui import db
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<bibid>'
    help = 'get the bibliographic data for a given bibid'

    def handle(self, *args, **options):
        if len(args) >= 1:
            item = db.get_item(args[0])
            print json.dumps(item, indent=2)
