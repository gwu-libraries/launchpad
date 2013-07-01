import pymarc
import os
from PyZ3950 import zoom
from django.conf import settings

os.environ['DJANGO_SETTINGS_MODULE'] = "lp.settings"
conn = zoom.Connection(settings.Z3950_SERVERS['GT']['IP'],settings.Z3950_SERVERS['GT']['PORT'] )

conn.databaseName = settings.Z3950_SERVERS['GT']['DB']
conn.preferredRecordSyntax = settings.Z3950_SERVERS['GT']['SYNTAX']

query = zoom.Query('PQF', '@attr 1=12 %s' % 'b4296166'.encode('utf-8'))

results = conn.search(query)

rows = results[0].data.holdingsData

print "------------------------------------------------------"
print rows[0]

print "------------------------------------------------------"

print rows[1]
