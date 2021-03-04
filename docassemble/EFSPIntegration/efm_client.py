#!/usr/bin/env python3

import zeep
import datetime
from zeep.wsse.username import UsernameToken
from zeep.wsse.utils import WSU
from zeep.wsse.signature import BinarySignature
import os
from lxml import etree

from deprecated import deprecated

# Bunch of junk code to work into objects later:
# Works!
# xmlsec.Key.from_memory(all_bytes, xmlsec.KeyFormat.PKCS12_PEM, os.getenv('x509_password'))
# Doesn't work, maybe not needed?
# key.load_cert_from_memory(all_bytes, xmlsec.KeyFormat.PKCS12_PEM)
"""func=xmlSecOpenSSLAppCertLoadBIO:file=app.c:line=1057:obj=unknown:subj=unknown:error=17:invalid format:format=6
func=xmlSecOpenSSLAppKeyCertLoadBIO:file=app.c:line=477:obj=x509:subj=xmlSecOpenSSLAppCertLoad:error=1:xmlsec library function failed: 
func=xmlSecOpenSSLAppKeyCertLoadMemory:file=app.c:line=424:obj=unknown:subj=xmlSecOpenSSLAppKeyCertLoadBIO:error=1:xmlsec library function failed: 
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
xmlsec.InternalError: (-1, 'cannot load cert')
"""
# https://github.com/mvantellingen/python-zeep/blob/master/src/zeep/wsse/signature.py
# https://github.com/lsh123/xmlsec/commit/97b14cbc1100a53bd79c10194f33e95e755760ab
# https://www.aleksey.com/xmlsec/api/xmlsec-examples-sign-x509.html
# https://github.com/mehcode/python-xmlsec/blob/18cbae111e2d1afff99687211aadb49c33c4a8f5/src/constants.c#L402

"""
>>> soap_client.service.RegisterUser(reg_obj)
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/brycew/Developer/LITLab/litlab_venv/lib/python3.6/site-packages/zeep/proxy.py", line 51, in __call__
    kwargs,
  File "/home/brycew/Developer/LITLab/litlab_venv/lib/python3.6/site-packages/zeep/wsdl/bindings/soap.py", line 135, in send
    return self.process_reply(client, operation_obj, response)
  File "/home/brycew/Developer/LITLab/litlab_venv/lib/python3.6/site-packages/zeep/wsdl/bindings/soap.py", line 219, in process_reply
    client.wsse.verify(doc)
  File "/home/brycew/Developer/LITLab/litlab_venv/lib/python3.6/site-packages/zeep/wsse/signature.py", line 73, in verify
    _verify_envelope_with_key(envelope, key)
  File "/home/brycew/Developer/LITLab/litlab_venv/lib/python3.6/site-packages/zeep/wsse/signature.py", line 310, in _verify_envelope_with_key
    raise SignatureVerificationFailed()
zeep.exceptions.SignatureVerificationFailed
"""


class EFMFirmConnection(object):
    def __init__(self, url: str, private_key_fn: str, public_key_fn: str, password: str):
        # From https://docs.python-zeep.org/en/master/wsse.html#usernametoken-with-timestamp-token
        timestamp_token = WSU.Timestamp()
        today_datetime = datetime.datetime.now()
        expires_datetime = today_datetime + datetime.timedelta(minutes=10)
        timestamp_elements = [
            WSU.Created(today_datetime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
            WSU.Expires(expires_datetime.strftime("%F-%m-%dT%H:%M:%S.%fZ"))
        ]
        timestamp_token.extend(timestamp_elements)
        user_name_token = UsernameToken('TODOusername', 'TODOpassword', timestamp_token=timestamp_token)
        signature = BinarySignature(private_key_fn, public_key_fn, password)

        self.soap_client = zeep.Client(
            wsdl=url,
            wsse=[user_name_token, signature])
        self.verbose = True


    def send_message(self, service_name: str, obj_to_send):
        if self.verbose:
            node = self.soap_client.create_message(self.soap_client.service, service_name, obj_to_send)
            print(etree.tostring(node, pretty_print=True).decode())
        with self.soap_client.settings(raw_response=True):
            return self.soap_client.service[service_name](obj_to_send)

    def RegisterUser(self, person_to_reg, password):
        # Rely on DA to answer the Address and phone questions if necessary
        factory = self.soap_client.type_factory('urn:tyler:efm:services:schema:RegistrationRequest')
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


class EFMUserServiceConnection(object):
    def __init__(self, url):
        self.soap_client = zeep.Client(wsdl=url)

    # TODO(brycew): is there a req for users to have access to these?
    def AuthenticateUser(self):
        pass

    def ChangePassword(self):
        pass

    @deprecated
    def GetPasswordQuestion(self):
        pass

    def SelfResendActivationEmail(self):
        pass

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
    client = EFMFirmConnection(os.getenv('firm_url'), 
                               '/home/brycew/Developer/LITLab/x509_stuff/Suffolk.encrypted.priv.key', 
                               '/home/brycew/Developer/LITLab/x509_stuff/Suffolk.pem',
                               os.getenv('x509_password'))
    x = MockPerson()
    client.verbose = True
    response = client.RegisterUser(x, 'TestPassword1')
    print(response.status_code)
    print(response.text)
    print(response.content)

