# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from uw_sws_graderoster.models import GradingScale


class TestGradingScale(TestCase):
    def test_is_scale(self):
        gs = GradingScale()

        # Copy the scale and reverse it
        rev_ug_scale = gs.GRADE_SCALES[gs.UNDERGRADUATE_SCALE].copy()[::-1]
        self.assertEqual(gs.is_undergraduate_scale(rev_ug_scale), True)
        self.assertEqual(gs.is_any_scale(rev_ug_scale), gs.UNDERGRADUATE_SCALE)

        # Copy the scale and lowercase
        lc_credit_scale = [x.lower() for x in gs.GRADE_SCALES[gs.CREDIT_SCALE]]
        self.assertEqual(gs.is_credit_scale(lc_credit_scale), True)
        self.assertEqual(gs.is_any_scale(lc_credit_scale), gs.CREDIT_SCALE)

        self.assertEqual(gs.is_undergraduate_scale([]), False)
        self.assertEqual(gs.is_graduate_scale([4.0]), False)
        self.assertEqual(gs.is_passfail_scale(['P']), False)
        self.assertEqual(gs.is_credit_scale(['', '']), False)
        self.assertEqual(gs.is_highpassfail_scale([]), False)

        self.assertEqual(gs.is_any_scale([]), None)
        self.assertEqual(gs.is_any_scale(['P']), None)

    def test_sorted_scale(self):
        gs = GradingScale()

        # Ensure the sorted scales equal themselves
        ug_scale = gs.GRADE_SCALES[gs.UNDERGRADUATE_SCALE]
        self.assertEqual(gs.sorted_scale(ug_scale), ug_scale)

        gr_scale = gs.GRADE_SCALES[gs.GRADUATE_SCALE]
        self.assertEqual(gs.sorted_scale(gr_scale), gr_scale)

        cnc_scale = gs.GRADE_SCALES[gs.CREDIT_SCALE]
        self.assertEqual(gs.sorted_scale(cnc_scale), cnc_scale)

        pf_scale = gs.GRADE_SCALES[gs.PASSFAIL_SCALE]
        self.assertEqual(gs.sorted_scale(pf_scale), pf_scale)

        hpf_scale = gs.GRADE_SCALES[gs.HIGHPASSFAIL_SCALE]
        self.assertEqual(gs.sorted_scale(hpf_scale), hpf_scale)

        # Test mixed sorting for arbitrary grade option lists
        grading_options = ['4.0', '2.5', '0.0', 'i', 'NC', 'Cr', '']
        self.assertEqual(gs.sorted_scale(grading_options),
                         ['', 'I', 'CR', 'NC', '4.0', '2.5', '0.0'])
