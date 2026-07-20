#!/usr/bin/env python3
import logging
import re
import pycountry
from typing import Dict, Union

import requests
from logging import LoggerAdapter
from requests import Response, PreparedRequest
from docassemble.base.functions import all_variables, get_config
from docassemble.base.util import (
    DAObject,
    log,
    Person,
    Individual,
    DAStore,
    DAEmpty,
    DADateTime,
    as_datetime,
    reconsider,
    current_context,
)
from docassemble.AssemblyLine.al_document import ALDocumentBundle
from docassemble.AssemblyLine.al_general import ALIndividual
from .py_efsp_client import (
    ApiResponse,
    LoggerWithContext,
    EfspConnection,
    _user_visible_resp,
)

__all__ = ["ApiResponse", "ProxyConnection", "state_name_to_code"]


class DALogger(LoggerAdapter):
    def __init__(self, logger):
        super().__init__(logger)

    def log(self, level, msg, *args, **kwargs):
        """
        Delegate a log call to Docassemble's `log` function, after adding
        contextual information from this adapter instance.
        """
        kwargs
        if not self.isEnabledFor(level):
            return

        msg = re.sub(r"\n", " ", msg)
        log(f"[{args}, {kwargs}] {msg}")


def state_name_to_code(state_name: str) -> str:
    try:
        return pycountry.subdivisions.lookup(state_name).code.split("-")[-1]
    except LookupError as ex:
        return state_name


def _give_data_url(bundle: ALDocumentBundle, key: str = "final") -> None:
    """Prepares the filing documents by setting a semi-permanent enabled and a data url
    The document bundle can either consist of documents or other document bundles. But each top element will
    sent to Tyler as a separate filing document, and needs to have the necessary attributes set (tyler_filing_id, etc)
    """
    if bundle is None:
        return
    for doc in bundle:
        doc.proxy_enabled = doc.is_enabled()
        if doc.proxy_enabled:
            # TODO(brycew): another hack: forcing the main doc to be it when filing components don't allow attachments
            if not (
                hasattr(doc, "tyler_merge_attachments") and doc.tyler_merge_attachments
            ) and isinstance(doc, ALDocumentBundle):
                # TODO(brycew): hacky, but should work for now. Make getting all enabled_docs an actual API on ALDocuments
                attachments = doc.enabled_documents()
                for attachment in attachments:
                    attachment.proxy_enabled = attachment.is_enabled()
                    attachment_pdf = attachment.as_pdf(key)
                    attachment.data_url = attachment_pdf.url_for(
                        external=True, temporary=True
                    )
                    if attachment.data_url.startswith("http://localhost/"):
                        attachment.data_url = attachment.data_url.replace(
                            "http://localhost/",
                            "http://" + get_config("external hostname") + "/",
                        )
                    attachment.page_count = attachment_pdf.num_pages()
            else:
                doc_pdf = doc.as_pdf(key)
                doc.data_url = doc_pdf.url_for(external=True, temporary=True)
                if doc.data_url.startswith("http://localhost/"):
                    doc.data_url = doc.data_url.replace(
                        "http://localhost/",
                        "http://" + get_config("external hostname") + "/",
                    )
                doc.page_count = doc_pdf.num_pages()


def _remove_all_da_emptys(json_val):
    if isinstance(json_val, DAEmpty):
        return None
    if isinstance(json_val, list):
        return [_remove_all_da_emptys(v) for v in json_val]
    if isinstance(json_val, dict):
        return {k: _remove_all_da_emptys(v) for k, v in json_val.items()}
    return json_val


def _get_all_vars(bundle: ALDocumentBundle, key: str = "final") -> Dict:
    """Strips out some extra big variables that we don't need to serialize and send across the network"""
    _give_data_url(bundle, key=key)
    all_vars_dict = all_variables()

    to_send_dict = {}
    # TODO: mark any of the below as required, ask for them now!
    for key in (
        "efile_case_category",
        "efile_case_type",
        "efile_case_subtype",
        "previous_case_id",
        "docket_number",
        "user_preferred_language",
        "user_started_case",
        "user_role",
        "comments_to_clerk",
        "tyler_payment_id",
        "return_date",
        "amount_in_controversy",
        "out_of_state",
        "filer_type",
        "max_fee_amount",
        "procedure_remedy",
        "damage_amount",
        "is_contested_case",
        "email_confirmation_subject",
        "email_confirmation_contents",
        "acceptance_subject",
        "acceptance_contents",
        "rejected_subject",
        "rejected_contents",
        "neutral_subject",
        "neutral_contents",
    ):
        to_send_dict[key] = all_vars_dict.get(key)

    # Simple lists or dicts (i.e. not people or filings)
    for key in (
        "attorney_ids",
        "party_to_attorneys",
        "service_contacts",
        "lower_court_case",
        "trial_court",
        "cross_references",
    ):
        to_send_dict[key] = all_vars_dict.get(key)

    def person_convert(person):
        new_person = {
            person_key: person.get(person_key)
            for person_key in (
                "mobile_number",
                "phone_number",
                "email",
                "party_type",
                "prefered_language",
                "gender",
                "date_of_birth",
                "person_type",
                "is_form_filler",
                "name",
                "tyler_id",
                "is_new",
            )
        }
        old_address = person.get("address") or {}
        new_person["address"] = {
            key: old_address.get(key)
            for key in ("address", "unit", "city", "state", "country", "county")
        }
        return new_person

    # The people
    for key in (
        "users",
        "other_parties",
    ):
        people = all_vars_dict.get(key)
        people_list = people.get("elements")
        new_people_list = []
        for person in people_list:
            new_person = person_convert(person)
            new_people_list.append(new_person)
        to_send_dict[key] = new_people_list

    if "lead_contact" in all_vars_dict:
        to_send_dict["lead_contact"] = person_convert(
            all_vars_dict.get("lead_contact") or {}
        )

    court_bundle = all_vars_dict.get("al_court_bundle")
    bundle_list = court_bundle.get("elements")
    new_bundle_list = []
    ATTACHMENT_KEYS = [
        "document_type",
        "filing_component",
        "filename",
        "document_description",
        "data_url",
        "proxy_enabled",
        "page_count",
    ]
    for doc in bundle_list:
        if doc.get("proxy_enabled"):
            new_doc = {
                doc_key: doc.get(doc_key)
                for doc_key in (
                    "proxy_enabled",
                    "filing_type",
                    "motion_type",
                    "optional_services",
                    "due_date",
                    "filing_description",
                    "reference_number",
                    "filing_attorney",
                    "filing_comment",
                    "courtesy_copies",
                    "preliminary_copies",
                    "filing_parties",
                    "filing_action",
                    "tyler_merge_attachments",
                )
            }
            for maybe_key in ATTACHMENT_KEYS:
                if maybe_key in doc:
                    new_doc[maybe_key] = doc.get(maybe_key)

            new_doc["elements"] = []
            for old_elem in doc.get("elements") or []:
                if old_elem.get("proxy_enabled"):
                    new_doc["elements"].append(
                        {
                            elem_key: old_elem.get(elem_key)
                            for elem_key in ATTACHMENT_KEYS
                        }
                    )
            new_bundle_list.append(new_doc)

    to_send_dict["al_court_bundle"] = new_bundle_list

    # TODO: needed?
    to_send_dict = _remove_all_da_emptys(to_send_dict)
    return to_send_dict


class ProxyConnection(EfspConnection):
    """The main class you use to communicate with the E-file proxy server from docassemble.

    Many methods are unchanged from the parent class, [EfspConnection](py_efsp_client#EfspConnection),
    and are documented there.
    """

    def __init__(
        self,
        *,
        url: str = None,
        api_key: str = None,
        credentials_code_block: str = "tyler_login",
        default_jurisdiction: str = None,
    ):
        """
        Creates the connection. Tries to get params from docassemble's config, but can
        be overriden with parameters to __init__.
        """
        temp_efile_config = get_config("efile proxy", {})
        if url is None:
            url = temp_efile_config.get("url", "")
        if api_key is None:
            api_key = temp_efile_config.get("api key")

        self.credentials_code_block = credentials_code_block

        interview_name = f"{current_context().filename}"
        interview_name = (
            interview_name.replace(".", "-").replace(":", "-").replace("/", "-")[:72]
        )
        super().__init__(
            url=url,
            api_key=api_key,
            default_jurisdiction=default_jurisdiction,
            interview_name=interview_name,
            logger=DALogger(logging.getLogger("docassemble")),
        )

    def _call_proxy(self, req: PreparedRequest) -> ApiResponse:
        try:
            resp = self.proxy_client.send(req)
            if resp.status_code == 401 and self.credentials_code_block:
                reconsider(self.credentials_code_block)
        except requests.ConnectionError as ex:
            return _user_visible_resp(
                f"Could not connect to the Proxy server at {self.base_url}: {ex}"
            )
        except requests.exceptions.MissingSchema as ex:
            return _user_visible_resp(f"Url {self.base_url} is not valid: {ex}")
        except requests.exceptions.InvalidURL as ex:
            return _user_visible_resp(f"Url {self.base_url} is not valid: {ex}")
        return _user_visible_resp(resp)

    def get_logger(self):
        if not hasattr(self, "logger"):
            # Copying what we do in `EfspConnection.get_logger` because it needs to
            # wrap the logger we're trying to make here.
            self.logger = LoggerWithContext(
                DALogger(logging.getLogger("docassemble")),
                {"session_id": self.get_session_id()},
            )
        return self.logger

    def authenticate_user(
        self,
        tyler_email: str = None,
        tyler_password: str = None,
        *,
        jurisdiction: str = None,
    ) -> ApiResponse:
        """
        Params:
            tyler_email (str)
            tyler_password (str)
        """
        temp_efile_config = get_config("efile proxy", {})
        if tyler_email is None:
            tyler_email = temp_efile_config.get("tyler email")
        if tyler_password is None:
            tyler_password = temp_efile_config.get("tyler password")
        resp = super().authenticate_user(
            tyler_email=tyler_email,
            tyler_password=tyler_password,
            jurisdiction=jurisdiction,
        )
        if resp.is_ok():
            store = DAStore(encrypted=True)
            for k, v in resp.data.get("tokens", {}).items():
                store.set(f"EFSP-{k}", v)
        return resp

    def register_user(
        self,
        person: Union[Individual, dict],
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
        if isinstance(person, Individual) or isinstance(person, ALIndividual):
            person_dict = person.as_serializable()
        else:
            person_dict = person
        return super().register_user(
            person_dict,
            registration_type,
            password=password,
            firm_name_or_id=firm_name_or_id,
        )

    #### Managing Firm Users

    def update_firm(self, firm: Union[Dict, Person]) -> ApiResponse:
        # firm is stateful
        if isinstance(firm, dict):
            firm_dict = firm
        else:
            firm_dict = serialize_person(firm)
        return super().update_firm(firm_dict)

    # Managing Service Contacts
    def update_service_contact(
        self,
        service_contact_id: str,
        service_contact: Union[Individual, Dict],
        is_public: bool = None,
        is_in_master_list: bool = None,
        admin_copy: str = None,
    ) -> ApiResponse:
        if isinstance(service_contact, dict):
            service_contact_dict = service_contact
        else:
            service_contact_dict = serialize_person(service_contact)
        return super().update_service_contact(
            service_contact_id,
            service_contact_dict,
            is_public=is_public,
            is_in_master_list=is_in_master_list,
            admin_copy=admin_copy,
        )

    def create_service_contact(
        self,
        service_contact: Union[Dict, Individual],
        *,
        is_public: bool,
        is_in_master_list: bool,
        admin_copy: str = None,
    ) -> ApiResponse:
        if isinstance(service_contact, dict):
            service_contact_dict = service_contact
        else:
            service_contact_dict = serialize_person(service_contact)
        return super().create_service_contact(
            service_contact_dict,
            is_public=is_public,
            is_in_master_list=is_in_master_list,
            admin_copy=admin_copy,
        )

    def check_filing(
        self, court_id: str, court_bundle: Union[ALDocumentBundle, dict]
    ) -> ApiResponse:
        all_vars = (
            _get_all_vars(court_bundle, key="preview")
            if isinstance(court_bundle, ALDocumentBundle)
            else court_bundle
        )
        return super().check_filing(court_id, all_vars)

    def file_for_review(
        self, court_id: str, court_bundle: Union[ALDocumentBundle, dict]
    ) -> ApiResponse:
        all_vars = (
            _get_all_vars(court_bundle)
            if isinstance(court_bundle, ALDocumentBundle)
            else court_bundle
        )
        if get_config("debug"):
            log(all_vars, "console")
        return super().file_for_review(court_id, all_vars)

    def get_service_types(
        self, court_id: str, court_bundle: Union[ALDocumentBundle, dict] = None
    ) -> ApiResponse:
        """Checks the court info: if it has conditional service types, call a special API with all filing info so far to get service types"""
        court_info = self.get_court(court_id)
        if court_info.data.get("hasconditionalservicetypes") and court_bundle:
            all_vars = (
                _get_all_vars(court_bundle)
                if isinstance(court_bundle, ALDocumentBundle)
                else court_bundle
            )
        else:
            all_vars = {}
        return super().get_service_types(court_id, all_vars=all_vars)

    def calculate_filing_fees(
        self, court_id: str, court_bundle: Union[ALDocumentBundle, dict]
    ):
        all_vars = (
            _get_all_vars(court_bundle, key="preview")
            if isinstance(court_bundle, ALDocumentBundle)
            else court_bundle
        )
        return super().calculate_filing_fees(court_id, all_vars)

    def get_return_date(
        self,
        court_id: str,
        req_return_date,
        court_bundle: Union[ALDocumentBundle, dict],
    ):
        all_vars = (
            _get_all_vars(court_bundle, key="preview")
            if isinstance(court_bundle, ALDocumentBundle)
            else court_bundle
        )
        return super().get_return_date(court_id, req_return_date, all_vars)

    def get_cases(
        self, court_id: str, *, person: ALIndividual = None, docket_number: str = None
    ):
        if person is None:
            return super().get_cases_raw(court_id, docket_number=docket_number)
        if person.person_type == "business":
            return super().get_cases_raw(
                court_id, business_name=person.name.first, docket_number=docket_number
            )
        else:
            return super().get_cases_raw(
                court_id,
                person_name=person.name.as_serializable(),
                docket_number=docket_number,
            )


def serialize_person(person: Union[Person, Individual]) -> Dict:
    """
    Converts a Docassemble Person or Individual into a dictionary suitable for
    json.dumps and in format expected by Tyler-specific endpoints on the EFSPProxy
    """
    if isinstance(person, Individual):
        return_dict = {
            "firstName": person.name.first,
            "middleName": (
                person.name.middle if hasattr(person.name, "middle") else None
            ),
            "lastName": person.name.last,
        }
    else:
        return_dict = {
            "firmName": person.name.text if hasattr(person.name, "text") else None,
        }
    return_dict.update(
        {
            "address": {
                "addressLine1": (
                    person.address.address
                    if hasattr(person.address, "address")
                    else None
                ),
                "addressLine2": (
                    person.address.unit if hasattr(person.address, "unit") else None
                ),
                "city": (
                    person.address.city if hasattr(person.address, "city") else None
                ),
                "state": (
                    person.address.state if hasattr(person.address, "state") else None
                ),
                "zipCode": (
                    person.address.zip if hasattr(person.address, "zip") else None
                ),
                "country": (
                    person.address.country
                    if hasattr(person.address, "country")
                    else "US"
                ),
            },
            "phoneNumber": (
                person.phone_number if hasattr(person, "phone_number") else None
            ),
            "email": person.email if hasattr(person, "email") else "",
        }
    )

    return return_dict
