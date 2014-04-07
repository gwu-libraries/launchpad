"""
This is a specialized command for running unit tests against the 
live, read-only Voyager database. The normal test command will attempt
to create a test database, which we cannot do in the Voyager db.
"""

import unittest

from django.core.management.base import BaseCommand

import ui.dbtest

test_dir = '/home/edsu/Projects/launchpad/lp/ui/tests'

class Command(BaseCommand):

    def handle(self,**options):
        s = unittest.defaultTestLoader.loadTestsFromModule(ui.dbtest)
        unittest.TextTestRunner().run(s)



