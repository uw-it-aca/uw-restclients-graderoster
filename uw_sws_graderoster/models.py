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
        self.section_id = kwargs.get('section_id')
        self.grade_submitter_person = kwargs.get('grade_submitter_person')
        self.grade_choices = []

        tree = kwargs.get('data')
        if tree is None:
            return super(GradeRosterItem, self).__init__(*args, **kwargs)

        for el in tree.xpath(".//xhtml:a[@rel='student']/*[@class='reg_id']",
                             namespaces=nsmap):
            self.student_uwregid = el.text.strip()

        for el in tree.xpath(".//xhtml:a[@rel='student']/*[@class='name']",
                             namespaces=nsmap):
            full_name = el.text.strip()
            try:
                (surname, first_name) = full_name.split(",", 1)
                self.student_first_name = first_name
                self.student_surname = surname
            except ValueError:
                pass

        for el in tree.xpath(".//*[@class]"):
            classname = el.get("class")
            if classname == "duplicate_code" and el.text is not None:
                duplicate_code = el.text.strip()
                if len(duplicate_code):
                    self.duplicate_code = duplicate_code
            elif classname == "section_id" and el.text is not None:
                self.section_id = el.text.strip()
            elif classname == "student_former_name" and el.text is not None:
                student_former_name = el.text.strip()
                if len(student_former_name):
                    self.student_former_name = student_former_name
            elif classname == "student_number":
                self.student_number = el.text.strip()
            elif classname == "student_credits" and el.text is not None:
                self.student_credits = el.text.strip()
            elif "date_withdrawn" in classname and el.text is not None:
                self.date_withdrawn = el.text.strip()
            elif classname == "incomplete":
                if el.get("checked", "") == "checked":
                    self.has_incomplete = True
                if el.get("disabled", "") != "disabled":
                    self.allows_incomplete = True
            elif classname == "writing_course":
                if el.get("checked", "") == "checked":
                    self.has_writing_credit = True
            elif classname == "auditor":
                if el.get("checked", "") == "checked":
                    self.is_auditor = True
            elif classname == "no_grade_now":
                if el.get("checked", "") == "checked":
                    self.no_grade_now = True
            elif classname == "grades":
                if el.get("disabled", "") != "disabled":
                    self.allows_grade_change = True
            elif classname == "grade":
                grade = el.text.strip() if el.text is not None else ""
                self.grade_choices.append(grade)
                if el.get("selected", "") == "selected":
                    self.grade = grade
            elif classname == "grade_document_id" and el.text is not None:
                self.grade_document_id = el.text.strip()
            elif "date_graded" in classname and el.text is not None:
                self.date_graded = el.text.strip()
            elif classname == "grade_submitter_source" and el.text is not None:
                self.grade_submitter_source = el.text.strip()
            elif classname == "code" and el.text is not None:
                self.status_code = el.text.strip()
            elif classname == "message" and el.text is not None:
                self.status_message = el.text.strip()


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
            loader=FileSystemLoader(template_path)
        ).get_template("graderoster.xhtml").render({"graderoster": self})

    def __init__(self, *args, **kwargs):
        self.section = kwargs.get('section')
        self.instructor = kwargs.get('instructor')
        self.authorized_grade_submitters = []
        self.grade_submission_delegates = []
        self.items = []

        tree = kwargs.get('data')
        if tree is None:
            return super(GradeRoster, self).__init__(*args, **kwargs)

        pws = PWS()
        people = {self.instructor.uwregid: self.instructor}

        root = tree.xpath(
            ".//xhtml:div[@class='graderoster']", namespaces=nsmap)[0]

        default_section_id = None
        xpath = "./xhtml:div/xhtml:a[@rel='section']/*[@class='section_id']"
        el = root.xpath(xpath, namespaces=nsmap)[0]
        default_section_id = el.text.upper()

        el = root.xpath(
            "./xhtml:div/*[@class='section_credits']", namespaces=nsmap)[0]
        if el.text is not None:
            self.section_credits = el.text.strip()

        el = root.xpath(
            "./xhtml:div/*[@class='writing_credit_display']",
            namespaces=nsmap)[0]
        if el.get("checked", "") == "checked":
            self.allows_writing_credit = True

        for el in root.xpath(
                "./xhtml:div//*[@rel='authorized_grade_submitter']",
                namespaces=nsmap):
            reg_id = el.xpath(".//*[@class='reg_id']")[0].text.strip()
            if reg_id not in people:
                people[reg_id] = pws.get_person_by_regid(reg_id)
            self.authorized_grade_submitters.append(people[reg_id])

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
            self.grade_submission_delegates.append(delegate)

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

            gr_item = GradeRosterItem(
                data=item, section_id=default_section_id,
                grade_submitter_person=grade_submitter_person)

            self.items.append(gr_item)
