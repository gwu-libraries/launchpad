from django.conf import settings
from django.test import TestCase

from ui.voyager import get_marc856


class BoundWithItem(TestCase):

    def test_marc_856_link(self):
        link = "856:42:$uhttp://findit.library.gwu.edu/item/12713487$zClick\
                here for circulation status [bound with The journal\
                of proceedings of the National Teachers' Association\
                ... and 2 other titles]"
        marc_856 = get_marc856(link)
        self.assertTrue(marc_856[0]['bound_item'])
        link = "856:40:$uhttp://proxygw.wrlc.org/login?url=\
                http://gateway.proquest.com/openurl?ctx_ver=Z39.88-2003\
                &res_id=xri:eebo&rft_val_fmt=&rft_id=xri:eebo:image:47581\
                $zClick here to access."
        marc_856 = get_marc856(link)
        self.assertFalse(marc_856[0]['bound_item'])
