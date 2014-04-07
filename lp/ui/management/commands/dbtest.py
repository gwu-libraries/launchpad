import unittest

from django.core.management.base import BaseCommand

import ui.dbtest

test_dir = '/home/edsu/Projects/launchpad/lp/ui/tests'

class Command(BaseCommand):

    def handle(self,**options):
        s = unittest.defaultTestLoader.loadTestsFromModule(ui.dbtest)
        unittest.TextTestRunner().run(s)



