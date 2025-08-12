#!/usr/bin/env python3

"""
The base python client used to communicate with the E-file proxy server.

Doesn't include anything from docassemble, and can be used without having it installed.
"""

import re
import logging
import requests
from logging import LoggerAdapter
from requests import Request, PreparedRequest
from uuid import UUID, uuid4
from requests import Response
from datetime import datetime
from typing import Optional, Union, List, Dict
import http.client as http_client
from copy import deepcopy

__all__ = ["LoggerWithContext", "ApiResponse", "EfspConnection"]

SESSION_ID_HEADER = "efsp-session-id"
CORR_ID_HEADER = "efsp-correlation-id"  # TODO(brycew): Figure out how to add
REQUEST_ID_HEADER = "efsp-request-id"


class LoggerWithContext(LoggerAdapter):
    """Acts like the `merge_extra` feature from LoggerAdapter (python 3.13) is always on.

    See https://github.com/python/cpython/pull/107292/files.
    """

    def __init__(self, logger, extra):
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        if "extra" in kwargs:
            kwargs["extra"] = {**self.extra, **kwargs["extra"]}
        else:
            kwargs["extra"] = self.extra
        return msg, kwargs


class ApiResponse(object):
    def __init__(
        self,
        response_code: int,
        error_msg: Optional[str],
        data,
        *,
        session_id: Optional[str] = None,
        req_id: Optional[str] = None,
    ):
        self.response_code = response_code
        self.error_msg = error_msg
        self.data = data
        self.session_id = session_id
        self.req_id = req_id

    def __str__(self):
        if self.error_msg:
            err_str = f"error_msg: {self.error_msg}, "
        else:
            err_str = ""
        msg = f"response_code: {self.response_code}, {err_str}data: {self.data}"
        if self.get_session_id():
            msg += f", session_id: {self.get_session_id()}"
        if self.get_req_id():
            msg += f", req_id: {self.get_req_id()}"
        return msg

    def __repr__(self):
        return str(self)

    def is_ok(self):
        return self.response_code in [200, 201, 202, 203, 204, 205]

    def get_session_id(self):
        if not hasattr(self, "session_id"):
            self.session_id = None
        return self.session_id

    def get_req_id(self):
        if not hasattr(self, "req_id"):
            self.req_id = None
        return self.req_id


def _user_visible_resp(resp: Union[Response, str, None]) -> ApiResponse:
    """This function takes the essentials of a response and puts in into
    a simple object.
    """
    if resp is None:
        return ApiResponse(501, "Not yet implemented (on both sides)", None)
    # Something went wrong with us / some error in requests
    if isinstance(resp, str):
        return ApiResponse(-1, resp, None)
    session_id = resp.request.headers.get(SESSION_ID_HEADER)
    req_id = resp.request.headers.get(REQUEST_ID_HEADER)
    try:
        data = resp.json()
        return ApiResponse(
            resp.status_code, None, data, session_id=session_id, req_id=req_id
        )
    except:
        return ApiResponse(
            resp.status_code, resp.text, None, session_id=session_id, req_id=req_id
        )


class EfspConnection:
    """A python client that communicates with the E-file proxy server."""

    def __init__(
        self, *, url: str, api_key: str, default_jurisdiction: str = None, logger=None
    ):
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
        # Keep one uuid for the whole of this class's life, i.e. the session
        self.session_id = str(uuid4())
        if logger is None:
            logger = logging.getLogger()
        self.logger = LoggerWithContext(logger, {"session_id": self.session_id})
        self.logger.info(f"setting default jurisdiction to {default_jurisdiction}")
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

    # Should only be called from _send.
    def _call_proxy(self, req: PreparedRequest) -> ApiResponse:
        try:
            resp = self.proxy_client.send(req)
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

    def _send(self, to_send: Request, *, req_id: Optional[UUID] = None) -> ApiResponse:
        """Handle sending the request / structuring the response"""
        if req_id is None:
            req_id = uuid4()
        to_send.headers["efsp-request-id"] = str(req_id)
        to_send.headers["efsp-session-id"] = self.get_session_id()
        self.get_logger().info(
            f"Calling {to_send.method} on {to_send.url}", extra={"req-id": str(req_id)}
        )
        return self._call_proxy(self.proxy_client.prepare_request(to_send))

    def get_session_id(self):
        if not hasattr(self, "session_id"):
            # Migration from older interviews, to start passing observability headers
            self.session_id = str(uuid4())
        return self.session_id

    def get_logger(self):
        if not hasattr(self, "logger"):
            self.logger = LoggerWithContext(
                logging.getLogger(), {"session_id": self.get_session_id()}
            )
        return self.logger

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
        req_id = uuid4()

        if jurisdiction is None:
            jurisdiction = self.default_jurisdiction
        self.get_logger().info(
            f"authenticating with jurisdiction: {jurisdiction}",
            extra={"req-id": str(req_id)},
        )
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
            resp = self.proxy_client.post(
                self.base_url + "authenticate",
                json=auth_obj,
                headers={"efsp-request-id": str(req_id)},
            )
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
        req_id = uuid4()
        self.get_logger().info("Attempting to register user", extra={"req-id": req_id})
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

        req = Request("POST", self.full_url("adminusers/users"), json=reg_obj)
        return self._send(req, req_id=req_id)

    def get_password_rules(self) -> ApiResponse:
        """
        Password rules are stored in the global court, id 0.

        TODO: They're in other courts too, including 1. Could they ever be different?
        """
        req = Request("GET", self.full_url("codes/courts/0/datafields/GlobalPassword"))
        return self._send(req)

    def is_valid_password(self, password: str) -> Optional[bool]:
        results = self.get_password_rules()
        if results.data:
            password_regex = results.data.get("regularexpression", ".*")
        else:
            self.get_logger().warning(f"No password rules found: {results}")
            password_regex = ".*"

        try:
            return bool(re.match(password_regex, password))
        except:
            return None

    # Managing Firm Users

    def get_user_list(self) -> ApiResponse:
        req = Request("GET", self.full_url("adminusers/users"))
        return self._send(req)

    def get_users(self) -> ApiResponse:
        return self.get_user_list()

    def get_user(self, id: str = None) -> ApiResponse:
        if id is None:
            url = self.full_url("adminusers/user")
        else:
            url = self.full_url(f"adminusers/users/{id}")
        req = Request("GET", url)
        return self._send(req)

    def get_user_roles(self, id: str) -> ApiResponse:
        req = Request("GET", self.full_url(f"adminusers/users/{id}/roles"))
        return self._send(req)

    def add_user_roles(self, id: str, roles: List[dict]) -> ApiResponse:
        req = Request("POST", self.full_url(f"adminusers/users/{id}/roles"), json=roles)
        return self._send(req)

    def remove_user_roles(self, id: str, roles: List[dict]) -> ApiResponse:
        url = self.full_url(f"adminusers/users/{id}/roles")
        req = Request("DELETE", url, json=roles)
        return self._send(req)

    def change_password(self, id: str, email: str, new_password: str) -> ApiResponse:
        url = self.full_url(f"adminusers/users/{id}/password")
        req = Request("POST", url, json={"email": email, "newPassword": new_password})
        return self._send(req)

    def self_change_password(self, current_pwd: str, new_pwd: str) -> ApiResponse:
        url = self.full_url("adminusers/user/password")
        req = Request(
            "POST", url, json={"currentPassword": current_pwd, "newPassword": new_pwd}
        )
        return self._send(req)

    def self_resend_activation_email(self, email: str) -> ApiResponse:
        url = self.full_url("adminusers/user/resend-activation-email")
        req = Request("POST", url, data=email)
        return self._send(req)

    def resend_activation_email(self, id: str) -> ApiResponse:
        url = self.full_url(f"adminusers/users/{id}/resend-activation-email")
        req = Request("POST", url)
        return self._send(req)

    def update_notification_preferences(
        self, notif_preferences: List[dict]
    ) -> ApiResponse:
        url = self.full_url(f"adminusers/user/notification-preferences")
        req = Request("PATCH", url, json=notif_preferences)
        return self._send(req)

    def get_notification_preferences(self) -> ApiResponse:
        req = Request("GET", self.full_url("adminusers/user/notification-preferences"))
        return self._send(req)

    def get_notification_options(self) -> ApiResponse:
        """AKA NotificationPreferencesList"""
        req = Request("GET", self.full_url("adminusers/notification-options"))
        return self._send(req)

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
        req = Request("PATCH", self.full_url("adminusers/user"), json=updated_user)
        return self._send(req)

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
        req = Request(
            "PATCH", self.full_url(f"adminusers/users/{id}"), json=updated_user
        )
        return self._send(req)

    def remove_user(self, id: str) -> ApiResponse:
        req = Request("DELETE", self.full_url(f"adminusers/users/{id}"))
        return self._send(req)

    # TODO(brycew): not tested
    def reset_user_password(self, email: str) -> ApiResponse:
        req = Request(
            "POST", self.full_url("adminusers/user/password/reset"), data=email
        )
        return self._send(req)

    ### Managing a Firm
    def get_firm(self) -> ApiResponse:
        """Gets info about the "firm" for an associated user. If a user is a pro-se, this
        contains their address information.
        """
        req = Request("GET", self.full_url("firmattorneyservice/firm"))
        return self._send(req)

    def update_firm(self, firm: dict) -> ApiResponse:
        """
        firm should have the below keys:
        * firstName, middleName, lastName if it's a person
        * firmName if it's a business
        * address (a dict), with keys addressLine1 addressLine2, city, state, zipCode, country
        * phoneNumber
        * email
        """
        req = Request("PATCH", self.full_url("firmattorneyservice/firm"), json=firm)
        return self._send(req)

    ### Managing Attorneys
    def get_attorney_list(self) -> ApiResponse:
        req = Request("GET", self.full_url("firmattorneyservice/attorneys"))
        return self._send(req)

    def get_attorney(self, attorney_id):
        url = self.full_url(f"firmattorneyservice/attorneys/{attorney_id}")
        return self._send(Request("GET", url))

    def update_attorney(
        self,
        attorney_id,
        bar_number: str = None,
        first_name: str = None,
        middle_name: str = None,
        last_name: str = None,
    ) -> ApiResponse:
        req = Request(
            "PATCH",
            self.full_url(f"firmattorneyservice/attorneys/{attorney_id}"),
            json={
                "barNumber": bar_number,
                "firstName": first_name,
                "middleName": middle_name,
                "lastName": last_name,
            },
        )
        return self._send(req)

    def create_attorney(
        self,
        bar_number: str,
        first_name: str,
        middle_name: str = None,
        last_name: str = None,
    ) -> ApiResponse:
        req = Request(
            "POST",
            self.full_url("firmattorneyservice/attorneys"),
            json={
                "barNumber": bar_number,
                "firstName": first_name,
                "middleName": middle_name,
                "lastName": last_name,
            },
        )
        return self._send(req)

    def remove_attorney(self, attorney_id) -> ApiResponse:
        url = self.full_url(f"firmattorneyservice/attorneys/{attorney_id}")
        return self._send(Request("DELETE", url))

    ### Managing Payment Accounts
    def get_payment_account_type_list(self) -> ApiResponse:
        req = Request("GET", self.full_url("payments/types"))
        return self._send(req)

    def get_payment_account_list(self, court_id: Optional[str] = None) -> ApiResponse:
        if not court_id:
            params = None
        else:
            params = {"court_id": court_id}
        req = Request("GET", self.full_url("payments/payment-accounts"), params=params)
        return self._send(req)

    def get_payment_account(self, payment_account_id: str) -> ApiResponse:
        url = self.full_url(f"payments/payment-accounts/{payment_account_id}")
        return self._send(Request("GET", url))

    def update_payment_account(
        self, payment_account_id: str, account_name: str = None, active: bool = True
    ) -> ApiResponse:
        url = self.full_url(f"payments/payment-accounts/{payment_account_id}")
        req = Request(
            "PATCH", url, json={"account_name": account_name, "active": active}
        )
        return self._send(req)

    def remove_payment_account(self, payment_account_id: str) -> ApiResponse:
        url = self.full_url(f"payments/payment-accounts/{payment_account_id}")
        return self._send(Request("DELETE", url))

    # Both types of accounts
    def create_waiver_account(self, account_name: str, is_global: bool) -> ApiResponse:
        url = self.full_url(
            "payments/global-accounts" if is_global else "payments/payment-accounts"
        )
        return self._send(Request("POST", url, data=account_name))

    # Global Payment Accounts
    def get_global_payment_account_list(self) -> ApiResponse:
        return self._send(Request("GET", self.full_url("payments/global-accounts")))

    def get_global_payment_account(self, global_payment_account_id: str) -> ApiResponse:
        url = self.full_url(f"payments/global-accounts/{global_payment_account_id}")
        return self._send(Request("GET", url))

    def update_global_payment_account(
        self,
        global_payment_account_id: str,
        account_name: str = None,
        active: bool = True,
    ) -> ApiResponse:
        url = self.full_url(f"payments/global-accounts/{global_payment_account_id}")
        req = Request(
            "PATCH", url, json={"account_name": account_name, "active": active}
        )
        return self._send(req)

    def remove_global_payment_account(
        self, global_payment_account_id: str
    ) -> ApiResponse:
        url = self.full_url(f"payments/global-accounts/{global_payment_account_id}")
        return self._send(Request("DELETE", url))

    ### Managing Service Contacts
    # Service contacts are part of the `firm` hierarchy
    def get_service_contact_list(self) -> ApiResponse:
        req = Request("GET", self.full_url(f"firmattorneyservice/service-contacts"))
        return self._send(req)

    def get_service_contact(self, service_contact_id) -> ApiResponse:
        url = self.full_url(
            f"firmattorneyservice/service-contacts/{service_contact_id}"
        )
        return self._send(Request("GET", url))

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
        url = self.full_url(
            f"firmattorneyservice/service-contacts/{service_contact_id}"
        )
        return self._send(Request("PATCH", url, json=service_contact_dict))

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
        url = self.full_url("firmattorneyservice/service-contacts")
        return self._send(Request("POST", url, json=service_contact_dict))

    def remove_service_contact(self, service_contact_id) -> ApiResponse:
        url = self.full_url(
            f"firmattorneyservice/service-contacts/{service_contact_id}"
        )
        return self._send(Request("DELETE", url))

    def get_public_service_contacts(
        self,
        first_name: str = None,
        middle_name: str = None,
        last_name: str = None,
        email: str = None,
    ) -> ApiResponse:
        req = Request(
            "GET",
            self.full_url(f"firmattorneyservice/service-contacts/public"),
            json={
                "firstName": first_name,
                "middleName": middle_name,
                "lastName": last_name,
                "email": email,
            },
        )
        return self._send(req)

    # Using Service Contacts
    def attach_service_contact(
        self, service_contact_id: str, case_id: str, case_party_id: str = None
    ) -> ApiResponse:
        req = Request(
            "PUT",
            self.full_url(
                f"firmattorneyservice/service-contacts/{service_contact_id}/cases"
            ),
            json={"caseId": case_id, "casepartyId": case_party_id},
        )
        return self._send(req)

    def detach_service_contact(
        self, service_contact_id: str, case_id: str, case_party_id: str = None
    ) -> ApiResponse:
        url = self.full_url(
            f"firmattorneyservice/service-contacts/{service_contact_id}/cases/{case_id}"
        )
        req = Request("DELETE", url, params={"case_party_id": case_party_id})
        return self._send(req)

    def get_attached_cases(self, court_id: str, service_contact_id: str) -> ApiResponse:
        url = self.full_url(
            f"cases/courts/{court_id}/service-contacts/{service_contact_id}/cases"
        )
        return self._send(Request("GET", url))

    def get_public_list(self):
        url = self.full_url("firmattorneyservice/service-contacts/public")
        return self._send(Request("GET", url))

    def get_courts(
        self, fileable_only: bool = False, with_names: bool = False
    ) -> ApiResponse:
        """Gets the list of courts."""
        params = {"fileable_only": fileable_only, "with_names": with_names}
        req = Request("GET", self.full_url("codes/courts"), params=params)
        return self._send(req)

    def get_court(self, court_id: str) -> ApiResponse:
        """Gets codes for a specific court"""
        req = Request("GET", self.full_url(f"codes/courts/{court_id}/codes"))
        return self._send(req)

    def get_court_list(self) -> ApiResponse:
        """Gets a list of all of the courts that you can file into. Slightly more limited than
        [get_courts](#get_courts)"""
        req = Request("GET", self.full_url(f"filingreview/courts"))
        return self._send(req)

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
        url = self.full_url(f"filingreview/courts/{court_id}/filings")
        req = Request("GET", url, params=params)
        return self._send(req)

    def get_filing(self, court_id: str, filing_id: str) -> ApiResponse:
        url = self.full_url(f"filingreview/courts/{court_id}/filings/{filing_id}")
        return self._send(Request("GET", url))

    def get_policy(self, court_id: str) -> ApiResponse:
        req = Request("GET", self.full_url(f"filingreview/courts/{court_id}/policy"))
        return self._send(req)

    def get_filing_status(self, court_id: str, filing_id: str) -> ApiResponse:
        url = self.full_url(
            f"filingreview/courts/{court_id}/filings/{filing_id}/status"
        )
        return self._send(Request("GET", url))

    def cancel_filing_status(self, court_id: str, filing_id: str) -> ApiResponse:
        url = self.full_url(f"filingreview/courts/{court_id}/filings/{filing_id}")
        return self._send(Request("DELETE", url))

    def check_filing(self, court_id: str, all_vars: dict) -> ApiResponse:
        url = self.full_url(f"filingreview/courts/{court_id}/filing/check")
        req = Request("GET", url, json=all_vars)
        return self._send(req)

    def file_for_review(self, court_id: str, all_vars: dict) -> ApiResponse:
        url = self.full_url(f"filingreview/courts/{court_id}/filings")
        req = Request("POST", url, json=all_vars)
        return self._send(req)

    def get_service_types(self, court_id: str, all_vars: dict = None) -> ApiResponse:
        """Checks the court info: if it has conditional service types, call a special API with all filing info so far to get service types"""
        court_info = self.get_court(court_id)
        if court_info.data.get("hasconditionalservicetypes") and all_vars:
            url = self.full_url(f"filingreview/courts/{court_id}/filing/servicetypes")
            req = Request("GET", url, json=all_vars)
            return self._send(req)
        else:
            return self.get_service_type_codes(court_id)

    def calculate_filing_fees(self, court_id: str, all_vars: dict) -> ApiResponse:
        url = self.full_url(f"filingreview/courts/{court_id}/filing/fees")
        req = Request("POST", url, json=all_vars)
        return self._send(req)

    def get_return_date(
        self, court_id: str, req_return_date: datetime, all_vars_obj: dict
    ) -> ApiResponse:
        all_vars_obj["return_date"] = req_return_date.isoformat()
        url = self.full_url(f"scheduling/courts/{court_id}/return_date")
        req = Request("POST", url, json=all_vars_obj)
        return self._send(req)

    def reserve_court_date(
        self,
        court_id: str,
        doc_id: str,
        range_after: Union[datetime, str] = None,
        range_before: Union[datetime, str] = None,
        estimated_duration=None,
    ) -> ApiResponse:
        req_id = uuid4()
        if range_after is not None and not isinstance(range_after, str):
            range_after_str = range_after.isoformat()
        else:
            range_after_str = range_after or ""
        self.get_logger().debug(f"after: {range_after}", extra={"req-id": req_id})
        if range_before is not None and not isinstance(range_before, str):
            range_before_str = range_before.isoformat()
        else:
            range_before_str = range_before or ""
        self.get_logger().debug(f"before: {range_before}", extra={"req-id": req_id})
        if estimated_duration is not None:
            estimated_duration = int(estimated_duration) * 60 * 60
        req = Request(
            "POST",
            self.full_url(f"scheduling/courts/{court_id}/reserve_date"),
            json={
                "doc_id": doc_id,
                "estimated_duration": estimated_duration,
                "range_after": range_after,
                "range_before": range_before,
            },
        )
        return self._send(req, req_id=req_id)

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
        req = Request(
            "GET",
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
        return self._send(req)

    def get_case(self, court_id: str, case_id: str) -> ApiResponse:
        req = Request("GET", self.full_url(f"cases/courts/{court_id}/cases/{case_id}"))
        return self._send(req)

    def get_document(self, court_id: str, case_id: str) -> ApiResponse:
        url = self.full_url(f"cases/courts/{court_id}/cases/{case_id}/documents")
        return self._send(Request("GET", url))

    def get_service_attach_case_list(
        self, court_id: str, service_contact_id: str
    ) -> ApiResponse:
        url = self.full_url(
            f"cases/courts/{court_id}/service-contacts/{service_contact_id}/cases"
        )
        return self._send(Request("GET", url))

    def get_service_information(
        self, court_id: str, case_tracking_id: str
    ) -> ApiResponse:
        url = self.full_url(
            f"cases/courts/{court_id}/cases/{case_tracking_id}/service-information"
        )
        return self._send(Request("GET", url))

    def get_service_information_history(
        self, court_id: str, case_tracking_id: str
    ) -> ApiResponse:
        url = self.full_url(
            f"cases/courts/{court_id}/cases/{case_tracking_id}/service-information-history"
        )
        return self._send(Request("GET", url))

    def search_case_categories(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        url = self.full_url(f"codes/categories")
        return self._send(Request("GET", url, params=params))

    def retrieve_case_categories(
        self, retrieve_name: Optional[str] = None
    ) -> ApiResponse:
        url = self.full_url(f"codes/categories/{retrieve_name}")
        return self._send(Request("GET", url))

    def get_case_categories(
        self, court_id: str, fileable_only: bool = False, timing: Optional[str] = None
    ) -> ApiResponse:
        params = {"fileable_only": fileable_only, "timing": timing}
        url = self.full_url(f"codes/courts/{court_id}/categories")
        return self._send(Request("GET", url, params=params))

    def get_filer_types(self, court_id: str) -> ApiResponse:
        url = self.full_url(f"codes/courts/{court_id}/filer_types")
        return self._send(Request("GET", url))

    def search_case_types(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        url = self.full_url(f"codes/case_types")
        return self._send(Request("GET", url, params=params))

    def retrieve_case_types(self, retrieve_name: Optional[str] = None) -> ApiResponse:
        url = self.full_url(f"codes/case_types/{retrieve_name}")
        return self._send(Request("GET", url))

    def get_case_types(
        self, court_id: str, case_category: str, timing: str = None
    ) -> ApiResponse:
        params = {"category_id": case_category, "timing": timing}
        url = self.full_url(f"codes/courts/{court_id}/case_types")
        return self._send(Request("GET", url, params=params))

    def get_case_type(self, court_id: str, case_type: str) -> ApiResponse:
        url = self.full_url(f"codes/courts/{court_id}/case_types/{case_type}")
        return self._send(Request("GET", url))

    def get_case_subtypes(self, court_id: str, case_type: str) -> ApiResponse:
        url = self.full_url(
            f"codes/courts/{court_id}/case_types/{case_type}/case_subtypes"
        )
        return self._send(Request("GET", url))

    def search_filing_types(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        url = self.full_url(f"codes/filing_types")
        return self._send(Request("GET", url, params=params))

    def retrieve_filing_types(self, retrieve_name: Optional[str] = None) -> ApiResponse:
        url = self.full_url(f"codes/filing_types/{retrieve_name}")
        return self._send(Request("GET", url))

    def get_filing_types(
        self, court_id: str, case_category: str, case_type: str, initial: bool
    ) -> ApiResponse:
        params = {
            "category_id": case_category,
            "type_id": case_type,
            "initial": str(initial),
        }
        url = self.full_url(f"codes/courts/{court_id}/filing_types")
        return self._send(Request("GET", url, params=params))

    def get_service_type_codes(self, court_id: str) -> ApiResponse:
        url = self.full_url(f"codes/courts/{court_id}/service_types")
        return self._send(Request("GET", url))

    def search_party_types(self, search_term: Optional[str] = None) -> ApiResponse:
        params = {"search": search_term}
        url = self.full_url(f"codes/party_types")
        return self._send(Request("GET", url, params=params))

    def retrieve_party_types(self, retrieve_name: Optional[str] = None) -> ApiResponse:
        url = self.full_url(f"codes/party_types/{retrieve_name}")
        return self._send(Request("GET", url))

    def get_party_types(
        self, court_id: str, case_type_id: Optional[str]
    ) -> ApiResponse:
        if case_type_id:
            url = self.full_url(
                f"codes/courts/{court_id}/case_types/{case_type_id}/party_types"
            )
        else:
            url = self.full_url(f"codes/courts/{court_id}/party_types")
        return self._send(Request("GET", url))

    def get_document_types(self, court_id: str, filing_type: str) -> ApiResponse:
        url = self.full_url(
            f"codes/courts/{court_id}/filing_types/{filing_type}/document_types"
        )
        return self._send(Request("GET", url))

    def get_motion_types(self, court_id: str, filing_type: str) -> ApiResponse:
        url = self.full_url(
            f"codes/courts/{court_id}/filing_types/{filing_type}/motion_types"
        )
        return self._send(Request("GET", url))

    def get_filing_components(self, court_id: str, filing_type: str) -> ApiResponse:
        url = self.full_url(
            f"codes/courts/{court_id}/filing_types/{filing_type}/filing_components"
        )
        return self._send(Request("GET", url))

    def search_optional_services(
        self, search_term: Optional[str] = None
    ) -> ApiResponse:
        params = {"search": search_term}
        url = self.full_url(f"codes/optional_services")
        return self._send(Request("GET", url, params=params))

    def retrieve_optional_services(
        self, retrieve_name: Optional[str] = None
    ) -> ApiResponse:
        url = self.full_url(f"codes/optional_services/{retrieve_name}")
        return self._send(Request("GET", url))

    def get_optional_services(self, court_id: str, filing_type: str) -> ApiResponse:
        url = self.full_url(
            f"codes/courts/{court_id}/filing_types/{filing_type}/optional_services"
        )
        return self._send(Request("GET", url))

    def get_cross_references(self, court_id: str, case_type: str) -> ApiResponse:
        url = self.full_url(
            f"codes/courts/{court_id}/case_types/{case_type}/cross_references"
        )
        return self._send(Request("GET", url))

    def get_damage_amounts(
        self, court_id: str, case_category: Optional[str] = None
    ) -> ApiResponse:
        params = {"category_id": case_category}
        url = self.full_url(f"codes/courts/{court_id}/damage_amounts")
        return self._send(Request("GET", url, params=params))

    def get_procedure_or_remedies(
        self, court_id: str, case_category: Optional[str] = None
    ) -> ApiResponse:
        params = {"category_id": case_category}
        url = self.full_url(
            f"codes/courts/{court_id}/procedure_or_remedies",
        )
        req = Request("GET", url, params=params)
        return self._send(req)

    def get_datafield(self, court_id: str, field_name: str) -> ApiResponse:
        url = self.full_url(f"codes/courts/{court_id}/datafields/{field_name}")
        return self._send(Request("GET", url))

    def get_disclaimers(self, court_id: str) -> ApiResponse:
        url = self.full_url(f"codes/courts/{court_id}/disclaimer_requirements")
        return self._send(Request("GET", url))

    def get_server_id(self) -> ApiResponse:
        url = self.full_url(f"api_user_settings/serverid")
        return self._send(Request("GET", url))

    def get_server_name(self) -> ApiResponse:
        return self._send(Request("GET", self.full_url(f"api_user_settings/name")))

    def get_logs(self) -> ApiResponse:
        url = self.full_url(f"api_user_settings/logs")
        req = Request("GET", url, headers={"Accept": "application/octet-stream"})
        # This resp has the logs as the error message: split by line and put in data
        resp = self._send(req)
        if resp.is_ok() and resp.error_msg and resp.error_msg != "":
            resp.data = resp.error_msg[1:].split("|\n|")
            resp.error_msg = None
        return resp
