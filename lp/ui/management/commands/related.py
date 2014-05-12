from ui import db
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    args = '<bibid>'
    help = 'get related bibids for a given bibid'

    def handle(self, *args, **options):
        if len(args) >= 1:
            item = db.get_item(args[0])
            bibids = db.get_related_bibids(item)
            print bibids
