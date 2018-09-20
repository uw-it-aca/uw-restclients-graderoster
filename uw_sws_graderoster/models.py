from restclients_core import models
from uw_sws.models import Section, Person
from jinja2 import Environment, FileSystemLoader
import os


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
    grade_submitter_person = models.ForeignKey(Person,
                                               related_name="grade_submitter",
                                               null=True)
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
