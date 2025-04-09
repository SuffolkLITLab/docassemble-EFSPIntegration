#!/usr/bin/env python3

"""
The base python client used to communicate with the E-file proxy server.

Doesn't include anything from docassemble, and can be used without having it installed.
"""

import re
import logging
import requests
from requests import Response
from datetime import datetime
from typing import Optional, Union, List, Dict
import http.client as http_client
from copy import deepcopy

__all__ = ["ApiResponse", "EfspConnection"]


class ApiResponse(object):
    def __init__(self, response_code: int, error_msg: Optional[str], data):
        self.response_code = response_code
        self.error_msg = error_msg
        self.data = data

    def __str__(self):
        if self.error_msg:
            return f"response_code: {self.response_code}, error_msg: {self.error_msg}, data: {self.data}"
        return f"response_code: {self.response_code}, data: {self.data}"

    def __repr__(self):
        return str(self)

    def is_ok(self):
        return self.response_code in [200, 201, 202, 203, 204, 205]


def _user_visible_resp(resp: Union[Response, str, None]) -> ApiResponse:
    """This function takes the essentials of a response and puts in into
    a simple object.
    """
    if resp is None:
        return ApiResponse(501, "Not yet implemented (on both sides)", None)
    # Something went wrong with us / some error in requests
    if isinstance(resp, str):
        return ApiResponse(-1, resp, None)
    try:
        data = resp.json()
        return ApiResponse(resp.status_code, None, data)
    except:
        return ApiResponse(resp.status_code, resp.text, None)


class EfspConnection:
    """A python client that communicates with the E-file proxy server."""

    def __init__(self, *, url: str, api_key: str, default_jurisdiction: str = None):
        """
        Args:
          url (str)
          api_key (str)
          default_jurisdiction (str)
        """
        if not url.endswith("/"):
            url = url + "/"

        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url

        self.base_url = url
        self.api_key = api_key
        self.proxy_client = requests.Session()
        self.active_token = None
        logging.info(f"setting default jurisdiction to {default_jurisdiction}")
        self.default_jurisdiction = default_jurisdiction
        self.proxy_client.headers.update(
            {
                "Content-type": "application/json",
                "Accept": "application/json",
            }
        )
        self.proxy_client.headers["X-API-KEY"] = api_key
        self.verbose = False
        self.authed_user_id = None

    def _call_proxy(self, send_func) -> ApiResponse:
        try:
            resp = send_func()
        except requests.ConnectionError as ex:
            return _user_visible_resp(
                f"Could not connect to the Proxy server at {self.base_url}: {ex}"
            )
        except requests.exceptions.MissingSchema as ex:
            return _user_visible_resp(f"Url {self.base_url} is not valid: {ex}")
        except requests.exceptions.InvalidURL as ex:
            return _user_visible_resp(f"Url {self.base_url} is not valid: {ex}")
        except requests.exceptions.RequestException as ex:
            return _user_visible_resp(f"Something went wrong with the request: {ex}")
        return _user_visible_resp(resp)

    @staticmethod
    def verbose_logging(turn_on: bool) -> None:
        if turn_on:
            http_client.HTTPConnection.debuglevel = 1
            logging.basicConfig()
            logging.getLogger().setLevel(logging.DEBUG)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.DEBUG)
            requests_log.propagate = True
        else:
            logging.getLogger().setLevel(logging.INFO)
            requests_log = logging.getLogger("requests.packages.urllib3")
            requests_log.setLevel(logging.INFO)
            requests_log.propagate = False

    def set_verbose_logging(self, turn_on: bool) -> None:
        if not self.verbose and turn_on:
            EfspConnection.verbose_logging(turn_on)
        elif self.verbose and not turn_on:
            EfspConnection.verbose_logging(turn_on)
        self.verbose = turn_on

    def full_url(self, endpoint: str, jurisdiction: str = None) -> str:
        if jurisdiction is None:
            jurisdiction = self.default_jurisdiction
        if any(
            [
                endpoint.startswith(service)
                for service in ["authenticate_user", "messages", "api_user_settings"]
            ]
        ):
            return self.base_url + endpoint
        return self.base_url + f"jurisdictions/{jurisdiction}/{endpoint}"

    def tyler_token(self) -> Optional[str]:
        token = self.proxy_client.headers.get(
            "TYLER-TOKEN-" + str(self.default_jurisdiction).upper()
        )
        if isinstance(token, bytes):
            return token.decode()
        return token

    def authenticate_user(
        self,
        *,
        tyler_email: Optional[str] = None,
        tyler_password: Optional[str] = None,
        jeffnet_key: Optional[str] = None,
        jurisdiction: str = None,
    ) -> ApiResponse:
        """
        Authenticates the user with the EFM server (not the E-file proxy).
        """

        if jurisdiction is None:
            jurisdiction = self.default_jurisdiction
        logging.info(f"authenticating with jurisdiction: {jurisdiction}")
        auth_obj: Dict[str, Union[str, Dict[str, str]]] = {}
        auth_obj["api_key"] = self.api_key
        if jeffnet_key:
            auth_obj["jeffnet"] = {"key": jeffnet_key}
        if tyler_email and tyler_password:
            auth_obj[f"tyler-{jurisdiction}"] = {
                "username": tyler_email,
                "password": tyler_password,
            }
        try:
            resp = self.proxy_client.post(self.base_url + "authenticate", json=auth_obj)
            if resp.status_code == requests.codes.ok:
                all_tokens = resp.json().get("tokens", {})
                for k, v in all_tokens.items():
                    self.proxy_client.headers[k] = v
                # self.authed_user_id = data['userID']
        except requests.ConnectionError as ex:
            return _user_visible_resp(
                f"Could not connect to the Proxy server at {self.base_url}"
            )
        except requests.exceptions.MissingSchema as ex:
            return _user_visible_resp(f"Url {self.base_url} is not valid: {ex}")
        except requests.exceptions.InvalidURL as ex:
            return _user_visible_resp(f"Url {self.base_url} is not valid: {ex}")
        except requests.exceptions.RequestException as ex:
            return _user_visible_resp(
                f'Something went wrong when connecting to {self.base_url + "authenticate"}: {ex}'
            )
        return _user_visible_resp(resp)

    def register_user(
        self,
        person: dict,
        registration_type: str,
        *,
        password: str = None,
        firm_name_or_id: str = None,
    ) -> ApiResponse:
        """
        registration_type needs to be INDIVIDUAL, FIRM_ADMINISTRATOR, or FIRM_ADMIN_NEW_MEMBER.
        If registration_type is INDIVIDUAL or FIRM_ADMINISTRATOR, you need a password.
        If it's FIRM_ADMINISTRATOR or FIRM_ADMIN_NEW_MEMBER, you need a firm_name_or_id
        """
        registration_type = registration_type.upper()
        if "phone_number" in person:
            phone_number = person["phone_number"]
        elif "mobile_number" in person:
            phone_number = person["mobile_number"]
        else:
            phone_number = ""
        reg_obj = {
            "registrationType": registration_type,
            "email": person.get("email"),
            "firstName": person.get("name", {}).get("first", ""),
            "middleName": person.get("name", {}).get("middle", ""),
            "lastName": person.get("name", {}).get("last", ""),
            "streetAddressLine1": person.get("address", {}).get("address", ""),
            "streetAddressLine2": person.get("address", {}).get("unit", ""),
            "city": person.get("address", {}).get("city", ""),
            "stateCode": person.get("address", {}).get("state", ""),
            "zipCode": person.get("address", {}).get("zip", ""),
            # Will error without it, and US is a good default
            "countryCode": person.get("address", {}).get("country", "US"),
            "phoneNumber": phone_number,
        }
        if registration_type != "INDIVIDUAL":
            reg_obj["firmName"] = firm_name_or_id
        if registration_type != "FIRM_ADMIN_NEW_MEMBER":
            reg_obj["password"] = password

        send = lambda: self.proxy_client.post(
            self.full_url("adminusers/users"), json=reg_obj
        )
        return self._call_proxy(send)

    def get_password_rules(self) -> ApiResponse:
        """
        Password rules are stored in the global court, id 0.

        TODO: They're in other courts too, including 1. Could they ever be different?
        """
        send = lambda: self.proxy_client.get(
            self.full_url("codes/courts/0/datafields/GlobalPassword")
        )
        return self._call_proxy(send)

    def is_valid_password(self, password: str) -> Optional[bool]:
        results = self.get_password_rules()
        if results.data:
            password_regex = results.data.get("regularexpression", ".*")
        else:
            logging.warning(str(results))
            password_regex = ".*"

        try:
            return bool(re.match(password_regex, password))
        except:
            return None

    # Managing Firm Users

    def get_user_list(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(self.full_url("adminusers/users"))
        return self._call_proxy(send)

    def get_users(self) -> ApiResponse:
        return self.get_user_list()

    def get_user(self, id: str = None) -> ApiResponse:
        if id is None:
            send = lambda: self.proxy_client.get(self.full_url("adminusers/user"))
        else:
            send = lambda: self.proxy_client.get(
                self.full_url(f"adminusers/users/{id}")
            )
        return self._call_proxy(send)

    def get_user_roles(self, id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"adminusers/users/{id}/roles")
        )
        return self._call_proxy(send)

    def add_user_roles(self, id: str, roles: List[dict]) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url(f"adminusers/users/{id}/roles"), json=roles
        )
        return self._call_proxy(send)

    def remove_user_roles(self, id: str, roles: List[dict]) -> ApiResponse:
        send = lambda: self.proxy_client.delete(
            self.full_url(f"adminusers/users/{id}/roles"), json=roles
        )
        return self._call_proxy(send)

    def change_password(self, id: str, email: str, new_password: str) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url(f"adminusers/users/{id}/password"),
            json={"email": email, "newPassword": new_password},
        )
        return self._call_proxy(send)

    def self_change_password(
        self, current_password: str, new_password: str
    ) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url("adminusers/user/password"),
            json={"currentPassword": current_password, "newPassword": new_password},
        )
        return self._call_proxy(send)

    def self_resend_activation_email(self, email: str) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url("adminusers/user/resend-activation-email"), data=email
        )
        return self._call_proxy(send)

    def resend_activation_email(self, id: str) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url(f"adminusers/users/{id}/resend-activation-email")
        )
        return self._call_proxy(send)

    def update_notification_preferences(
        self, notif_preferences: List[dict]
    ) -> ApiResponse:
        send = lambda: self.proxy_client.patch(
            self.full_url(f"adminusers/user/notification-preferences"),
            json=notif_preferences,
        )
        return self._call_proxy(send)

    def get_notification_preferences(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url("adminusers/user/notification-preferences")
        )
        return self._call_proxy(send)

    def get_notification_options(self) -> ApiResponse:
        """AKA NotificationPreferencesList"""
        send = lambda: self.proxy_client.get(
            self.full_url("adminusers/notification-options")
        )
        return self._call_proxy(send)

    def self_update_user(
        self,
        email: str = None,
        first_name: str = None,
        middle_name: str = None,
        last_name: str = None,
    ) -> ApiResponse:
        updated_user = {
            "email": email,
            "firstName": first_name,
            "middleName": middle_name,
            "lastName": last_name,
        }
        send = lambda: self.proxy_client.patch(
            self.full_url("adminusers/user"), json=updated_user
        )
        return self._call_proxy(send)

    def update_user(
        self,
        id: str,
        email: str = None,
        first_name: str = None,
        middle_name: str = None,
        last_name: str = None,
    ) -> ApiResponse:
        updated_user = {
            "email": email,
            "firstName": first_name,
            "middleName": middle_name,
            "lastName": last_name,
        }
        send = lambda: self.proxy_client.patch(
            self.full_url(f"adminusers/users/{id}"), json=updated_user
        )
        return self._call_proxy(send)

    def remove_user(self, id: str) -> ApiResponse:
        send = lambda: self.proxy_client.delete(self.full_url(f"adminusers/users/{id}"))
        return self._call_proxy(send)

    # TODO(brycew): not tested
    def reset_user_password(self, email: str) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url("adminusers/user/password/reset"), data=email
        )
        return self._call_proxy(send)

    ### Managing a Firm
    def get_firm(self) -> ApiResponse:
        """Gets info about the "firm" for an associated user. If a user is a pro-se, this
        contains their address information.
        """
        send = lambda: self.proxy_client.get(self.full_url("firmattorneyservice/firm"))
        return self._call_proxy(send)

    def update_firm(self, firm: dict) -> ApiResponse:
        """
        firm should have the below keys:
        * firstName, middleName, lastName if it's a person
        * firmName if it's a business
        * address (a dict), with keys addressLine1 addressLine2, city, state, zipCode, country
        * phoneNumber
        * email
        """
        send = lambda: self.proxy_client.patch(
            self.full_url("firmattorneyservice/firm"), json=firm
        )
        return self._call_proxy(send)

    ### Managing Attorneys
    def get_attorney_list(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url("firmattorneyservice/attorneys")
        )
        return self._call_proxy(send)

    def get_attorney(self, attorney_id):
        send = lambda: self.proxy_client.get(
            self.full_url(f"firmattorneyservice/attorneys/{attorney_id}")
        )
        return self._call_proxy(send)

    def update_attorney(
        self,
        attorney_id,
        bar_number: str = None,
        first_name: str = None,
        middle_name: str = None,
        last_name: str = None,
    ) -> ApiResponse:
        send = lambda: self.proxy_client.patch(
            self.full_url(f"firmattorneyservice/attorneys/{attorney_id}"),
            json={
                "barNumber": bar_number,
                "firstName": first_name,
                "middleName": middle_name,
                "lastName": last_name,
            },
        )
        return self._call_proxy(send)

    def create_attorney(
        self,
        bar_number: str,
        first_name: str,
        middle_name: str = None,
        last_name: str = None,
    ) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url("firmattorneyservice/attorneys"),
            json={
                "barNumber": bar_number,
                "firstName": first_name,
                "middleName": middle_name,
                "lastName": last_name,
            },
        )
        return self._call_proxy(send)

    def remove_attorney(self, attorney_id) -> ApiResponse:
        send = lambda: self.proxy_client.delete(
            self.full_url(f"firmattorneyservice/attorneys/{attorney_id}")
        )
        return self._call_proxy(send)

    ### Managing Payment Accounts
    def get_payment_account_type_list(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(self.full_url("payments/types"))
        return self._call_proxy(send)

    def get_payment_account_list(self, court_id: Optional[str] = None) -> ApiResponse:
        if not court_id:
            send = lambda: self.proxy_client.get(
                self.full_url("payments/payment-accounts")
            )
        else:
            params = {"court_id": court_id}
            send = lambda: self.proxy_client.get(
                self.full_url("payments/payment-accounts"), params=params
            )
        return self._call_proxy(send)

    def get_payment_account(self, payment_account_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"payments/payment-accounts/{payment_account_id}")
        )
        return self._call_proxy(send)

    def update_payment_account(
        self, payment_account_id: str, account_name: str = None, active: bool = True
    ) -> ApiResponse:
        send = lambda: self.proxy_client.patch(
            self.full_url(f"payments/payment-accounts/{payment_account_id}"),
            json={"account_name": account_name, "active": active},
        )
        return self._call_proxy(send)

    def remove_payment_account(self, payment_account_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.delete(
            self.full_url(f"payments/payment-accounts/{payment_account_id}")
        )
        return self._call_proxy(send)

    # Both types of accounts
    def create_waiver_account(self, account_name: str, is_global: bool) -> ApiResponse:
        url = self.full_url(
            "payments/global-accounts" if is_global else "payments/payment-accounts"
        )
        send = lambda: self.proxy_client.post(url, data=account_name)
        return self._call_proxy(send)

    # Global Payment Accounts
    def get_global_payment_account_list(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(self.full_url("payments/global-accounts"))
        return self._call_proxy(send)

    def get_global_payment_account(self, global_payment_account_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"payments/global-accounts/{global_payment_account_id}")
        )
        return self._call_proxy(send)

    def update_global_payment_account(
        self,
        global_payment_account_id: str,
        account_name: str = None,
        active: bool = True,
    ) -> ApiResponse:
        send = lambda: self.proxy_client.patch(
            self.full_url(f"payments/global-accounts/{global_payment_account_id}"),
            json={"account_name": account_name, "active": active},
        )
        return self._call_proxy(send)

    def remove_global_payment_account(
        self, global_payment_account_id: str
    ) -> ApiResponse:
        send = lambda: self.proxy_client.delete(
            self.full_url(f"payments/global-accounts/{global_payment_account_id}")
        )
        return self._call_proxy(send)

    ### Managing Service Contacts
    # Service contacts are part of the `firm` hierarchy
    def get_service_contact_list(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"firmattorneyservice/service-contacts")
        )
        return self._call_proxy(send)

    def get_service_contact(self, service_contact_id) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"firmattorneyservice/service-contacts/{service_contact_id}")
        )
        return self._call_proxy(send)

    def update_service_contact(
        self,
        service_contact_id: str,
        service_contact: dict,
        *,
        is_public: bool = None,
        is_in_master_list: bool = None,
        admin_copy: str = None,
    ) -> ApiResponse:
        service_contact_dict = deepcopy(service_contact)
        service_contact_dict["isPublic"] = is_public
        service_contact_dict["isInFirmMasterList"] = is_in_master_list
        service_contact_dict["administrativeCopy"] = admin_copy
        send = lambda: self.proxy_client.patch(
            self.full_url(f"firmattorneyservice/service-contacts/{service_contact_id}"),
            json=service_contact_dict,
        )
        return self._call_proxy(send)

    def create_service_contact(
        self,
        service_contact: dict,
        *,
        is_public: bool,
        is_in_master_list: bool,
        admin_copy: str = None,
    ) -> ApiResponse:
        service_contact_dict = deepcopy(service_contact)
        service_contact_dict["isPublic"] = is_public
        service_contact_dict["isInFirmMaster"] = is_in_master_list
        service_contact_dict["administrativeCopy"] = admin_copy
        send = lambda: self.proxy_client.post(
            self.full_url("firmattorneyservice/service-contacts"),
            json=service_contact_dict,
        )
        return self._call_proxy(send)

    def remove_service_contact(self, service_contact_id) -> ApiResponse:
        send = lambda: self.proxy_client.delete(
            self.full_url(f"firmattorneyservice/service-contacts/{service_contact_id}")
        )
        return self._call_proxy(send)

    def get_public_service_contacts(
        self,
        first_name: str = None,
        middle_name: str = None,
        last_name: str = None,
        email: str = None,
    ) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"firmattorneyservice/service-contacts/public"),
            json={
                "firstName": first_name,
                "middleName": middle_name,
                "lastName": last_name,
                "email": email,
            },
        )
        return self._call_proxy(send)

    # Using Service Contacts
    def attach_service_contact(
        self, service_contact_id: str, case_id: str, case_party_id: str = None
    ) -> ApiResponse:
        send = lambda: self.proxy_client.put(
            self.full_url(
                f"firmattorneyservice/service-contacts/{service_contact_id}/cases"
            ),
            json={"caseId": case_id, "casepartyId": case_party_id},
        )
        return self._call_proxy(send)

    def detach_service_contact(
        self, service_contact_id: str, case_id: str, case_party_id: str = None
    ) -> ApiResponse:
        url = self.full_url(
            f"firmattorneyservice/service-contacts/{service_contact_id}/cases/{case_id}"
        )
        send = lambda: self.proxy_client.delete(
            url, params={"case_party_id": case_party_id}
        )
        return self._call_proxy(send)

    def get_attached_cases(self, court_id: str, service_contact_id: str) -> ApiResponse:
        url = self.full_url(
            f"cases/courts/{court_id}/service-contacts/{service_contact_id}/cases"
        )
        send = lambda: self.proxy_client.get(url)
        return self._call_proxy(send)

    def get_public_list(self):
        send = lambda: self.proxy_client.get(
            self.full_url("firmattorneyservice/service-contacts/public")
        )
        return self._call_proxy(send)

    def get_courts(
        self, fileable_only: bool = False, with_names: bool = False
    ) -> ApiResponse:
        """Gets the list of courts."""
        params = {"fileable_only": fileable_only, "with_names": with_names}
        send = lambda: self.proxy_client.get(
            self.full_url("codes/courts"), params=params
        )
        return self._call_proxy(send)

    def get_court(self, court_id: str) -> ApiResponse:
        """Gets codes for a specific court"""
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/codes")
        )
        return self._call_proxy(send)

    def get_court_list(self) -> ApiResponse:
        """Gets a list of all of the courts that you can file into. Slightly more limited than
        [get_courts](#get_courts)"""
        send = lambda: self.proxy_client.get(self.full_url(f"filingreview/courts"))
        return self._call_proxy(send)

    def get_filing_list(
        self,
        court_id: str,
        user_id: str = None,
        start_date: datetime = None,
        before_date: datetime = None,
    ) -> ApiResponse:
        """Returns a list of filings that a particular user has made with a court."""
        params = {
            "user_id": user_id,
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
            "before_date": before_date.strftime("%Y-%m-%d") if before_date else None,
        }
        send = lambda: self.proxy_client.get(
            self.full_url(f"filingreview/courts/{court_id}/filings"), params=params
        )
        return self._call_proxy(send)

    def get_filing(self, court_id: str, filing_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"filingreview/courts/{court_id}/filings/{filing_id}")
        )
        return self._call_proxy(send)

    def get_policy(self, court_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"filingreview/courts/{court_id}/policy")
        )
        return self._call_proxy(send)

    def get_filing_status(self, court_id: str, filing_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"filingreview/courts/{court_id}/filings/{filing_id}/status")
        )
        return self._call_proxy(send)

    def cancel_filing_status(self, court_id: str, filing_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.delete(
            self.full_url(f"filingreview/courts/{court_id}/filings/{filing_id}")
        )
        return self._call_proxy(send)

    def check_filing(self, court_id: str, all_vars: dict) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"filingreview/courts/{court_id}/filing/check"), json=all_vars
        )
        return self._call_proxy(send)

    def file_for_review(self, court_id: str, all_vars: dict) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url(f"filingreview/courts/{court_id}/filings"), json=all_vars
        )
        return self._call_proxy(send)

    def get_service_types(self, court_id: str, all_vars: dict = None) -> ApiResponse:
        """Checks the court info: if it has conditional service types, call a special API with all filing info so far to get service types"""
        court_info = self.get_court(court_id)
        if court_info.data.get("hasconditionalservicetypes") and all_vars:
            send = lambda: self.proxy_client.get(
                self.full_url(f"filingreview/courts/{court_id}/filing/servicetypes"),
                json=all_vars,
            )
            return self._call_proxy(send)
        else:
            return self.get_service_type_codes(court_id)

    def calculate_filing_fees(self, court_id: str, all_vars: dict) -> ApiResponse:
        send = lambda: self.proxy_client.post(
            self.full_url(f"filingreview/courts/{court_id}/filing/fees"), json=all_vars
        )
        return self._call_proxy(send)

    def get_return_date(
        self, court_id: str, req_return_date: datetime, all_vars_obj: dict
    ) -> ApiResponse:
        all_vars_obj["return_date"] = req_return_date.isoformat()
        send = lambda: self.proxy_client.post(
            self.full_url(f"scheduling/courts/{court_id}/return_date"),
            json=all_vars_obj,
        )
        return self._call_proxy(send)

    def reserve_court_date(
        self,
        court_id: str,
        doc_id: str,
        range_after: Union[datetime, str] = None,
        range_before: Union[datetime, str] = None,
        estimated_duration=None,
    ) -> ApiResponse:
        if range_after is not None and not isinstance(range_after, str):
            range_after_str = range_after.isoformat()
        else:
            range_after_str = range_after or ""
        logging.debug(f"after: {range_after}")
        if range_before is not None and not isinstance(range_before, str):
            range_before_str = range_before.isoformat()
        else:
            range_before_str = range_before or ""
        logging.debug(f"before: {range_before}")
        if estimated_duration is not None:
            estimated_duration = int(estimated_duration) * 60 * 60
        send = lambda: self.proxy_client.post(
            self.full_url(f"scheduling/courts/{court_id}/reserve_date"),
            json={
                "doc_id": doc_id,
                "estimated_duration": estimated_duration,
                "range_after": range_after,
                "range_before": range_before,
            },
        )
        return self._call_proxy(send)

    def get_cases_raw(
        self,
        court_id: str,
        *,
        person_name: dict = None,
        business_name: str = None,
        docket_number: str = None,
    ) -> ApiResponse:
        """
        Finds existing cases at a particular court. Only one of person_name, business_name, or docket_number should be
        provided at a time.
        Params:
          court_id (str)
          person_name (dict)
          business_name (str)
          docket_number (str)
        """
        send = lambda: self.proxy_client.get(
            self.full_url(f"cases/courts/{court_id}/cases"),
            params={
                "first_name": (
                    person_name.get("first") if person_name is not None else None
                ),
                "middle_name": (
                    person_name.get("middle") if person_name is not None else None
                ),
                "last_name": (
                    person_name.get("last") if person_name is not None else None
                ),
                "business_name": business_name,
                "docket_number": docket_number,
            },
        )
        return self._call_proxy(send)

    def get_case(self, court_id: str, case_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"cases/courts/{court_id}/cases/{case_id}")
        )
        return self._call_proxy(send)

    def get_document(self, court_id: str, case_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"cases/courts/{court_id}/cases/{case_id}/documents")
        )
        return self._call_proxy(send)

    def get_service_attach_case_list(
        self, court_id: str, service_contact_id: str
    ) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"cases/courts/{court_id}/service-contacts/{service_contact_id}/cases"
            )
        )
        return self._call_proxy(send)

    def get_service_information(
        self, court_id: str, case_tracking_id: str
    ) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"cases/courts/{court_id}/cases/{case_tracking_id}/service-information"
            )
        )
        return self._call_proxy(send)

    def get_service_information_history(
        self, court_id: str, case_tracking_id: str
    ) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"cases/courts/{court_id}/cases/{case_tracking_id}/service-information-history"
            )
        )
        return self._call_proxy(send)

    def search_case_categories(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/categories"), params=params
        )
        return self._call_proxy(send)

    def retrieve_case_categories(
        self, retrieve_name: Optional[str] = None
    ) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/categories/{retrieve_name}")
        )
        return self._call_proxy(send)

    def get_case_categories(
        self, court_id: str, fileable_only: bool = False, timing: Optional[str] = None
    ) -> ApiResponse:
        params = {"fileable_only": fileable_only, "timing": timing}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/categories"), params=params
        )
        return self._call_proxy(send)

    def get_filer_types(self, court_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/filer_types")
        )
        return self._call_proxy(send)

    def search_case_types(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/case_types"), params=params
        )
        return self._call_proxy(send)

    def retrieve_case_types(self, retrieve_name: Optional[str] = None) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/case_types/{retrieve_name}")
        )
        return self._call_proxy(send)

    def get_case_types(
        self, court_id: str, case_category: str, timing: str = None
    ) -> ApiResponse:
        params = {"category_id": case_category, "timing": timing}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/case_types"), params=params
        )
        return self._call_proxy(send)

    def get_case_type(self, court_id: str, case_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/case_types/{case_type}")
        )
        return self._call_proxy(send)

    def get_case_subtypes(self, court_id: str, case_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/case_types/{case_type}/case_subtypes"
            )
        )
        return self._call_proxy(send)

    def search_filing_types(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/filing_types"), params=params
        )
        return self._call_proxy(send)

    def retrieve_filing_types(self, retrieve_name: Optional[str] = None) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/filing_types/{retrieve_name}")
        )
        return self._call_proxy(send)

    def get_filing_types(
        self, court_id: str, case_category: str, case_type: str, initial: bool
    ) -> ApiResponse:
        params = {
            "category_id": case_category,
            "type_id": case_type,
            "initial": str(initial),
        }
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/filing_types"), params=params
        )
        return self._call_proxy(send)

    def get_service_type_codes(self, court_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/service_types")
        )
        return self._call_proxy(send)

    def search_party_types(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/party_types"), params=params
        )
        return self._call_proxy(send)

    def retrieve_party_types(self, retrieve_name: Optional[str] = None) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/party_types/{retrieve_name}")
        )
        return self._call_proxy(send)

    def get_party_types(
        self, court_id: str, case_type_id: Optional[str]
    ) -> ApiResponse:
        if case_type_id:
            send = lambda: self.proxy_client.get(
                self.full_url(
                    f"codes/courts/{court_id}/case_types/{case_type_id}/party_types"
                )
            )
        else:
            send = lambda: self.proxy_client.get(
                self.full_url(f"codes/courts/{court_id}/party_types")
            )
        return self._call_proxy(send)

    def get_document_types(self, court_id: str, filing_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/filing_types/{filing_type}/document_types"
            )
        )
        return self._call_proxy(send)

    def get_motion_types(self, court_id: str, filing_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/filing_types/{filing_type}/motion_types"
            )
        )
        return self._call_proxy(send)

    def get_filing_components(self, court_id: str, filing_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/filing_types/{filing_type}/filing_components"
            )
        )
        return self._call_proxy(send)

    def search_optional_services(
        self, search_term: Optional[str] = None
    ) -> ApiResponse:
        params = {"search": search_term}
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/optional_services"), params=params
        )
        return self._call_proxy(send)

    def retrieve_optional_services(
        self, retrieve_name: Optional[str] = None
    ) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/optional_services/{retrieve_name}")
        )
        return self._call_proxy(send)

    def get_optional_services(self, court_id: str, filing_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/filing_types/{filing_type}/optional_services"
            )
        )
        return self._call_proxy(send)

    def get_cross_references(self, court_id: str, case_type: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/casetypes/{case_type}/cross_references"
            )
        )
        return self._call_proxy(send)

    def get_damage_amounts(
        self, court_id: str, case_category: Optional[str] = None
    ) -> ApiResponse:
        params = {"category_id": case_category}
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/damage_amounts",
            ),
            params=params,
        )
        return self._call_proxy(send)

    def get_procedure_or_remedies(
        self, court_id: str, case_category: Optional[str] = None
    ) -> ApiResponse:
        params = {"category_id": case_category}
        send = lambda: self.proxy_client.get(
            self.full_url(
                f"codes/courts/{court_id}/procedure_or_remedies",
            ),
            params=params,
        )
        return self._call_proxy(send)

    def get_datafield(self, court_id: str, field_name: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/datafields/{field_name}")
        )
        return self._call_proxy(send)

    def get_disclaimers(self, court_id: str) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"codes/courts/{court_id}/disclaimer_requirements")
        )
        return self._call_proxy(send)

    def get_server_id(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"api_user_settings/serverid")
        )
        return self._call_proxy(send)

    def get_server_name(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(self.full_url(f"api_user_settings/name"))
        return self._call_proxy(send)

    def get_logs(self) -> ApiResponse:
        send = lambda: self.proxy_client.get(
            self.full_url(f"api_user_settings/logs"),
            headers={
                "Accept": "application/octet-stream",
                "X-API-KEY": self.proxy_client.headers["X-API-KEY"],
            },
        )
        # This resp has the logs as the error message: split by line and put in data
        resp = self._call_proxy(send)
        if resp.is_ok() and resp.error_msg and resp.error_msg != "":
            resp.data = resp.error_msg[1:].split("|\n|")
            resp.error_msg = None
        return resp
