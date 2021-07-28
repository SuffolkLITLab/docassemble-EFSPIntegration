#!/usr/bin/env python3

import os
import json
import sys

import requests
import http.client as http_client
import logging
from typing import Dict, List
from docassemble.base.functions import all_variables 
from docassemble.base.util import log 
from docassemble.AssemblyLine.al_document import ALDocumentBundle

class ApiResponse(object):
  def __init__(self, response_code, error_msg, data):
    self.response_code = response_code
    self.error_msg = error_msg
    self.data = data

  def __str__(self):
    if self.error_msg:
      return f'response_code: {self.response_code}, error_msg: {self.error_msg}, data: {data}'
    else:
      return f'response_code: {self.response_code}, data: {self.data}'

class ProxyConnection(object):
    def __init__(self, url: str, api_token: str):
        if not url.endswith('/'):
          url = url + '/'
        self.base_url = url
        self.api_token = api_token
        self.proxy_client = requests.Session()
        self.proxy_client.headers = {
          'Content-type': 'application/json', 
          'Accept': 'application/json',
          'X-API-KEY': self.api_token,
        }
        self.verbose = False
        self.authed_user_id = None
        self.set_verbose_logging(True)

    @staticmethod
    # TODO(brycew): this is old zeep logging: update to use requests
    def verbose_logging(turn_on: bool):
        if turn_on:
            http_client.HTTPConnection.debuglevel = 1
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True

    def set_verbose_logging(self, turn_on: bool): 
        if self.verbose != turn_on:
            ProxyConnection.verbose_logging(turn_on)
        self.verbose = turn_on

    @staticmethod
    def user_visible_resp(resp):
      """By default, the responses from `requests` aren't pickable, which causes
         some issues in Docassemble if you are using this in interviews. This function
         takes the essentials of a response and puts in into a simple object.
      """
      if resp is None:
        return ApiResponse(200, 'Not yet implemented', None)
      try:
        data = resp.json()
        return ApiResponse(resp.status_code, None, data)
      except:
        return ApiResponse(resp.status_code, resp.text, None)

    def AuthenticateUser(self, email:str=None, password:str=None, jeffnet_token:str=None):
      auth_obj = {}
      if jeffnet_token:
        auth_obj['jeffnet'] = {'token': jeffnet_token}
      if email and password:
        auth_obj['tyler'] = {'username': email, 'password': password}
      resp = self.proxy_client.post(self.base_url + 'adminusers/authenticate/', data=json.dumps(auth_obj))
      if resp.status_code == requests.codes.ok:
        self.proxy_client.headers['X-API-KEY'] = resp.text
        # self.authed_user_id = data['userID']
      print(resp.status_code)
      print(resp.text)
      print(resp.reason)
      print(resp.content)
      return ProxyConnection.user_visible_resp(resp)

    def RegisterUser(self, person_to_reg, password:str, registration_type:str='INDIVIDUAL'):
        reg_obj = {
            'registrationType': registration_type,
            'email': person_to_reg.email,
            'firstName': person_to_reg.name.first,
            'middleName': person_to_reg.name.middle,
            'lastName': person_to_reg.name.last,
            'password': password,
            'streetAddressLine1': person_to_reg.address.address,
            'streetAddressLine2': person_to_reg.address.unit,
            'city': person_to_reg.address.city,
            'stateCode': person_to_reg.address.state,
            'zipCode': person_to_reg.address.zip_code,
            'countryCode': person_to_reg.address.country,
            # only grabs the first 10 digits of the phone number
            'phoneNumber': person_to_reg.sms_number()[-10:]
        }

        resp = self.proxy_client.put(self.base_url + 'adminusers/users', data=json.dumps(reg_obj))
        print(resp.status_code)
        print(resp.text)
        print(resp.reason)
        return ProxyConnection.user_visible_resp(resp)

    # Managing Firm Users

    def GetUserList(self):
        resp = self.proxy_client.get(self.base_url + 'adminusers/users') 
        return ProxyConnection.user_visible_resp(resp)

    def GetUser(self, id:str):
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.get(self.base_url + f'adminusers/users/{id}')
        return ProxyConnection.user_visible_resp(resp)

    def GetUserRole(self, id:str):
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.get(self.base_url + f'adminuser/users/{id}/roles')
        return ProxyConnection.user_visible_resp(resp)

    def AddUserRole(self, roles:List[dict], id:str):
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.post(self.base_url + f'adminusers/users/{id}/roles', data=json.dumps(roles))
        return ProxyConnection.user_visible_resp(resp)

    def RemoveUserRole(self, roles:List[dict], id:str):
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.delete(self.base_url + f'adminuser/users/{id}/roles')
        return ProxyConnection.user_visible_resp(resp)

    def ChangePassword(self):
        return ProxyConnection.user_visible_resp(None)

    def SelfResendActivationEmail(self, email: str):
        resp = self.proxy_client.post(self.base_url + 'adminusers/user/resend_activation_email', 
            data=email)
        return ProxyConnection.user_visible_resp(resp)

    # TODO(brycew): not tested
    def ResendActivitationEmail(self, id:str):
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.post(self.base_url + f'adminusers/users/{id}/resend_activation_email')
        return ProxyConnection.user_visible_resp(resp)

    # TODO(brycew): not tested
    def UpdateNotificationPreferences(self):
        return ProxyConnection.user_visible_resp(None)


    # TODO(brycew): not tested
    def GetNoficitationPreferenceOptions(self):
        return self.proxy_client.get(self.base_url + 'adminusers/notification_options').json()

    # TODO(brycew): not tested
    def UpdateUser(self, email:str, first_name:str, middle_name:str, last_name:str, id:str):
        updated_user = {'email': email, 'firstName': first_name, 'middleName': middle_name, 'lastName': last_name}
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.post(self.base_url + f'adminusers/users/{id}', data=json.dumps(updated_user))
        return ProxyConnection.user_visible_resp(resp)

    def RemoveUser(self, id:str):
        #if id is None:
        #    id = self.authed_user_id
        resp = self.proxy_client.delete(self.base_url + f'adminusers/users/{id}')
        return ProxyConnection.user_visible_resp(resp)

    # TODO(brycew): not tested
    def ResetUserPassword(self, email:str):
      resp = self.proxy_client.post(self.base_url + 'adminusers/user/reset_password', data=email)
      return ProxyConnection.user_visible_resp(resp)

    # Managing a Firm
    def GetFirm(self, firm_id):
      resp = self.proxy_client.get(self.base_url + 'firmattorneyservice/firm')
      return ProxyConnection.user_visible_resp(resp)

    def UpdateFirm(self, firm_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    # Managing Attorneys
    def GetAttorneyList(self, firm_id):
        return ProxyConnection.user_visible_resp(None)

    def GetAttorney(self, firm_id, attorney_id),:
        return ProxyConnection.user_visible_resp(None)

    def UpdateAttorney(self, firm_id, attorney_id):
        return ProxyConnection.user_visible_resp(None)

    def CreateAttorney(self, firm_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def RemoveAttorney(self, firm_id, attorney_id):
        return ProxyConnection.user_visible_resp(None)

    # Managing Payment Accounts
    def GetPaymentAccountTypeList(self):
        return ProxyConnection.user_visible_resp(None)

    def GetPaymentAccountList(self, firm_id):
        return ProxyConnection.user_visible_resp(None)

    def GetPaymountAccount(self, firm_id, payment_account_id):
        return ProxyConnection.user_visible_resp(None)

    def UpdatePaymentAccount(self, firm_id, payment_account_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def CreatePaymentAccount(self, firm_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def RemovePaymentAccount(self, firm_id, payment_account_id):
        return ProxyConnection.user_visible_resp(None)

    # TODO(brycew): there is no documentation for these two calls...
    # QS: VitalCheck is a background check service from Lexis
    def GetVitalChekPaymentAccountId(self, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def CreateInactivePaymentAccount(self, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    # Managing Service Contacts
    # Service contacts are part of the `firm` hierarchy
    def GetServiceContactList(self, firm_id):
        return ProxyConnection.user_visible_resp(None)

    def GetServiceContact(self, firm_id, service_contact_id):
        return ProxyConnection.user_visible_resp(None)

    def UpdateServiceContact(self, firm_id, service_contact_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def CreateServiceContact(self, firm_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def RemoveServiceContact(self, firm_id, service_contact_id):
        return ProxyConnection.user_visible_resp(None)

    # Using Service Contacts
    def AttachServiceContact(self, firm_id, service_contact_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def DetachServiceContact(self, firm_id, service_contact_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    # TODO(QS): should this name include ServiceContact?
    def GetPublicList(self, firm_id):
        return ProxyConnection.user_visible_resp(None)

    # Global Payment Accounts
    def GetGlobalPaymentAccountList(self):
        return ProxyConnection.user_visible_resp(None)

    def GetGlobalPaymentAccount(self, global_payment_account_id):
        return ProxyConnection.user_visible_resp(None)

    def UpdateGlobalPaymentAccount(self, global_payment_account_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def CreateGlobalPaymentAccount(self, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def RemoveGlobalPaymentAccount(self, global_payment_account_id):
        return ProxyConnection.user_visible_resp(None)

    def GetCourts(self):
        resp = self.proxy_client.get(self.base_url + f'filingreview/courts')
        return ProxyConnection.user_visible_resp(resp)

    def GetFilingList(self, court_id:str):
        resp = self.proxy_client.get(self.base_url + f'filingreview/court/{court_id}/filings')
        return ProxyConnection.user_visible_resp(resp)

    def GetFiling(self, court_id:str, filing_id:str):
        resp = self.proxy_client.get(self.base_url + f'filingreview/court/{court_id}/filing/{filing_id}')
        return ProxyConnection.user_visible_resp(resp)

    def GetFilingStatus(self, court_id:str, filing_id:str):
        resp = self.proxy_client.get(self.base_url + f'filingreview/court/{court_id}/filing/{filing_id}/status')
        return ProxyConnection.user_visible_resp(resp)

    def CancelFilingStatus(self, court_id:str, filing_id:str):
        resp = self.proxy_client.delete(self.base_url + f'filingreview/court/{court_id}/filing/{filing_id}')
        return ProxyConnection.user_visible_resp(resp)

    def CheckFiling(self, court_id:str, al_court_bundle:ALDocumentBundle):
        def recursive_give_data_url(bundle):
            for doc in bundle:
                if isinstance(doc, ALDocumentBundle):
                    recursive_give_data_url(doc)
                else:
                    doc.data_url = doc.as_pdf().url_for(temporary=True)
        recursive_give_data_url(al_court_bundle)
        all_vars = json.dumps(all_variables())
        resp = self.proxy_client.post(self.base_url + f'filingreview/court/{court_id}/check_filing', data=all_vars)
        return ProxyConnection.user_visible_resp(resp)

    def FileForReview(self, court_id:str, al_court_bundle:ALDocumentBundle):
        def recursive_give_data_url(bundle):
            for doc in bundle:
                if isinstance(doc, ALDocumentBundle):
                    recursive_give_data_url(doc)
                else:
                    doc.data_url = doc.as_pdf().url_for(temporary=True)

        recursive_give_data_url(al_court_bundle)
        all_vars = json.dumps(all_variables())
        resp = self.proxy_client.post(self.base_url + f'filingreview/court/{court_id}/filing', 
            data=all_vars)
        return ProxyConnection.user_visible_resp(resp)
        

class MockPerson(object):
    def __init__(self):
        self.email = 'thesurferdude@comcast.net' 
        # Neat trick: https://stackoverflow.com/a/24448351/11416267
        self.name = type('', (), {})()
        self.name.first = 'B'
        self.name.middle = 'S'
        self.name.last = 'W'
        self.address = type('', (), {})()
        self.address.address = '123 Fakestreet Ave'
        self.address.unit = 'Apt 1'
        self.address.city = 'Boston'
        self.address.state = 'MA'
        self.address.zip_code = '12345'
        self.address.country = 'US'

    def sms_number(self) -> str:
        return '1234567890'


if __name__ == '__main__':
    client = ProxyConnection(sys.argv[1]) # os.getenv('proxy_url'))
    x = MockPerson()
    #response = client.RegisterUser(x, 'TestPassword1')
    response = client.AuthenticateUser('thesurferdude@comcast.net', 'Password1') #os.getenv('bryce_user_password'))
    x = MockPerson()
    resp = client.RemoveUser() 
    print(resp)

