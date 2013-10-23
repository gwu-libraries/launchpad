import pprint

from django.core.management.base import BaseCommand

from ui import voyager


class Command(BaseCommand):
    args = '<bibid>'
    help = 'get the bibliographic data for a given bibid'

    def handle(self, *args, **options):
        if len(args) >= 1:
            bib = voyager.get_bib_data(args[0])
            pprint.pprint(bib)
