#!/usr/bin/env python3

import os
import json

import requests
import http.client as http_client
import logging

class ProxyConnection(object):
    def __init__(self, url: str):
        self.base_url = url
        self.proxy_client = requests.Session()
        self.proxy_client.headers = {'Content-type': 'text/json', 'Accept': 'application/json'}
        self.verbose = False
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

    def RegisterUser(self, person_to_reg, password):
        # Rely on DA to answer the Address and phone questions if necessary
        pass

        reg_obj = factory.RegistrationRequestType(
            RegistrationType='Individual',
            Email=person_to_reg.email,
            FirstName=person_to_reg.name.first,
            MiddleName=person_to_reg.name.middle,
            LastName=person_to_reg.name.last,
            Password=password,
            StreetAddressLine1=person_to_reg.address.address,
            StreetAddressLine2=person_to_reg.address.unit,
            City=person_to_reg.address.city,
            StateCode=person_to_reg.address.state,
            ZipCode=person_to_reg.address.zip_code,
            CountryCode=person_to_reg.address.country,
            # only grabs the first 10 digits of the phone number
            PhoneNumber=person_to_reg.sms_number()[-10:])

        return self.send_message('RegisterUser', reg_obj)

    # TODO(brycew): fill these in as we progress
    # Managing Firm Users
    def GetUserList(self):
        pass

    def GetUser(self):
        pass

    def AddUserRole(self):
        pass

    def RemoveUserRole(self):
        pass

    def UpdateUser(self):
        pass

    def RemoveUser(self):
        pass

    def ResetUserPassword(self):
        pass

    def ResendActivitationEmail(self):
        pass

    def GetNotificationPreferencesList(self):
        pass

    # Managing a Firm
    def GetFirm(self):
        pass

    def UpdateFirm(self):
        pass

    # Managing Attorneys
    def GetAttorneyList(self):
        pass

    def GetAttorney(self):
        pass

    def UpdateAttorney(self):
        pass

    def CreateAttorney(self):
        pass

    def RemoveAttorney(self):
        pass

    # Managing Payment Accounts
    def GetPaymentAccountTypeList(self):
        pass

    def GetPaymentAccountList(self):
        pass

    def GetPaymountAccount(self):
        pass

    def UpdatePaymentAccount(self):
        pass

    def CreatePaymentAccount(self):
        pass

    def RemovePaymentAccount(self):
        pass

    # TODO(brycew): there is no documentation for these two calls...
    def GetVitalChekPaymentAccountId(self):
        pass

    def CreateInactivePaymentAccount(self):
        pass

    # Managing Service Contacts
    def GetServiceContactList(self):
        pass

    def GetServiceContact(self):
        pass

    def UpdateServiceContact(self):
        pass

    def CreateServiceContact(self):
        pass

    def RemoveServiceContact(self):
        pass

    # Using Service Contacts
    def AttachServiceContact(self):
        pass

    def DetachServiceContact(self):
        pass

    def GetPublicList(self):
        pass

    # Global Payment Accounts
    def GetGlobalPaymentAccountList(self):
        pass

    def GetGlobalPaymentAccount(self):
        pass

    def UpdateGlobalPaymentAccount(self):
        pass

    def CreateGlobalPaymentAccount(self):
        pass

    def RemoveGlobalPaymentAccount(self):
        pass

    def AuthenticateUser(self, email: str, password: str):
        auth_obj = {'username': email, 'password': password} 
        resp = self.proxy_client.post(self.base_url + 'adminusers/authenticate/', data=json.dumps(auth_obj))
        if resp.status_code == requests.codes.ok:
            data = resp.json()
            if data['error']['errorCode'] == '0':
                self.proxy_client.auth = (email, data['passwordHash'])
                self.authed_user_id = data['userID']
        return resp

    @staticmethod
    def verbose_logging(turn_on: bool):
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def ChangePassword(self):
        pass

    def SelfResendActivationEmail(self, email: str):
        resend_obj = {'email': email}
        return self.proxy_client.post(self.base_url + 'adminusers/user/resend_activation_email')

    def UpdateNotificationPreferences(self):
        pass

    def GetNoficitationPreferences(self):
        pass

    def UpdateUser(self):
        pass

    def GetUser(self):
        pass

class MockPerson(object):
    def __init__(self):
        self.email = 'bwilley@suffolk.edu'
        # Neat trick: https://stackoverflow.com/a/24448351/11416267
        self.name = type('', (), {})()
        self.name.first = 'Bryce'
        self.name.middle = 'Steven'
        self.name.last = 'Willey'
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
    client = ProxyConnection(os.getenv('proxy_url'))
    x = MockPerson()
    #response = client.RegisterUser(x, 'TestPassword1')
    response = client.AuthenticateUser('bwilley@suffolk.edu', os.getenv('bryce_user_password'))
    print(response.status_code)
    print(response.text)

