from uw_sws.dao import SWS_DAO
from commonconf import settings
from os.path import abspath, dirname
from lxml import etree
import random
import os
import re


class SWS_GradeRoster_DAO(SWS_DAO):
    def service_mock_paths(self):
        return [abspath(os.path.join(dirname(__file__), 'resources'))]

    def _custom_headers(self, method, url, headers, body):
        pass

    def _update_put(self, url, body, response):
        # For developing against crashes in grade submission
        if re.match('/student/v\d/graderoster/2013,spring,ZERROR,101,S1,',
                    url):
            response.data = "No employee found for ID 1234567890"
            response.status = 500

        # Submitted too late, sad.
        if re.match('/student/v\d/graderoster/2013,spring,ZERROR,101,S2,',
                    url):
            response.data = "grading period not active for year/quarter"
            response.status = 404

        if body is not None:
            response.status = 200
            response.headers = {"X-Data-Source": "SWS file mock data"}
            response.data = self._make_grade_roster_submitted(body)
        else:
            response.status = 400
            response.data = "Bad Request: no PUT body"

    def _make_grade_roster_submitted(self, submitted_body):
        root = etree.fromstring(submitted_body)
        item_elements = root.findall('.//*[@class="graderoster_item"]')
        for item in item_elements:
            date_graded = item.find('.//*[@class="date_graded date"]')
            if date_graded.text is None:
                date_graded.text = '2013-06-01'

            grade_submitter_source = item.find(
                './/*[@class="grade_submitter_source"]')
            if grade_submitter_source.text is None:
                grade_submitter_source.text = 'WEBCGB'

            # Set the status code and message for each item, these elements
            # aren't present in graderosters returned from GET
            # Use settings.GRADEROSTER_PARTIAL_SUBMISSIONS to simulate failures
            status_code_text = '200'
            status_message_text = ''
            if (getattr(settings,
                        'GRADEROSTER_PARTIAL_SUBMISSIONS',
                        False) and random.choice([True, False])):

                status_code_text = '500'
                status_message_text = 'Invalid grade'

            status_code = item.find('.//*[@class="code"]')
            if status_code is None:
                status_code = etree.fromstring('<span class="code"/>')
                item.append(status_code)
            status_code.text = status_code_text

            status_message = item.find('.//*[@class="message"]')
            if status_message is None:
                status_message = etree.fromstring('<span class="message"/>')
                item.append(status_message)
            status_message.text = status_message_text

        return etree.tostring(root)
