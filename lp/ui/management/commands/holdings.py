from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from ui import voyager as v
import sys

class Command(BaseCommand):
    args = '<bibid>'
    help = 'gett the holdings data for a given bibid'

    def handle(self, *args, **options):
        if len(args) >= 1:
            bib = v.get_bib_data(args[0])
            h = v.get_holdings(bib )
            

