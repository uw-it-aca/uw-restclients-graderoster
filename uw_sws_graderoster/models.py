# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from restclients_core import models
from uw_pws import PWS
from uw_sws.models import Section, Person, GradeSubmissionDelegate
from jinja2 import Environment, FileSystemLoader
import os

nsmap = {"xhtml": "http://www.w3.org/1999/xhtml"}


class GradeRosterItem(models.Model):
    student_uwregid = models.CharField(max_length=32)
    student_first_name = models.CharField(max_length=100)
    student_surname = models.CharField(max_length=100)
    student_former_name = models.CharField(max_length=120, null=True)
    student_number = models.PositiveIntegerField()
    student_type = models.CharField(max_length=20, null=True)
    student_credits = models.FloatField()
    duplicate_code = models.CharField(max_length=8, null=True)
    section_id = models.CharField(max_length=2)
    is_auditor = models.BooleanField(default=False)
    allows_incomplete = models.BooleanField(default=False)
    has_incomplete = models.BooleanField(default=False)
    has_writing_credit = models.BooleanField(default=False)
    no_grade_now = models.BooleanField(default=False)
    date_withdrawn = models.DateField(null=True)
    grade = models.CharField(max_length=20, null=True, default=None)
    allows_grade_change = models.BooleanField(default=False)
    date_graded = models.DateField(null=True)
    grade_document_id = models.CharField(max_length=100, null=True)
    grade_submitter_person = models.ForeignKey(
        Person, related_name="grade_submitter", null=True)
    grade_submitter_source = models.CharField(max_length=8, null=True)
    status_code = models.CharField(max_length=3, null=True)
    status_message = models.CharField(max_length=500, null=True)

    def student_label(self, separator=","):
        label = self.student_uwregid
        if self.duplicate_code is not None and len(self.duplicate_code):
            label += "{}{}".format(separator, self.duplicate_code)
        return label

    def __eq__(self, other):
        return (self.student_uwregid == other.student_uwregid and
                self.duplicate_code == other.duplicate_code)

    def __init__(self, *args, **kwargs):
        super(GradeRosterItem, self).__init__(*args, **kwargs)
        self.grade_choices = []

    @staticmethod
    def from_xhtml(tree, *args, **kwargs):
        gr_item = GradeRosterItem(*args, **kwargs)
        for el in tree.xpath(".//xhtml:a[@rel='student']/*[@class='reg_id']",
                             namespaces=nsmap):
            gr_item.student_uwregid = el.text.strip()

        for el in tree.xpath(".//xhtml:a[@rel='student']/*[@class='name']",
                             namespaces=nsmap):
            try:
                (surname, first_name) = el.text.split(",", 1)
                gr_item.student_first_name = first_name.strip()
                gr_item.student_surname = surname.strip()
            except ValueError:
                pass

        for el in tree.xpath(".//*[@class]"):
            classname = el.get("class")
            if classname == "duplicate_code" and el.text is not None:
                duplicate_code = el.text.strip()
                if len(duplicate_code):
                    gr_item.duplicate_code = duplicate_code
            elif classname == "section_id" and el.text is not None:
                gr_item.section_id = el.text.strip()
            elif classname == "student_former_name" and el.text is not None:
                student_former_name = el.text.strip()
                if len(student_former_name):
                    gr_item.student_former_name = student_former_name
            elif classname == "student_number":
                gr_item.student_number = el.text.strip()
            elif classname == "student_credits" and el.text is not None:
                gr_item.student_credits = el.text.strip()
            elif "date_withdrawn" in classname and el.text is not None:
                gr_item.date_withdrawn = el.text.strip()
            elif classname == "incomplete":
                if el.get("checked", "") == "checked":
                    gr_item.has_incomplete = True
                if el.get("disabled", "") != "disabled":
                    gr_item.allows_incomplete = True
            elif classname == "writing_course":
                if el.get("checked", "") == "checked":
                    gr_item.has_writing_credit = True
            elif classname == "auditor":
                if el.get("checked", "") == "checked":
                    gr_item.is_auditor = True
            elif classname == "no_grade_now":
                if el.get("checked", "") == "checked":
                    gr_item.no_grade_now = True
            elif classname == "grades":
                if el.get("disabled", "") != "disabled":
                    gr_item.allows_grade_change = True
            elif classname == "grade":
                grade = el.text.strip() if el.text is not None else ""
                gr_item.grade_choices.append(grade)
                if el.get("selected", "") == "selected":
                    gr_item.grade = grade
            elif classname == "grade_document_id" and el.text is not None:
                gr_item.grade_document_id = el.text.strip()
            elif "date_graded" in classname and el.text is not None:
                gr_item.date_graded = el.text.strip()
            elif classname == "grade_submitter_source" and el.text is not None:
                gr_item.grade_submitter_source = el.text.strip()
            elif classname == "code" and el.text is not None:
                gr_item.status_code = el.text.strip()
            elif classname == "message" and el.text is not None:
                gr_item.status_message = el.text.strip()
        return gr_item


class GradeRoster(models.Model):
    section = models.ForeignKey(Section,
                                on_delete=models.PROTECT)
    instructor = models.ForeignKey(Person,
                                   on_delete=models.PROTECT)
    section_credits = models.FloatField()
    allows_writing_credit = models.NullBooleanField()

    def graderoster_label(self):
        return "{year},{qtr},{abbr},{no},{sect},{inst}".format(
            year=self.section.term.year,
            qtr=self.section.term.quarter,
            abbr=self.section.curriculum_abbr,
            no=self.section.course_number,
            sect=self.section.section_id,
            inst=self.instructor.uwregid)

    def xhtml(self):
        template_path = os.path.join(os.path.dirname(__file__), "templates/")
        return Environment(
            loader=FileSystemLoader(template_path), autoescape=True
        ).get_template("graderoster.xhtml").render({"graderoster": self})

    def __init__(self, *args, **kwargs):
        super(GradeRoster, self).__init__(*args, **kwargs)
        self.authorized_grade_submitters = []
        self.grade_submission_delegates = []
        self.items = []

    @staticmethod
    def from_xhtml(tree, *args, **kwargs):
        pws = PWS()
        gr = GradeRoster(*args, **kwargs)

        people = {gr.instructor.uwregid: gr.instructor}

        root = tree.xpath(
            ".//xhtml:div[@class='graderoster']", namespaces=nsmap)[0]

        default_section_id = None
        xpath = "./xhtml:div/xhtml:a[@rel='section']/*[@class='section_id']"
        el = root.xpath(xpath, namespaces=nsmap)[0]
        default_section_id = el.text.upper()

        el = root.xpath(
            "./xhtml:div/*[@class='section_credits']", namespaces=nsmap)[0]
        if el.text is not None:
            gr.section_credits = el.text.strip()

        el = root.xpath(
            "./xhtml:div/*[@class='writing_credit_display']",
            namespaces=nsmap)[0]
        if el.get("checked", "") == "checked":
            gr.allows_writing_credit = True

        for el in root.xpath(
                "./xhtml:div//*[@rel='authorized_grade_submitter']",
                namespaces=nsmap):
            reg_id = el.xpath(".//*[@class='reg_id']")[0].text.strip()
            if reg_id not in people:
                people[reg_id] = pws.get_person_by_regid(reg_id)
            gr.authorized_grade_submitters.append(people[reg_id])

        for el in root.xpath(
                "./xhtml:div//*[@class='grade_submission_delegate']",
                namespaces=nsmap):
            reg_id = el.xpath(".//*[@class='reg_id']")[0].text.strip()
            node = el.xpath(".//*[@class='delegate_level']")[0]
            delegate_level = node.text.strip()
            if reg_id not in people:
                people[reg_id] = pws.get_person_by_regid(reg_id)
            delegate = GradeSubmissionDelegate(person=people[reg_id],
                                               delegate_level=delegate_level)
            gr.grade_submission_delegates.append(delegate)

        xpath = "./*[@class='graderoster_items']/*[@class='graderoster_item']"
        for item in root.xpath(xpath):
            grade_submitter_person = None
            xpath = (".//xhtml:a[@rel='grade_submitter_person']/"
                     "*[@class='reg_id']")
            for el in item.xpath(xpath, namespaces=nsmap):
                reg_id = el.text.strip()
                if reg_id not in people:
                    people[reg_id] = pws.get_person_by_regid(reg_id)
                grade_submitter_person = people[reg_id]

            gr_item = GradeRosterItem.from_xhtml(
                item, section_id=default_section_id,
                grade_submitter_person=grade_submitter_person)
            gr.items.append(gr_item)
        return gr


class GradingScale(models.Model):
    UNDERGRADUATE_SCALE = "ug"
    GRADUATE_SCALE = "gr"
    PASSFAIL_SCALE = "pf"
    CREDIT_SCALE = "cnc"
    HIGHPASSFAIL_SCALE = "hpf"

    SCALE_CHOICES = (
        (UNDERGRADUATE_SCALE, "Undergraduate Scale (4.0-0.7)"),
        (GRADUATE_SCALE, "Graduate Scale (4.0-1.7)"),
        (PASSFAIL_SCALE, "School of Medicine Pass/No Pass Scale"),
        (CREDIT_SCALE, "Credit/No Credit Scale"),
        (HIGHPASSFAIL_SCALE, "Honors/High Pass/Pass/Fail Scale")
    )

    GRADE_SCALES = {
        UNDERGRADUATE_SCALE: [
            "4.0", "3.9", "3.8", "3.7", "3.6", "3.5", "3.4", "3.3", "3.2",
            "3.1", "3.0", "2.9", "2.8", "2.7", "2.6", "2.5", "2.4", "2.3",
            "2.2", "2.1", "2.0", "1.9", "1.8", "1.7", "1.6", "1.5", "1.4",
            "1.3", "1.2", "1.1", "1.0", "0.9", "0.8", "0.7"],
        GRADUATE_SCALE: [
            "4.0", "3.9", "3.8", "3.7", "3.6", "3.5", "3.4", "3.3", "3.2",
            "3.1", "3.0", "2.9", "2.8", "2.7", "2.6", "2.5", "2.4", "2.3",
            "2.2", "2.1", "2.0", "1.9", "1.8", "1.7"],
        PASSFAIL_SCALE: ["P", "F"],
        CREDIT_SCALE: ["CR", "NC"],
        HIGHPASSFAIL_SCALE: ["H", "HP", "P", "F"],
    }

    # Controls sort order for all valid grades, including mixed sorting
    # with 4.0 scale grades
    GRADE_ORDER = {
        "": "9.9", "I": "9.8", "W": "9.7", "HW": "9.5", "H": "7.3",
        "HP": "7.2", "P": "7.1", "F": "7.0", "CR": "6.1", "NC": "6.0", "N": "5"
    }

    def sorted_scale(self, grade_scale):
        return sorted([str(x).upper() for x in grade_scale],
                      key=lambda x: self.GRADE_ORDER.get(x, x),
                      reverse=True)

    def is_undergraduate_scale(self, grade_scale):
        return self._is_scale(grade_scale, self.UNDERGRADUATE_SCALE)

    def is_graduate_scale(self, grade_scale):
        return self._is_scale(grade_scale, self.GRADUATE_SCALE)

    def is_passfail_scale(self, grade_scale):
        return self._is_scale(grade_scale, self.PASSFAIL_SCALE)

    def is_credit_scale(self, grade_scale):
        return self._is_scale(grade_scale, self.CREDIT_SCALE)

    def is_highpassfail_scale(self, grade_scale):
        return self._is_scale(grade_scale, self.HIGHPASSFAIL_SCALE)

    def is_any_scale(self, grade_scale):
        for scale in self.GRADE_SCALES.keys():
            if self._is_scale(grade_scale, scale):
                return scale

    def _is_scale(self, grade_scale, scale):
        return self.sorted_scale(grade_scale) == self.GRADE_SCALES[scale]
