#! /usr/bin/env python3

import os
import json
import sys
import subprocess
from docassemble.EFSPIntegration.py_efsp_client import EfspConnection, ApiResponse
from pathlib import Path
from datetime import datetime, timedelta


def get_proxy_server_ip():
    # Figure out the ip addr of the service, assuming it's running through
    # Docker compose
    info_json = subprocess.check_output(
        ["docker", "inspect", "efileproxyserver_efspjava_1"]
    )
    if info_json:
        info_dict = json.loads(info_json)
        base_url = (
            "http://"
            # + info_dict[0]["NetworkSettings"]["Networks"]["efileproxyserver_default"]["IPAddress"]
            + "localhost"
            + ":9000/"
        )
        print("Using URL: " + base_url)
        return base_url
    else:
        print("FAILED Can't find the docker image!")
        return None


def mock_person():
    per = {}
    per["email"] = "fakeemail@example.com"
    # Neat trick: https://stackoverflow.com/a/24448351/11416267
    per["name"] = {
        "first": "B",
        "middle": "S",
        "last": "W",
    }
    per["address"] = {
        "addressLine1": "123 Fakestreet Ave",
        "addressLine2": "Apt 1",
        "city": "Boston",
        "state": "MA",
        "zipCode": "12345",
        "country": "US",
    }
    per["phoneNumber"] = "1234567890"
    return per


class TestClass:
    def __init__(
        self, proxy_conn, verbose: bool = True, user_email=None, user_password=None
    ):
        self.proxy_conn = proxy_conn
        self.verbose = verbose
        self.user_email = user_email
        self.user_password = user_password

    def basic_assert(self, resp: ApiResponse):
        if self.verbose or not resp.is_ok():
            print(resp)
        assert resp.is_ok()
        return resp

    def test_authenticate(self):
        print("\n\n### Authenticate ###\n\n")
        empty_resp = self.proxy_conn.authenticate_user()
        self.basic_assert(empty_resp)
        assert len(empty_resp.data["tokens"]) == 0
        resp = self.proxy_conn.authenticate_user(
            tyler_email=self.user_email, tyler_password=self.user_password
        )
        self.basic_assert(resp)

    def test_hateos(self):
        print("\n\n### Hateos ###\n\n")
        base_url = self.proxy_conn.base_url
        base_send = lambda: self.proxy_conn.proxy_client.get(base_url)
        next_level_urls = self.basic_assert(self.proxy_conn._call_proxy(base_send)).data
        all_urls = [url for url in next_level_urls.values()]
        visited_urls = set()
        while len(all_urls) > 0:
            url = all_urls.pop(0)
            if url in visited_urls:
                continue
            else:
                visited_urls.add(url)
            if "authenticate" in url:
                continue
            if "logs" in url:
                continue
            if "{" in url or "}" in url:
                continue
            # TODO(brycew): scheduling is broken, /service-contacts/public isn't RESTful
            if (
                "scheduling" in url
                or "service-contacts/public" in url
                or (
                    (
                        "adminusers" in url
                        or "firmattorneyservice" in url
                        or "payments" in url
                    )
                    and "illinois" not in url
                )
            ):
                continue
            print(f"visiting {url}")
            send = lambda: self.proxy_conn.proxy_client.get(url)
            resp = self.basic_assert(self.proxy_conn._call_proxy(send)).data
            if isinstance(resp, dict):
                for url in resp.values():
                    if isinstance(url, str) and url.startswith("http"):
                        all_urls.append(url)
                    elif (
                        isinstance(url, dict)
                        and ("method" in url and url["method"] == "GET")
                        and "url" in url
                    ):
                        all_urls.append(url["url"])

    def test_self_user(self):
        print("\n\n### Self user ###\n\n")
        myself = self.basic_assert(self.proxy_conn.get_user())
        assert myself.data["middleName"] == "Steven"
        nm = self.basic_assert(
            self.proxy_conn.update_user(myself.data["userID"], middle_name="Stephen")
        )
        bad_spelling = self.basic_assert(self.proxy_conn.get_user())
        assert bad_spelling.data["middleName"] == "Stephen"
        self.basic_assert(self.proxy_conn.self_update_user(middle_name="Steven"))

        # Password stuff
        current_password = self.user_password
        new_password = "12345678AbcDe!"
        email = self.user_email
        changed_password = self.basic_assert(
            self.proxy_conn.self_change_password(current_password, new_password)
        )
        self.basic_assert(
            self.proxy_conn.authenticate_user(
                tyler_email=email, tyler_password=new_password
            )
        )
        changed_back = self.basic_assert(
            self.proxy_conn.self_change_password(new_password, current_password)
        )
        self.basic_assert(
            self.proxy_conn.authenticate_user(
                tyler_email=email, tyler_password=current_password
            )
        )

        self.basic_assert(self.proxy_conn.get_notification_options())
        self.basic_assert(self.proxy_conn.get_notification_preferences())
        self.basic_assert(
            self.proxy_conn.update_notification_preferences(
                [{"code": "SERVICEUNDELIVERABLE", "isActive": False}]
            )
        )
        new_notifs = self.basic_assert(self.proxy_conn.get_notification_preferences())
        assert all(
            map(
                lambda n: n["isActive"] == False,
                filter(lambda n: n["code"] == "SERVICEUNDELIVERABLE", new_notifs.data),
            )
        )
        last_update = self.proxy_conn.update_notification_preferences(
            [{"code": "SERVICEUNDELIVERABLE", "isActive": True}]
        )
        assert last_update.response_code == 200

    def test_service_contacts(self):
        print("\n\n### Service Contacts ###\n\n")
        public = self.basic_assert(
            self.proxy_conn.get_public_service_contacts(first_name="John")
        )
        new_contact = {
            "firstName": "Ella",
            "lastName": "Doe",
            "email": "ella.doe@example.com",
            "address": {
                "addressLine1": "123 Fakestreet Ave",
                "addressLine2": "Unit 999",
                "city": "Boston",
                "state": "MA",
                "zipCode": "12345",
                "country": "US",
            },
            "phoneNumber": "9727133770",
        }
        new_c = self.basic_assert(
            self.proxy_conn.create_service_contact(
                new_contact,
                is_public=False,
                is_in_master_list=True,
                admin_copy="ella.doe@example.com",
            )
        )
        contact_id = new_c.data
        new_contact["middleName"] = '"Lorde"'
        new_contact["email"] = "different@example.com"
        self.basic_assert(
            self.proxy_conn.update_service_contact(
                contact_id, new_contact, is_public=False, is_in_master_list=True
            )
        )

        my_list = self.basic_assert(self.proxy_conn.get_service_contact_list())
        assert len(my_list.data) >= 1
        updated_contact = self.basic_assert(
            self.proxy_conn.get_service_contact(contact_id)
        )
        assert updated_contact.data["email"] == "different@example.com"
        assert updated_contact.data["middleName"] == '"Lorde"'

        self.basic_assert(
            self.proxy_conn.attach_service_contact(
                contact_id, "c6d795d1-3f89-411d-8c86-fa1a33fb88e5"
            )
        )
        self.basic_assert(
            self.proxy_conn.detach_service_contact(
                contact_id, "c6d795d1-3f89-411d-8c86-fa1a33fb88e5"
            )
        )

        self.basic_assert(self.proxy_conn.remove_service_contact(contact_id))

    def test_firm(self):
        print("\n\n### Firm ###\n\n")
        update_firm = {}
        update_firm["firmName"] = "Suffolk FIT Lab"
        update_firm["address"] = {"addressLine1": "121 Tremont Street"}
        resp = self.proxy_conn.update_firm(update_firm)
        assert resp.response_code == 200

        new_firm = self.basic_assert(self.proxy_conn.get_firm())
        assert new_firm.data["firmName"] == "Suffolk FIT Lab"
        assert new_firm.data["address"]["addressLine1"] == "121 Tremont Street"

        update_firm["firmName"] = "Suffolk LIT Lab"
        update_firm["address"]["addressLine1"] = "120 Tremont Street"
        self.basic_assert(self.proxy_conn.update_firm(update_firm))

        firm = self.basic_assert(self.proxy_conn.get_firm())
        assert firm.data["firmName"] == "Suffolk LIT Lab"
        assert firm.data["isIndividual"] == False
        assert firm.data["address"]["addressLine1"] == "120 Tremont Street"

    def test_users(self):
        print("\n\n### Users ###\n\n")
        all_initial_users = self.basic_assert(self.proxy_conn.get_users())
        person = mock_person()
        for u in all_initial_users.data:
            if u["email"] == person["email"]:
                self.basic_assert(self.proxy_conn.remove_user(u["userID"]))
                all_initial_users = self.basic_assert(self.proxy_conn.get_users())
                break
        firm_id = self.proxy_conn.get_firm().data["firmID"]
        new_user = self.proxy_conn.register_user(
            person,
            registration_type="FIRM_ADMIN_NEW_MEMBER",
            firm_name_or_id=firm_id,
        )
        assert new_user.response_code == 201
        new_id = new_user.data["userID"]

        self.basic_assert(self.proxy_conn.resend_activation_email(new_id))

        full_user = self.basic_assert(self.proxy_conn.get_user(new_id))
        assert full_user.data["middleName"] == "S"

        all_users = self.basic_assert(self.proxy_conn.get_users())
        assert len(all_users.data) == len(all_initial_users.data) + 1

        roles = self.basic_assert(self.proxy_conn.get_user_roles(new_id))
        assert len(roles.data) == 1
        assert roles.data[0]["roleName"] == "FILER"

        new_role_add = self.proxy_conn.add_user_roles(
            new_id, [{"roleName": "FIRM_ADMIN"}]
        )
        assert new_role_add.response_code == 204

        new_roles = self.proxy_conn.get_user_roles(new_id)
        assert any(map(lambda r: r["roleName"] == "FIRM_ADMIN", new_roles.data))
        rm_roles = self.proxy_conn.remove_user_roles(
            new_id, [{"roleName": "FIRM_ADMIN"}]
        )
        assert rm_roles.response_code == 200

        original_roles = self.proxy_conn.get_user_roles(new_id)
        assert original_roles.response_code == 200
        assert roles.data == original_roles.data

        self.basic_assert(self.proxy_conn.remove_user(new_id))

    def test_get_courts(self):
        courts = self.basic_assert(self.proxy_conn.get_courts())
        assert "jefferson" in courts.data

    def test_global_payment_accounts(self):
        print("\n\n### Global payment accounts ###\n\n")
        all_accounts = self.proxy_conn.get_global_payment_account_list()
        if self.verbose:
            print(all_accounts)
        assert all_accounts.response_code == 200
        assert all_accounts.data[0]["firmID"] is None
        account_id = all_accounts.data[0]["paymentAccountID"]
        account = self.proxy_conn.get_global_payment_account(
            global_payment_account_id=account_id
        )
        if self.verbose:
            print(account)
        assert account.response_code == 200
        assert account.data["paymentAccountID"] == account_id

        update_account = self.proxy_conn.update_global_payment_account(
            account_id, account_name="New, Better Name"
        )
        if self.verbose:
            print(update_account)
        assert update_account.response_code == 200
        better_account = self.proxy_conn.get_global_payment_account(account_id)
        assert better_account.response_code == 200
        assert better_account.data["accountName"] == "New, Better Name"

        update_account = self.proxy_conn.update_global_payment_account(
            account_id, account_name=account.data["accountName"]
        )
        assert update_account.response_code == 200

        global_account = self.basic_assert(
            self.proxy_conn.create_waiver_account(
                "integration test global account", True
            )
        )
        self.basic_assert(
            self.proxy_conn.remove_global_payment_account(global_account.data)
        )

    def test_payment_accounts(self):
        print("\n\n### Payment accounts ###\n\n")
        self.basic_assert(self.proxy_conn.get_payment_account_type_list())
        self.basic_assert(self.proxy_conn.get_payment_account_list())
        self.basic_assert(self.proxy_conn.get_payment_account_list("adams"))

        new_account = self.basic_assert(
            self.proxy_conn.create_waiver_account("New Integration Test account", False)
        )
        id = new_account.data
        one_account = self.basic_assert(self.proxy_conn.get_payment_account(id))
        assert one_account.data["accountName"] == "New Integration Test account"
        assert one_account.data["paymentAccountID"] == id

        self.basic_assert(
            self.proxy_conn.update_payment_account(id, account_name="New, Better Name")
        )
        better_account = self.basic_assert(self.proxy_conn.get_payment_account(id))
        assert better_account.data["accountName"] == "New, Better Name"

        self.basic_assert(
            self.proxy_conn.update_payment_account(
                id, account_name=one_account.data["accountName"]
            )
        )
        self.basic_assert(self.proxy_conn.remove_payment_account(new_account.data))

    def test_court_record(self):
        print("\n\n### Court record ###\n\n")
        contact = {}
        contact["first"] = "John"
        contact["last"] = "Brown"
        cases = self.basic_assert(
            self.proxy_conn.get_cases_raw("adams", person_name=contact)
        )
        assert len(cases.data) > 0
        case_id = cases.data[0]["value"]["caseTrackingID"]["value"]
        case = self.basic_assert(self.proxy_conn.get_case("adams", case_id))
        doc_resp = self.proxy_conn.get_document("adams", case_id)
        assert doc_resp.response_code == 405
        serv_info = self.basic_assert(
            self.proxy_conn.get_service_information("adams", case_id)
        )
        history_serv_info = self.basic_assert(
            self.proxy_conn.get_service_information_history("adams", case_id)
        )

        if len(serv_info.data) > 0:
            serv_id = serv_info.data[0]
            attach_cases = self.proxy_conn.get_service_attach_case_list(
                "adams", serv_id
            )
            if self.verbose:
                print(attach_cases)

    def test_attorneys(self):
        print("\n\n### Attorneys ###\n\n")
        new_attorney = self.proxy_conn.create_attorney(
            bar_number="6224951",
            first_name="Valarie",
            middle_name="DONTUSE_IS_REAL_PERSON",
            last_name="Franklin",
        )
        assert new_attorney.response_code == 200
        new_attorney_id = new_attorney.data

        attorney_list = self.basic_assert(self.proxy_conn.get_attorney_list())
        assert any(map(lambda a: a["barNumber"] == "6224951", attorney_list.data))

        updated_attorney = self.basic_assert(
            self.proxy_conn.update_attorney(new_attorney_id, middle_name="Lobert")
        )
        assert updated_attorney.data is not None

        full_new_attorney = self.basic_assert(
            self.proxy_conn.get_attorney(new_attorney_id)
        )
        assert full_new_attorney.data["middleName"] == "Lobert"

        deleted_maybe = self.proxy_conn.remove_attorney(new_attorney_id)
        assert deleted_maybe.response_code == 200

    def test_filings(self):
        print("\n\n### Filings ###\n\n")
        court = "adams"
        filing_list = self.basic_assert(
            self.proxy_conn.get_filing_list(
                court,
                start_date=datetime.today() - timedelta(days=3),
                before_date=datetime.today(),
            )
        )
        policy = self.basic_assert(self.proxy_conn.get_policy(court))

        cdir = Path(__file__).resolve().parent
        with open(cdir.joinpath("opening_affidavit_adams.json"), "r") as f:
            all_vars_str = f.read()
        base_url = self.proxy_conn.base_url
        fees_send = lambda: self.proxy_conn.proxy_client.post(
            base_url
            + f"jurisdictions/illinois/filingreview/courts/{court}/filing/fees",
            data=all_vars_str,
        )
        fees_resp = self.basic_assert(self.proxy_conn._call_proxy(fees_send))
        check_send = lambda: self.proxy_conn.proxy_client.get(
            base_url
            + f"jurisdictions/illinois/filingreview/courts/{court}/filing/check",
            data=all_vars_str,
        )
        checked_resp = self.basic_assert(self.proxy_conn._call_proxy(check_send))
        return
        # IDK if I want to make a new filing each time, even if we cancel it
        file_send = lambda: self.proxy_conn.proxy_client.post(
            base_url + f"jurisdictions/illinois/filingreview/courts/{court}/filings",
            data=all_vars_str,
        )
        filing_resp = self.basic_assert(self.proxy_conn._call_proxy(file_send))

        for filing_id in filing_resp.data:
            status_resp = self.basic_assert(
                self.proxy_conn.get_filing_status(court, filing_id)
            )
            detail_resp = self.basic_assert(
                self.proxy_conn.get_filing(court, filing_id)
            )
            cancel_resp = self.basic_assert(
                self.proxy_conn.cancel_filing_status(court, filing_id)
            )

    def test_codes(self):
        print("\n\n### Codes ###\n\n")
        self.basic_assert(self.proxy_conn.get_court_list())
        self.basic_assert(self.proxy_conn.get_court("adams"))
        self.basic_assert(self.proxy_conn.get_datafield("adams", "GlobalPassword"))
        self.basic_assert(self.proxy_conn.get_disclaimers("adams"))
        categories = self.basic_assert(
            self.proxy_conn.get_case_categories("adams")
        ).data
        for idx, cat in enumerate(categories):
            if idx > 5:
                continue
            self.basic_assert(self.proxy_conn.get_case_types("adams", cat["code"]))

    def test_logs(self):
        print("\n\n### Test Logs ###\n\n")
        server_id = self.basic_assert(self.proxy_conn.get_server_id()).data
        all_logs = self.basic_assert(self.proxy_conn.get_logs())
        for l in all_logs.data:
            assert l.split("|")[1].strip() == server_id


def main(*, base_url, api_key, user_email=None, user_password=None):
    if not base_url:
        base_url = get_proxy_server_ip()
    if not api_key:
        print("You need to have the PROXY_API_KEY env var set; not running tests")
        return 1
    if not user_email:
        user_email = os.getenv("bryce_user_email")
    if not user_password:
        user_password = os.getenv("bryce_user_password")
    bad_proxy = EfspConnection(
        url=base_url, api_key="IntenionallyWrongKey", default_jurisdiction="illinois"
    )
    intentional_bad_resp = bad_proxy.authenticate_user()
    if intentional_bad_resp.response_code != 403:
        print(intentional_bad_resp)
    assert intentional_bad_resp.response_code == 403
    bad_proxy.proxy_client.close()
    proxy_conn = EfspConnection(
        url=base_url, api_key=api_key, default_jurisdiction="illinois"
    )
    proxy_conn.set_verbose_logging(False)
    tc = TestClass(
        proxy_conn, verbose=False, user_email=user_email, user_password=user_password
    )
    tc.test_authenticate()
    tc.test_hateos()
    tc.test_self_user()
    tc.test_firm()
    tc.test_service_contacts()
    tc.test_get_courts()
    tc.test_payment_accounts()
    tc.test_attorneys()
    tc.test_court_record()
    tc.test_users()
    tc.test_codes()
    tc.test_logs()
    # TODO(brycew): needs a more up to date JSON from any filing interiview
    tc.test_filings()
    print("Done!")
    # TODO(brycew): Tyler issue, have to wait on them
    # tc.test_global_payment_accounts()
    proxy_conn.proxy_client.close()


if __name__ == "__main__":
    main(
        base_url=sys.argv[1] if len(sys.argv) > 1 else None,
        api_key=os.getenv("PROXY_API_KEY"),
    )
