import json
import unittest
from unittest.mock import MagicMock
from pathlib import Path
from docassemble.base.core import DAObject
from docassemble.AssemblyLine.al_general import ALIndividual
from ..efm_client import ProxyConnection, ApiResponse
from ..conversions import parse_case_info, parse_service_contacts

class TestConversions(unittest.TestCase):
  def setUp(self):
    with open(Path(__file__).parent / 'vars.json', 'r') as file:
      full_json = json.load(file).get('variables')
    self.my_var = full_json.get('my_var').get('data')
    self.my_service_contacts = full_json.get('my_service_contacts')
    self.proxy_conn = ProxyConnection()
    self.proxy_conn.get_case = MagicMock('get_case', return_value=ApiResponse(200, '', self.my_var))

  def test_parse_case_info(self):
    """Makes sure that participants of the case are parsed fully, needed """
    case = DAObject('case')
    parse_case_info(self.proxy_conn, case, self.my_var, 'adams', {})
    self.assertEqual(len(case.participants), 2)
    for partip in case.participants:
      self.assertIsInstance(partip, ALIndividual)
      self.assertIn(partip.person_type, ['ALIndividual', 'business'])
      self.assertNotEqual(partip.name.first, None)
      if partip.person_type == 'ALIndividual':
        self.assertNotEqual(partip.name.last, None)
        # Make sure the name is title case: first letter is upper, everything else lower
        self.assertEqual(partip.name.first[0], partip.name.first[0].upper())
        self.assertEqual(partip.name.first[1], partip.name.first[1].lower())
        self.assertTrue(hasattr(partip, 'address'))
        self.assertEqual(partip.address.city, 'RADOM')
        self.assertEqual(partip.address.zip_code, '62876')
        self.assertFalse(hasattr(partip, 'phone_number'))
        self.assertFalse(hasattr(partip, 'email'))
      self.assertTrue(hasattr(partip, 'party_type'))
      self.assertTrue(hasattr(partip, 'party_type_name'))
      self.assertTrue(hasattr(partip, 'tyler_id'))
    self.assertEqual(case.participants[0].instanceName, 'case.participants[0]')

  def test_parse_service_contact(self):
    no_contacts = parse_service_contacts([])
    self.assertEqual(len(no_contacts), 0)

    service_contacts = parse_service_contacts(self.my_service_contacts)
    self.assertEqual(len(service_contacts), 1)
    self.assertEqual(service_contacts[0][0], "6707a4f8-9f4c-4bbb-8498-ed4890208c6d")
    self.assertEqual(service_contacts[0][1], "Bryce Willey")
