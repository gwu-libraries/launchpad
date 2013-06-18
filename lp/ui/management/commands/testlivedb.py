from django.core.management.base import NoArgsCommand
import unittest

from ui.tests import LiveWrlcTestCase


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        suite = unittest.TestLoader().loadTestsFromTestCase(LiveWrlcTestCase)
        unittest.TextTestRunner().run(suite)
