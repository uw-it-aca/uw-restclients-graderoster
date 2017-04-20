from unittest import TestCase
from uw_sws_graderoster.dao import SWS_GradeRoster_DAO


class SWSGradeRosterTestDao(TestCase):
    def test_custom_headers(self):
        self.assertEquals(
            SWS_GradeRoster_DAO()._custom_headers('GET', '/', {}, None), None)
