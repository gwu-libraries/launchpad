import gzip
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections


def _newfile(counter):
    """Generate a new sitemap filename based on count."""
    name = '%s/sitemap-%s.xml.gz' % (settings.SITEMAPS_DIR,
        counter)
    fp = gzip.open(name, 'wb')
    fp.write("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n""")
    return fp


def _newurl(counter):
    """Generate the <loc> URL for a sitemap file based on count."""
    return "%s/sitemap-%s.xml.gz" % (settings.SITEMAPS_BASE_URL, counter)


class Command(BaseCommand):
    help = 'Generate sitemap files'

    def handle(self, *args, **options):
        # first, clear out the existing files
        print 'Removing old files'
        for old_file in os.listdir(settings.SITEMAPS_DIR):
            os.remove('%s/%s' % (settings.SITEMAPS_DIR, old_file))
        print 'Generating maps'
        cursor = connections['voyager'].cursor()
        query = """SELECT BIB_ID FROM bib_master
            WHERE SUPPRESS_IN_OPAC = 'N'
            """
        cursor.execute(query)
        index_file = '%s/sitemap-index.xml' % settings.SITEMAPS_DIR
        fp_index = open(index_file, 'wb')
        fp_index.write("""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n""")
        i = j = 0
        fp = _newfile(j)
        line = "<sitemap><loc>%s</loc></sitemap>\n" % _newurl(j)
        fp_index.write(line)
        row = cursor.fetchone()
        while row:
            line = '<url><loc>%s/item/%s</loc></url>\n' % \
                (settings.SITEMAPS_BASE_URL, row[0])
            fp.write(line)
            if i == 49990:
                i = 0
                j += 1
                fp.write('</urlset>')
                fp.close()
                fp = _newfile(j)
                line = "<sitemap><loc>%s</loc></sitemap>\n" % _newurl(j)
                fp_index.write(line)
                print '%s - %s' % (j, row[0])
            else:
                i += 1
            row = cursor.fetchone()
        if fp:
            fp.write('</urlset>\n')
            fp.close()
        fp_index.write("""</sitemapindex>\n""")
        fp_index.close()
