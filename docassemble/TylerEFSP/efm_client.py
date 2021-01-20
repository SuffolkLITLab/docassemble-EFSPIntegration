#!/usr/bin/env python3

import zeep


def get_soap_client(url):
    return zeep.Client(wsdl=url)


def register_user(client, email, first_name, last_name, password, address_1, city, state, zip_code, country, phone):
    # Gotten from python -mzeep file:///.../Artifacts/Schema/EFMFirmService.wsdl
    reg_type = client.get_type('ns1:RegistrationRequestType')
    r = reg_type(RegistrationType='Individual', Email=email,
                 FirstName=first_name, LastName=last_name, Password=password,
                 StreetAddressLine1=address_1, City=city, StateCode=state, 
                 ZipCode=zip_code, CountryCode=country, PhoneNumber=phone)
    #client.service.RegistrerUser(r)
    return client.create_message(client.service, 'RegisterUser', r)