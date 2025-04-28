# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from uw_sws_graderoster.dao import SWS_GradeRoster_DAO


class SWSGradeRosterTestDao(TestCase):
    def test_custom_headers(self):
        self.assertEqual(
            SWS_GradeRoster_DAO()._custom_headers('GET', '/', {}, None), None)
