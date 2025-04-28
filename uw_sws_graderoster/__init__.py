# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from uw_sws import encode_section_label
from uw_sws_graderoster.dao import SWS_GradeRoster_DAO
from uw_sws_graderoster.models import GradeRoster
from restclients_core.exceptions import DataFailureException
from lxml import etree

graderoster_url = "/student/v5/graderoster"


def get_graderoster(section, instructor, requestor):
    """
    Returns a restclients.GradeRoster for the passed Section model and
    instructor Person.
    """
    label = GradeRoster(section=section,
                        instructor=instructor).graderoster_label()
    url = "{}/{}".format(graderoster_url, encode_section_label(label))
    headers = {"Accept": "text/xhtml",
               "Connection": "keep-alive",
               "X-UW-Act-as": requestor.uwnetid}

    response = SWS_GradeRoster_DAO().getURL(url, headers)

    if response.status != 200:
        root = etree.fromstring(response.data)
        msg = root.find(".//*[@class='status_description']").text.strip()
        raise DataFailureException(url, response.status, msg)

    try:
        root = etree.fromstring(response.data.strip())
    except etree.XMLSyntaxError as ex:
        raise DataFailureException(url, response.status, ex)

    return GradeRoster.from_xhtml(root, section=section, instructor=instructor)


def update_graderoster(graderoster, requestor):
    """
    Updates the graderoster resource for the passed restclients.GradeRoster
    model. A new restclients.GradeRoster is returned, representing the
    document returned from the update request.
    """
    label = graderoster.graderoster_label()
    url = "{}/{}".format(graderoster_url, encode_section_label(label))
    headers = {"Content-Type": "application/xhtml+xml",
               "Connection": "keep-alive",
               "X-UW-Act-as": requestor.uwnetid}
    body = graderoster.xhtml()

    response = SWS_GradeRoster_DAO().putURL(url, headers, body)

    if response.status != 200:
        root = etree.fromstring(response.data)
        msg = root.find(".//*[@class='status_description']").text.strip()
        raise DataFailureException(url, response.status, msg)

    try:
        root = etree.fromstring(response.data.strip())
    except etree.XMLSyntaxError as ex:
        raise DataFailureException(url, response.status, ex)

    return GradeRoster.from_xhtml(root, section=graderoster.section,
                                  instructor=graderoster.instructor)
