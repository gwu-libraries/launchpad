from optparse import make_option
from pymarc.marcxml import record_to_xml
from django.core.management.base import BaseCommand

from ui import voyager


class Command(BaseCommand):
    args = '<bibid>'
    help = 'get the marc record for a given bibid'

    format = make_option('--format', 
                         action='store',
                         dest='format',
                         default='marc',
                         help='format for record: json, marc, xml')

    option_list = BaseCommand.option_list + (format,)

    def handle(self, bibid, **options):
        record = voyager.get_marc_blob(bibid)
        if options['format'] == 'json':
            print record.as_json(indent=2)
        elif options['format'] == 'xml':
            print record_to_xml(record)
        else:
            print record.as_marc21()
