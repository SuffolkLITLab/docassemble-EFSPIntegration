"""Functions that help convert the JSON-ized XML from the proxy server into usable information."""

import re
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Any, Mapping, Callable, Optional, Union
import docassemble.base.util
from docassemble.base.util import (
    DADict,
    DAList,
    DAObject,
    DADateTime,
    as_datetime,
    validation_error,
    log,
    as_datetime,
)
from docassemble.AssemblyLine.al_general import ALIndividual, ALAddress
from docassemble.base.functions import get_config, illegal_variable_name, TypeType
from .efm_client import ApiResponse, ProxyConnection
import importlib
import dateutil.parser

__all__ = [
    "convert_court_to_id",
    "chain_xml",
    "choices_and_map",
    "pretty_display",
    "debug_display",
    "parse_service_contacts",
    "tyler_daterep_to_datetime",
    "tyler_timestamp_to_datetime",
    "validate_tyler_regex",
    "parse_case_info",
    "fetch_case_info",
    "filter_payment_accounts",
    "payment_account_labels",
    "filing_id_and_label",
    "get_tyler_roles",
]

TypeType = type(type(None))


def convert_court_to_id(trial_court) -> str:
    if hasattr(trial_court, "tyler_court_code"):
        return trial_court.tyler_court_code
    if hasattr(trial_court, "tyler_code"):
        return trial_court.tyler_code
    # The probably not right inputs
    if hasattr(trial_court, "name"):
        return str(trial_court.name).lower()
    if isinstance(trial_court, dict):
        return trial_court["code"]
    if isinstance(trial_court, str):
        return trial_court.lower()
    return trial_court


class SafeDict(dict):
    def disp(self, elem, attr):
        return (self.get(elem) or {}).get(attr, elem)


def choices_and_map(
    codes_list: List, display: str = None, backing: str = None
) -> Tuple[List[Any], Dict]:
    """Takes the responses from the 'codes' service and make a DA ready list of choices and a map back
    to the full code object"""
    if display is None:
        display = "{name}"
    if backing is None:
        backing = "code"

    if codes_list is None:
        return [], SafeDict({})

    if isinstance(codes_list, str):
        log(f"choices_and_map codes_list is a string? {codes_list}")
        return [], SafeDict({})

    choices_list = [
        (code_obj[backing], display.format(**code_obj)) for code_obj in codes_list
    ]
    codes_map = SafeDict({vv[backing]: vv for vv in codes_list})
    return choices_list, codes_map


def pretty_display(data, tab_depth=0, skip_xml=True, item_name=None) -> str:
    """Given an arbitrarily nested JSON structure, print it nicely.
    Recursive, for subsequent calls `tab_depth` increases."""
    tab_inc = 4
    out = ""
    tab_str = " " * tab_depth
    if isinstance(data, list):
        for idx, elem in enumerate(data):
            if item_name:
                out += tab_str + f"* {item_name}: {idx}\n"
            else:
                out += tab_str + f"* Item: {idx}\n"
            out += pretty_display(elem, tab_depth + tab_inc)

    elif isinstance(data, dict):
        if "declaredType" in data:
            if data["declaredType"] == "gov.niem.niem.niem_core._2.TextType":
                out += (
                    tab_str
                    + f"* {data['name'].replace(':', '/')}: {data['value']['value']}\n"
                )
                return out
            if data["declaredType"] == "gov.niem.niem.proxy.xsd._2.Boolean":
                out += (
                    tab_str
                    + f"* {data['name'].replace(':', '/')}: {data['value']['value']}\n"
                )
                return out
            if data["declaredType"] == "gov.niem.niem.proxy.xsd._2.DateTime":
                out += (
                    tab_str
                    + f"* date: {datetime.fromtimestamp(float(data['value']['value'])/1000)}\n"
                )
                return out
        for key, val in data.items():
            if (
                val is not None
                and (isinstance(val, dict))
                and "value" in val
                and isinstance(val["value"], str)
            ):
                out += tab_str + f"* {key}: {val['value']}\n"
            elif key == "nil" and not val:
                continue
            elif key == "globalScope" and val:
                continue
            elif key == "scope" and "GlobalScope" in val:
                continue
            elif key == "typeSubstituted" and (not val or val == "False"):
                continue
            elif skip_xml and key == "declaredType":
                continue
            elif (
                skip_xml
                and key == "name"
                and ("niem-core" in val or "legalxml-courtfiling" in val)
            ):
                continue
            elif val is not None and isinstance(val, str):
                out += tab_str + f"* {key}: {val}\n"
            elif val is not None and val != [] and val != {}:
                out += tab_str + f"* {key}: \n"
                item_name = key
                if item_name.startswith("document"):
                    item_name = item_name[8:]
                out += pretty_display(val, tab_depth + tab_inc, item_name=item_name)
    else:
        out = tab_str + str(data) + "\n"
    return out


def debug_display(resp: ApiResponse) -> str:
    """Returns a string with either the error of the response,
    or it's data run through pretty_display"""
    if resp.is_ok() and resp.data is None:
        return f"All ok! ({resp.response_code})"
    if not resp.is_ok():
        to_return = resp.error_msg if resp.error_msg is not None else ""
        if get_config("debug"):
            to_return += f"\nResponse Code: {resp.response_code}"
            if hasattr(resp, "data"):
                to_return += f"({resp.data})"
        return to_return
    log(f"resp.data: {resp.data}")
    return pretty_display(resp.data)


def tyler_daterep_to_datetime(tyler_daterep: Mapping) -> DADateTime:
    """
    Takes an jsonized-XML object of "{http://niem.gov/niem/niem-core/2.0}ActivityDate,
    returns the datetime it repsents.
    """
    timestamp = chain_xml(tyler_daterep, ["dateRepresentation", "value", "value"]) or 0
    return tyler_timestamp_to_datetime(timestamp)


def tyler_timestamp_to_datetime(timestamp_ms: int) -> DADateTime:
    """Given a timestamp in milliseconds from epoch (in UTC), make a datetime from it"""
    return as_datetime(datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc))


def validate_tyler_regex(data_field: Mapping) -> Callable:
    """
    Return a function that validates a given input with the provided regex,
    suitable for use with Docassemble's `validate:` question modifier
    """

    def fn_validate(input_str):
        if not data_field:
            return True  # Don't want to stop on-screen validation if we can't retrieve the code
        if re.match(data_field.get("regularexpression"), str(input_str)):
            return True
        validation_message = data_field.get("validationmessage")
        if not validation_message:
            validation_message = "Enter a valid value"
            # Hardcode the fallback validation message for 1-999. Inexplicably, no validation message
            # supplied for 1-999 in Illinois but I think this will stay the same for a long time
            if data_field.get("regularexpression") == r"^([1-9][0-9]{0,2})$":
                validation_message = "Enter a number betweeen 1-999"
            elif (
                data_field.get("regularexpression")
                == r"^([0-9]{0,9}(\.([0-9]{0,2}))?)$"
            ):
                validation_message = "Enter a number between 0-999,999,999"
            elif data_field.get("regularexpression") == r"^[0-9]*$":
                validation_message = "Enter only digits"
        validation_error(validation_message)

    return fn_validate


def _is_person(possible_person_entity: dict):
    """Helper for getting party ID"""
    # TODO(brycew): could also check the declaredType?
    return possible_person_entity.get("personOtherIdentification") is not None


def chain_xml(xml_val, elems: List[Union[str, int]]):
    val = xml_val
    for elem in elems:
        if not val:
            return None
        if isinstance(val, dict):
            val = val.get(elem) or {}
        else:
            try:
                val = val[elem]
            except:
                val = {}
    return val


def combine_opt_strs(elems: List[Optional[str]], title=True):
    ret = ""
    for val in elems:
        if val:
            if title:
                ret += " " + val.title()
            else:
                ret += " " + val
    return ret.strip()


def _parse_phone_number(phone_xml) -> Optional[str]:
    """Parses a gov.niem.niem.niem_core._2.TelephoneNumberType / nc:TelephoneNumberType into a string"""
    if phone_xml is None:
        return None
    if (
        phone_xml.get("name")
        == "{http://niem.gov/niem/niem-core/2.0}FullTelephoneNumber"
    ):
        return chain_xml(phone_xml, ["value", "telephoneNumberFullID", "value"])
    elif (
        phone_xml.get("name")
        == "{http://niem.gov/niem/niem-core/2.0}InternationalTelephoneNumber"
    ):
        return (
            chain_xml(phone_xml, ["value", "telephoneCountryCodeID", "value"]) or ""
        ) + (chain_xml(phone_xml, ["value", "telephoneNumberID", "value"]) or "")
    elif (
        phone_xml.get("name")
        == "{http://niem.gov/niem/niem-core/2.0}NANPTelephoneNumber"
    ):
        tp = phone_xml.get("value") or {}
        return (
            (chain_xml(tp, ["telephoneAreaCodeID", "value"]) or "")
            + (chain_xml(tp, ["telephoneExchanceID", "value"]) or "")
            + (chain_xml(tp, ["telephoneLineID", "value"]) or "")
        )
    else:
        # TODO(brycew): no telephone type we recognize?
        return None


def _parse_address(address_xml: Mapping) -> ALAddress:
    address = ALAddress()
    street_xml = chain_xml(address_xml, ["value", "addressDeliveryPoint", 0, "value"])
    # TODO(brycew): haven't seen street address IRL yet, not sure how it serializes
    if street_xml:
        street_full = chain_xml(street_xml, ["streetFullText", "value"])
        if street_full:
            address.address = street_full
        else:
            street_name = chain_xml(street_xml, ["streetName", "value"])
            street_number = chain_xml(street_xml, ["streetNumberText", "value"])
            if street_name and street_number:
                address.address = f"{street_number} {street_name}"
    city_xml = chain_xml(address_xml, ["value", "locationCityName"]) or {}
    if city_xml and "value" in city_xml:
        address.city = city_xml.get("value")
    zip_xml = chain_xml(address_xml, ["value", "locationPostalCode"]) or {}
    if zip_xml and "value" in zip_xml:
        address.zip = zip_xml.get("value")
    state_xml = chain_xml(address_xml, ["value", "locationState"]) or {}
    if state_xml and state_xml.get("value", {}).get("value"):
        address.state = state_xml.get("value", {}).get("value")
    return address


def _is_attorney(participant_val):
    role_code = chain_xml(
        participant_val, ["value", "caseParticipantRoleCode", "value"]
    )
    return role_code.upper() == "ATTY"


def _parse_participant_id(entity):
    """Just get the participant ID from the Participant"""
    if _is_person(entity):
        return (
            next(iter(entity.get("personOtherIdentification", {})), {})
            .get("identificationID", {})
            .get("value")
        )
    else:
        return chain_xml(
            entity,
            [
                "organizationIdentification",
                "value",
                "identification",
                0,
                "identificationID",
                "value",
            ],
        )


def _parse_name(name_obj, name_val):
    if not name_val:
        name_val = {}

    # TODO(brycew): some french last names are all caps? It could happen, but this is best for now.
    def make_readable(name):
        if len(name) > 1 and name.isupper():
            return name.title()
        return name

    name_obj.first = make_readable(name_val.get("personGivenName", {}).get("value", ""))
    name_obj.middle = make_readable(
        name_val.get("personMiddleName", {}).get("value", "")
    )
    name_obj.last = make_readable(name_val.get("personSurName", {}).get("value", ""))
    return name_obj


def _parse_contact_means(obj, contact_means_xml):
    if not contact_means_xml:
        contact_means_xml = []
    for contact_info in contact_means_xml:
        if (
            contact_info.get("name")
            == "{http://niem.gov/niem/niem-core/2.0}ContactTelephoneNumber"
        ):
            phone = _parse_phone_number(
                contact_info.get("value", {}).get("telephoneNumberRepresentation")
            )
            if phone:
                obj.phone_number = phone
        if (
            contact_info.get("name")
            == "{http://niem.gov/niem/niem-core/2.0}ContactMailingAddress"
        ):
            address = _parse_address(
                contact_info.get("value", {}).get("addressRepresentation")
            )
            if address:
                obj.address = address
                obj.address.instanceName = obj.instanceName + ".address"
        if (
            contact_info.get("name")
            == "{http://niem.gov/niem/niem-core/2.0}ContactEmailID"
        ):
            email = contact_info.get("value", {}).get("value")
            if email:
                obj.email = email
    return obj


def _parse_participant(part_obj, participant_val, roles: dict):
    """Given an xsd:CommonTypes-4.0:CaseParticipantType, fills it with necessary info"""
    part_obj.party_type = chain_xml(
        participant_val, ["value", "caseParticipantRoleCode", "value"]
    )
    part_obj.party_type_name = roles.get(part_obj.party_type, {}).get("name")
    entity = chain_xml(participant_val, ["value", "entityRepresentation", "value"])
    if _is_person(entity):
        part_obj.person_type = "ALIndividual"
        name = entity.get("personName") or {}
        _parse_name(part_obj.name, name)
        # TODO(brycew): parse the address, phone, and email if possible
        contact_xml = next(
            iter(entity.get("personAugmentation", {}).get("contactInformation", []))
        ).get("contactMeans", [])
        _parse_contact_means(part_obj, contact_xml)
    else:
        part_obj.person_type = "business"
        part_obj.name.first = entity.get("organizationName", {}).get("value", "")
    part_obj.tyler_id = _parse_participant_id(entity)
    return part_obj


def _parse_attorney(att_obj, att_val):
    """Given an Attorney (caseOtherEntityAttorney), gets the name and contact info into a docassemble object"""
    entity = chain_xml(att_val, ["roleOfPersonReference", "ref"])
    if entity:
        _parse_name(att_obj.name, entity.get("personName") or {})
        contact_xml = next(
            iter(entity.get("personAugmentation", {}).get("contactInformation", []))
        ).get("contactMeans", [])
        _parse_contact_means(att_obj, contact_xml)
    return att_obj


def parse_service_contacts(service_list):
    """We'll take both Tyler service contact lists and Niem service contact lists.
    Tyler's are just `{"firstName": "Bob", "middleName": "P", ..., "serviceContactId": "abcrunh-13..."
    Niem's are more complicated
    """
    info = []
    for contact in service_list:
        if (
            "firstName" in contact
            and "lastName" in contact
            and "serviceContactID" in contact
        ):
            serv_id = contact["serviceContactID"]
            display_name = combine_opt_strs(
                [
                    contact.get("firstName", ""),
                    contact.get("middleName", ""),
                    contact.get("lastName", ""),
                    contact.get("firmName", ""),
                ]
            )
        else:
            serv_id = chain_xml(
                contact,
                [
                    "entityRepresentation",
                    "value",
                    "personAugmentation",
                    "electronicServiceInformation",
                    "serviceRecipientID",
                    "identificationID",
                    "value",
                ],
            )
            per_name = chain_xml(
                contact, ["entityRepresentation", "value", "personName"]
            )
            display_name = (
                combine_opt_strs(
                    [
                        chain_xml(per_name, ["personGivenName", "value"]),
                        chain_xml(per_name, ["personMiddleName", "value"]),
                        chain_xml(per_name, ["personSurName", "value"]),
                    ],
                    title=True,
                )
                if per_name
                else "(No name given)"
            )
        info.append((serv_id, display_name))
    return info


def parse_case_info(
    proxy_conn: ProxyConnection,
    new_case: DAObject,
    entry: dict,
    court_id: str,
    *,
    fetch: bool = True,
    roles: dict = None,
):
    if not roles:
        roles = {}
    new_case.details = entry
    new_case.court_id = court_id
    new_case.title = chain_xml(entry, ["value", "caseTitleText", "value"])
    new_case.tracking_id = chain_xml(entry, ["value", "caseTrackingID", "value"])
    new_case.docket_number = chain_xml(entry, ["value", "caseDocketID", "value"])
    new_case.category = chain_xml(entry, ["value", "caseCategoryText", "value"])

    if fetch:
        fetch_case_info(proxy_conn, new_case, roles)


def fetch_case_info(
    proxy_conn: ProxyConnection, new_case: DAObject, roles: dict = None
):
    """Fills in these attributes with the full case details:
    * attorneys
    * party_to_attorneys
    * case_details_worked
    * case_details
    * case_type
    * title
    * date
    * participants
    """
    if not roles:
        roles = {}

    # NOTE: case court can change from searched location (i.e. search in peoria can find cases
    # in peoriacr); using the original here, but can change it here if necessary
    full_case_details = proxy_conn.get_case(new_case.court_id, new_case.tracking_id)
    if not full_case_details.is_ok():
        log(
            f"couldn't get full details for {new_case.court_id}-{ new_case.tracking_id}: {full_case_details}"
        )
    new_case.attorneys = DADict(
        new_case.instanceName + ".attorneys",
        object_type=ALIndividual,
        auto_gather=False,
    )
    new_case.party_to_attorneys = {}
    new_case.case_details_worked = (
        full_case_details.response_code,
        full_case_details.error_msg,
    )
    new_case.case_details = full_case_details.data or {}
    # TODO: is the order of this array predictable? might it break if Tyler changes something?
    new_case.case_type = (
        new_case.case_details.get("value", {})
        .get("rest", [{}, {}])[1]
        .get("value", {})
        .get("caseTypeText", {})
        .get("value")
    )
    maybe_court = chain_xml(
        new_case.case_details,
        [
            "value",
            "rest",
            0,
            "value",
            "caseCourt",
            "organizationIdentification",
            "value",
            "identificationID",
            "value",
        ],
    )
    if maybe_court:
        new_case.court_id = maybe_court
    new_case.efile_case_type = new_case.case_type
    new_case.title = chain_xml(
        new_case.case_details, ["value", "caseTitleText", "value"]
    )
    if new_case.title:
        new_case.title = re.sub(
            r"([A-Z])In the Matter of the Estate of([A-Z])",
            r"\1 In the Matter of the Estate of \2",
            new_case.title,
        )
        new_case.title = re.sub(r"([A-Z])vs([A-Z])", r"\1 vs \2", new_case.title)
    new_case.date = tyler_daterep_to_datetime(
        chain_xml(
            new_case.case_details, ["value", "activityDateRepresentation", "value"]
        )
    )
    new_case.participants = DAList(
        new_case.instanceName + ".participants",
        object_type=ALIndividual,
        auto_gather=False,
    )
    for aug in new_case.case_details.get("value", {}).get("rest", []):
        if "AppellateCaseOriginalCase" in aug.get("declaredType"):
            new_case.lower_docket_number = aug.get("value", {}).get("caseDocketID")
            new_case.lower_case_title = aug.get("value", {}).get("caseTitleText")
        if (
            aug.get("declaredType")
            == "tyler.ecf.extensions.common.CaseAugmentationType"
        ):
            new_case.lower_judge = aug.get("value", {}).get("lowerCourtJudgeText")
            participant_xml = aug.get("value", {}).get("caseParticipant", [])
            for participant in participant_xml:
                if not _is_attorney(participant):
                    partip_obj = new_case.participants.appendObject()
                    _parse_participant(partip_obj, participant, roles)

            attorneys = aug.get("value", {}).get("caseOtherEntityAttorney")
            for attorney in attorneys:
                entity = chain_xml(attorney, ["roleOfPersonReference", "ref"])
                tmp: Dict = next(iter(entity.get("personOtherIdentification", {})), {})
                attorney_tyler_id = tmp.get("identificationID", {}).get("value", None)
                new_att_obj = new_case.attorneys.initializeObject(
                    attorney_tyler_id, ALIndividual
                )
                _parse_attorney(new_att_obj, attorney)
                parties = attorney.get("caseRepresentedPartyReference", [])
                for party in parties:
                    party_id = _parse_participant_id(party.get("ref", {}))
                    if party_id in new_case.party_to_attorneys:
                        new_case.party_to_attorneys[party_id].append(attorney_tyler_id)
                    else:
                        new_case.party_to_attorneys[party_id] = [attorney_tyler_id]
                    for participant in new_case.participants.elements:
                        if participant.tyler_id == party_id:
                            if hasattr(participant, "existing_attorney_ids"):
                                participant.existing_attorney_ids.append(
                                    attorney_tyler_id
                                )
                            else:
                                participant.existing_attorney_ids = [attorney_tyler_id]
    new_case.participants.gathered = True
    new_case.attorneys.gathered = True


def _payment_labels(acc: Mapping) -> str:
    if acc.get("paymentAccountTypeCode") == "CC":
        return f"{acc.get('accountName')} ({acc.get('cardType',{}).get('value')}, {acc.get('cardLast4')})"
    elif acc.get("paymentAccountTypeCode") == "WV":
        return f"{acc.get('accountName')} (Waiver account)"
    else:
        return f"{acc.get('accountName')} ({acc.get('paymentAccountTypeCode')})"


def filter_payment_accounts(account_list, allowable_card_types) -> List:
    """Gets a list of all payment accounts and filters them by if the card is
    accepted at a particular court"""
    allowed_card = lambda acc: acc.get("paymentAccountTypeCode") != "CC" or (
        acc.get("paymentAccountTypeCode") == "CC"
        and acc.get("cardType", {}).get("value") in allowable_card_types
    )
    return [
        (acct.get("paymentAccountID"), _payment_labels(acct))
        for acct in account_list
        if acct.get("active", {}).get("value") and allowed_card(acct)
    ]


def payment_account_labels(resp):
    if resp.data:
        return [
            {account.get("paymentAccountID"): _payment_labels(account)}
            for account in resp.data
        ]
    else:
        return None


def filing_id_and_label(case: Mapping, style="FILING_ID") -> Dict[str, str]:
    tracking_id = case.get("caseTrackingID", {}).get("value")
    try:
        filing_id = (
            case.get("documentIdentification", [{}, {}])[1]
            .get("identificationID", {})
            .get("value")
        )
    except IndexError:
        filing_id = "id-not-found"
    filer_name = (
        case.get("documentSubmitter", {})
        .get("entityRepresentation", {})
        .get("value", {})
        .get("personName", {})
        .get("personFullName", {})
        .get("value")
    )
    document_description = case.get("documentDescriptionText", {}).get("value")
    # Filing code is plain English
    matching_category: Mapping = next(
        filter(
            lambda category: category.get("name")
            == "{urn:tyler:ecf:extensions:Common}FilingCode",
            case.get("documentCategoryText", []),
        ),
        {},
    )
    filing_code = matching_category.get("value", {}).get("value")
    try:
        filing_date = tyler_timestamp_to_datetime(
            case.get("documentFiledDate", {})
            .get("dateRepresentation", {})
            .get("value", {})
            .get("value", 1000)
        )
    except:
        filing_date = ""
    filing_label = (
        f"{filer_name} - {document_description} ({filing_code}) {filing_date}"
    )
    if style == "FILING_ID":
        return {filing_id: filing_label}
    else:
        return {tracking_id: filing_label}


def get_tyler_roles(
    proxy_conn: ProxyConnection,
    login_data: Mapping,
    user_details: Optional[ApiResponse] = None,
) -> Tuple[bool, bool]:
    """Gets whether or not the user of this interview is a Tyler Admin, and a 'global' admin.
    The global admin means that they are allowed to change specific Global payment methods,
    and can be listed under the 'global server admins' section of the 'efile proxy' settings in the
    DAConfig"""

    if not user_details:
        if not login_data:
            return False, False
        user_details = proxy_conn.get_user(
            login_data.get("TYLER-ID", login_data.get("TYLER_ID"))
        )

    if not user_details.data:
        return False, False

    is_admin = lambda role: role.get("roleName") == "FIRM_ADMIN"
    firm_details = proxy_conn.get_firm()
    logged_in_user_is_admin = any(
        filter(is_admin, user_details.data.get("role"))
    ) and not firm_details.data.get("isIndividual", False)
    logged_in_user_is_global_admin = logged_in_user_is_admin and user_details.data.get(
        "email"
    ) in get_config("efile proxy").get("global server admins", [])
    return logged_in_user_is_admin, logged_in_user_is_global_admin
