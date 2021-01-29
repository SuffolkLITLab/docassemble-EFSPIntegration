#!/usr/bin/env python3

import zeep

from deprecated import deprecated


class EFMFirmConnection(object):
    def __init__(self, url):
        self.soap_client = zeep.Client(wsdl=url)

    def RegisterUser(self, person_to_reg, password):
        # Rely on DA to answer the Address and phone questions if necessary
        factory = self.soap_client.type_factory('urn:tyler:efm:services:schema:RegistrationRequest')
        reg_obj = factory.RegistrationRequest(
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

        return self.soap_client.service.RegisterUser(reg_obj)

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
