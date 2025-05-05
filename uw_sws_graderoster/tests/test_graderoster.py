# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from unittest import TestCase
from uw_pws.util import fdao_pws_override
from uw_sws.util import fdao_sws_override
from uw_sws.section import get_section_by_label
from uw_sws.models import Section
from uw_sws_graderoster import get_graderoster, update_graderoster
from restclients_core.exceptions import DataFailureException
import random
import re


@fdao_pws_override
@fdao_sws_override
class SWSTestGradeRoster(TestCase):

    def test_get_graderoster(self):
        section = get_section_by_label('2013,summer,CSS,161/A')
        instructor = section.meetings[0].instructors[0]
        requestor = instructor

        graderoster = get_graderoster(section, instructor, requestor)

        self.assertEqual(
            graderoster.graderoster_label(),
            "2013,summer,CSS,161,A,{}".format(instructor.uwregid),
            "Correct graderoster_label()")
        self.assertEqual(
            len(graderoster.grade_submission_delegates), 2,
            "Grade submission delegates")
        self.assertEqual(len(graderoster.items), 5, "GradeRoster items")

        grades = ['0.7', None, '3.1', '1.5', '4.0']
        labels = ['1914B1B26A7D11D5A4AE0004AC494FFE',
                  '511FC8241DC611DB9943F9D03AACCE31',
                  'F00E253C634211DA9755000629C31437',
                  'C7EED7406A7C11D5A4AE0004AC494FFE',
                  'A9D2DDFA6A7D11D5A4AE0004AC494FFE,A']
        surnames = ['AVERAGE', 'AVERAGE', 'AVERAGE', 'AVERAGE', 'TEACHER']
        first_names = [
            'CHARLIE', 'JASON A', 'STEPHEN J', 'MICHAEL S.', 'PHIL AVERAGE']
        for idx, item in enumerate(graderoster.items):
            self.assertEqual(
                len(item.grade_choices), 36,
                "grade_choices returns correct grades")
            self.assertEqual(
                item.grade, grades[idx], "Correct default grade")
            self.assertEqual(
                item.student_label(), labels[idx], "Correct student label")
            self.assertEqual(item.grade_document_id, "08261300000")
            self.assertEqual(
                item.student_first_name, first_names[idx], "First name")
            self.assertEqual(item.student_surname, surnames[idx], "Surname")

    def test_put_graderoster(self):
        section = get_section_by_label('2013,summer,CSS,161/A')
        instructor = section.meetings[0].instructors[0]
        requestor = instructor

        graderoster = get_graderoster(section, instructor, requestor)

        for item in graderoster.items:
            new_grade = str(round(random.uniform(1, 4), 1))
            item.grade = new_grade

        orig_xhtml = split_xhtml(graderoster.xhtml())

        new_graderoster = update_graderoster(graderoster, requestor)
        new_xhtml = split_xhtml(new_graderoster.xhtml())
        self.assertEqual(orig_xhtml, new_xhtml, "XHTML is equal")

    def test_graderoster_with_entities(self):
        section = get_section_by_label('2013,autumn,EDC&I,461/A')
        instructor = section.meetings[0].instructors[0]
        requestor = instructor

        graderoster = get_graderoster(section, instructor, requestor)

        orig_xhtml = split_xhtml(graderoster.xhtml())
        new_graderoster = update_graderoster(graderoster, requestor)
        new_xhtml = split_xhtml(new_graderoster.xhtml())
        self.assertEqual(orig_xhtml, new_xhtml, "XHTML is equal")


def split_xhtml(xhtml):
    return re.split(r'\s*\n\s*', xhtml.strip())
