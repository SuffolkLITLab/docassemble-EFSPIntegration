import json
import unittest
from unittest.mock import MagicMock
from pathlib import Path
from docassemble.base.core import DAObject
from docassemble.AssemblyLine.al_general import ALIndividual
from ..efm_client import ProxyConnection, ApiResponse
from ..conversions import parse_case_info, parse_service_contacts


class TestConversions(unittest.TestCase):
    # Tests conversions.py on the "vars.json" file

    def setUp(self):
        with open(Path(__file__).parent / "vars.json", "r") as file:
            full_json = json.load(file).get("variables")
            self.my_var = full_json.get("my_var").get("data")
        self.my_service_contacts = full_json.get("my_service_contacts")
        self.proxy_conn = ProxyConnection()
        self.proxy_conn.get_case = MagicMock(
            "get_case", return_value=ApiResponse(200, "", self.my_var)
        )

    def test_parse_case_info(self):
        # Makes sure that participants of the case are parsed fully, needed
        case = DAObject("case")
        parse_case_info(self.proxy_conn, case, self.my_var, "adams")
        self.assertEqual(len(case.participants), 2)
        for partip in case.participants:
            self.assertIsInstance(partip, ALIndividual)
            self.assertIn(partip.person_type, ["ALIndividual", "business"])
            self.assertNotEqual(partip.name.first, None)
            self.assertNotEqual(partip.tyler_id, None)
            if partip.person_type == "ALIndividual":
                self.assertNotEqual(partip.name.last, None)
                # Make sure the name is title case: first letter is upper, everything else lower
                self.assertEqual(partip.name.first[0], partip.name.first[0].upper())
                self.assertEqual(partip.name.first[1], partip.name.first[1].lower())
                self.assertTrue(hasattr(partip, "address"))
                self.assertEqual(partip.address.city, "RADOM")
                self.assertEqual(partip.address.zip, "62876")
                self.assertFalse(hasattr(partip, "phone_number"))
                self.assertFalse(hasattr(partip, "email"))
            self.assertTrue(hasattr(partip, "party_type"))
            self.assertTrue(hasattr(partip, "party_type_name"))
            self.assertTrue(hasattr(partip, "tyler_id"))
        self.assertEqual(case.participants[0].instanceName, "case.participants[0]")
        self.assertEqual(case.docket_number, "2020SC12")
        self.assertEqual(case.category, "6198")

    def test_parse_service_contact(self):
        no_contacts = parse_service_contacts([])
        self.assertEqual(len(no_contacts), 0)

        service_contacts = parse_service_contacts(self.my_service_contacts)
        self.assertEqual(len(service_contacts), 1)
        self.assertEqual(service_contacts[0][0], "6707a4f8-9f4c-4bbb-8498-ed4890208c6d")
        self.assertEqual(service_contacts[0][1], "Bryce Willey")


class TestNoneResp(unittest.TestCase):
    # Tests with none responses conversions.py on the "vars.json" file

    def setUp(self):
        with open(Path(__file__).parent / "vars.json", "r") as file:
            full_json = json.load(file).get("variables")
            self.my_var = full_json.get("my_var").get("data")
        self.my_service_contacts = full_json.get("my_service_contacts")
        self.proxy_conn = ProxyConnection()
        self.proxy_conn.get_case = MagicMock(
            "get_case", return_value=ApiResponse(200, "", None)
        )

    def test_none(self):
        # Makes sure that participants of the case are parsed fully, needed
        case = DAObject("case")
        parse_case_info(self.proxy_conn, case, None, "peoria")
        # no throw!


class TestCourtSwitching(unittest.TestCase):
    # Tests that if we search a case in a grouped court (say peoria) and
    # get back a court from a sub court (peariacr), that the
    # court_id from the found case reflects the sub court.
    #
    # This is necessary, as filings can't be accepted to the grouped court."""

    def setUp(self):
        with open(Path(__file__).parent / "peoria_to_cr.json", "r") as file:
            self.my_var = json.load(file)
        self.proxy_conn = ProxyConnection()
        self.proxy_conn.get_case = MagicMock(
            "get_case", return_value=ApiResponse(200, "", self.my_var)
        )

    def test_switched_court(self):
        # Makes sure that participants of the case are parsed fully, needed
        case = DAObject("case")
        parse_case_info(self.proxy_conn, case, self.my_var, "peoria")
        self.assertEqual(case.court_id, "peoriacr")
        self.assertEqual(case.docket_number, "02-CM-02778-1")
        self.assertEqual(case.category, "135493")


class TestConversionIgnoreAttorneys(unittest.TestCase):
    def setUp(self):
        with open(Path(__file__).parent / "temp2.json", "r") as file:
            full_json = json.load(file).get("selected_existing_case")
            self.first_resp = full_json.get("details")
            self.more_details = full_json.get("case_details")
        self.proxy_conn = ProxyConnection()
        self.proxy_conn.get_case = MagicMock(
            "get_case", return_value=ApiResponse(200, "", self.more_details)
        )

    def test_ignore_attorneys(self):
        # Attorneys are just stuck in the middle with normal case participants. You can't attach service contacts to them, so
        case = DAObject("case")
        parse_case_info(self.proxy_conn, case, self.first_resp, "peoria")
        self.assertEqual(len(case.attorneys.keys()), 2)
        self.assertTrue("e650827f-3a2b-4550-b76c-f7d22ed479ff" in case.attorneys.keys())
        self.assertTrue("7ff43f9b-53ff-4e6d-9253-e393318549d0" in case.attorneys.keys())
