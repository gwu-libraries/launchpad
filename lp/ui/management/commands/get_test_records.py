"""
This command takes a full pass through the database looking for MARC records
that match the fields we extract. If records are found they are saved to
the testdata directory.
"""

import os
import sys

from django.db import connection
from django.core.management.base import BaseCommand

from ui import marc
from ui.voyager import get_marc_blob


test_data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'testdata')
field_specs_found = set()


class Command(BaseCommand):
    help = 'extract marc records from voyager for testing'

    def handle(self, *args, **kwargs):
        for bib_id, record in records():
            # provid an indicator of records being looked at
            sys.stdout.write('.')
            sys.stdout.flush()

            for name, field_specs in marc.mapping.items():
                for fs in field_specs:
                    # TODO: handle tuple too
                    if type(fs) != str:
                        continue

                    if not fs in field_specs_found:
                        found = check_record(bib_id, record, name, fs)
                        if found:
                            field_specs_found.add(fs)

        # report any field specs that we couldn't find a record fo
        for fs in field_specs:
            if fs not in field_specs_found:
                print "unable to find field spec" % fs


def check_record(bib_id, record, name, field_spec):
    fields = record.get_fields(field_spec)
    found = False
    if len(fields) > 0:
        f = os.path.join(test_data_dir, "%s_%s.mrc" % (name, field_spec))
        try:
            marc = record.as_marc()
            open(f, "wb").write(marc)
            sys.stdout.write("\nfound: %s %s\n" % (name, field_spec))
            found = True
        except Exception as e:
            print "unable to serialize %s; %s" % (bib_id, e)
    return found


def records():
    cursor = connection.cursor()
    query = "SELECT BIB_ID FROM bib_master WHERE SUPPRESS_IN_OPAC = 'N'"
    cursor.execute(query)
    while True:
        row = cursor.fetchone()
        if not row:
            break
        bib_id = row[0]
        record = get_marc_blob(bib_id)
        yield bib_id, record
