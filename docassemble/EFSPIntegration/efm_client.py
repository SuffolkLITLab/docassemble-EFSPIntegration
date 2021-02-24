#!/usr/bin/env python3

import zeep
from zeep.wsse.signature import Signature

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


class EFMFirmConnection(object):
    def __init__(self, url: str, private_key_fn: str, public_key_fn: str, password: str):
        self.soap_client = zeep.Client(
            wsdl=url,
            wsse=Signature(private_key_fn, public_key_fn, password))


    def send_message(self, service_name: str, obj_to_send):
        if self.verbose:
            node = self.soap_client.create_message(soap_client.service, service_name, obj_to_send)
            print(etree.tostring(node, pretty_print=True).decode())
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
            CountryCode=person_to_reg.address.county,
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
