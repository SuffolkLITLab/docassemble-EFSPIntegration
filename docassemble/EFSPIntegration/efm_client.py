#!/usr/bin/env python3

import os
import json
import sys

import requests
from requests import ConnectionError
import http.client as http_client
import logging
from typing import List
from docassemble.base.functions import all_variables, get_config 
from docassemble.AssemblyLine.al_document import ALDocumentBundle

class ApiResponse(object):
  def __init__(self, response_code, error_msg:str, data):
    self.response_code = response_code
    self.error_msg = error_msg
    self.data = data

  def __str__(self):
    if self.error_msg:
      return f'response_code: {self.response_code}, error_msg: {self.error_msg}, data: {self.data}'
    else:
      return f'response_code: {self.response_code}, data: {self.data}'

def _recursive_give_data_url(bundle):
  """Prepares the document types by setting a semi-permanent enabled and a data url"""
  for doc in bundle:
    if isinstance(doc, ALDocumentBundle):
      recursive_give_data_url(doc)
    else:
      doc.proxy_enabled = doc.enabled
      if doc.proxy_enabled:
        doc.data_url = doc.as_pdf().url_for(temporary=True)
      del doc.enabled

class ProxyConnection(object):
    def __init__(self, url:str=None, api_key:str=None):
      temp_efile_config = get_config('efile proxy', {})
      if url is None:
        url = temp_efile_config.get('url')
      if api_key is None:
        api_key = temp_efile_config.get('api key')

      if not url.endswith('/'):
        url = url + '/'
      self.base_url = url
      self.api_key = api_key
      self.proxy_client = requests.Session()
      self.proxy_client.headers = {
        'Content-type': 'application/json', 
        'Accept': 'application/json',
      }
      self.verbose = False
      self.authed_user_id = None
      self.set_verbose_logging(True)

    def _call_proxy(self, send_func):
      try:
        resp = send_func()
        if resp.status_code == 401:
          auth_resp = self.AuthenticateUser()
          if auth_resp.response_code == 200:
            resp = send_func()
      except ConnectionError as ex:
        return ProxConnection.user_visible_resp(f'Could not connect to the Proxy server at {self.base_url}')
      return ProxyConnection.user_visible_resp(resp)

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
        return ApiResponse(501, 'Not yet implemented (on both sides)', None)
      # Something went wrong with us / some error in requests
      if isinstance(resp, str):
        return ApiResponse(-1, resp, None)
      try:
        data = resp.json()
        return ApiResponse(resp.status_code, None, data)
      except:
        return ApiResponse(resp.status_code, resp.text, None)

    def AuthenticateUser(self, tyler_email:str=None, tyler_password:str=None, jeffnet_key:str=None):
      temp_efile_config = get_config('efile proxy', {})
      if tyler_email is None:
        tyler_email = temp_efile_config.get('tyler email')
      if tyler_password is None:
        tyler_password = temp_efile_config.get('tyler password')
      if jeffnet_key is None:
        jeffnet_key = temp_efile_config.get('jeffnet api token')
      auth_obj = {}
      auth_obj['api_key'] = self.api_key
      if jeffnet_key:
        auth_obj['jeffnet'] = {'key': jeffnet_key}
      if tyler_email and tyler_password:
        auth_obj['tyler'] = {'username': tyler_email, 'password': tyler_password}
      try:
        resp = self.proxy_client.post(self.base_url + 'adminusers/authenticate/', data=json.dumps(auth_obj))
        if resp.status_code == requests.codes.ok:
          self.active_token = resp.text
          self.proxy_client.headers['X-API-KEY'] = self.active_token
          # self.authed_user_id = data['userID']
      except ConnectionError as ex:
        return ProxConnection.user_visible_resp(f'Could not connect to the Proxy server at {self.base_url}')
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

      send = lambda: self.proxy_client.put(self.base_url + 'adminusers/users', data=json.dumps(reg_obj))
      return self._call_proxy(send)

    # Managing Firm Users

    def GetUserList(self):
      send = lambda: self.proxy_client.get(self.base_url + 'adminusers/users') 
      return self._call_proxy(send) 

    def GetUser(self, id:str):
      #if id is None:
      #    id = self.authed_user_id
      send = lambda: self.proxy_client.get(self.base_url + f'adminusers/users/{id}')
      return self._call_proxy(send) 

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
      send = lambda: self.proxy_client.get(self.base_url + 'adminusers/notification_options').json()
      return self._call_proxy(send)

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
      send = lambda: self.proxy_client.get(self.base_url + 'firmattorneyservice/firm')
      return self._call_proxy(send) 

    def UpdateFirm(self, firm_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    # Managing Attorneys
    def GetAttorneyList(self, firm_id):
        return ProxyConnection.user_visible_resp(None)

    def GetAttorney(self, firm_id, attorney_id):
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
      send = lambda: self.proxy_client.get(self.base_url + 'payments/global_payment')
      return self._call_proxy(send)

    def GetGlobalPaymentAccount(self, global_payment_account_id):
      send = lambda: self.proxy_client.get(self.base_url + f'payments/global_payment/{global_payment_account_id}') 
      return self._call_proxy(send)

    def UpdateGlobalPaymentAccount(self, global_payment_account_id, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def CreateGlobalPaymentAccount(self, **kwargs):
        return ProxyConnection.user_visible_resp(None)

    def RemoveGlobalPaymentAccount(self, global_payment_account_id):
        return ProxyConnection.user_visible_resp(None)

    def GetCourts(self):
      send = lambda: self.proxy_client.get(self.base_url + f'filingreview/courts')
      return self._call_proxy(send)

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
      _recursive_give_data_url(al_court_bundle)
      all_vars = json.dumps(all_variables())
      send = lambda: self.proxy_client.post(self.base_url + f'filingreview/court/{court_id}/check_filing', data=all_vars)
      return self._call_proxy(send)
      
    def FileForReview(self, court_id:str, al_court_bundle:ALDocumentBundle):
      _recursive_give_data_url(al_court_bundle)
      all_vars_obj = all_variables()
      all_vars_obj['tyler_payment_id'] = get_config('efile proxy').get('tyler payment id')
      all_vars = json.dumps(all_vars_obj)
      send = lambda: self.proxy_client.post(self.base_url + f'filingreview/court/{court_id}/filing', 
            data=all_vars)
      return self._call_proxy(send)

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
