#! /usr/bin/env python3

"""
Env vars needed to run:

* PROXY_URL: URL where the EfileProxyServer is running
* PROXY_API_KEY: the API Key generated from the running EfileProxyServer
* TYLER_USER_EMAIL: the email of a user account in the specific jurisdiction of Tyler's EFM (should be a firm account)
* TYLER_USER_PASSWORD: the password for that user account
"""

import os
import json
import sys
import random
import subprocess
from docassemble.EFSPIntegration.py_efsp_client import EfspConnection, ApiResponse
from pathlib import Path
from datetime import datetime, timedelta

import unittest

jurisdiction = "illinois"  # 'massachusetts'

base_url = os.getenv("PROXY_URL")
api_key = os.getenv("PROXY_API_KEY")


def mock_person():
    per = {}
    per["email"] = f"fakeemail-no-conflicts-{random.randint(0, 1_000_000)}@example.com"
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


class BadAuth(unittest.TestCase):

    def test_misconfigured_proxy(self):
        if not base_url:
            print("Need to pass the Proxy Server URL")
            exit(1)
        bad_proxy = EfspConnection(
            url=base_url,
            api_key="IntenionallyWrongKey",
            default_jurisdiction=jurisdiction,
        )
        intentional_bad_resp = bad_proxy.authenticate_user()
        self.assertEqual(intentional_bad_resp.response_code, 403)
        bad_proxy.proxy_client.close()

    def test_good_but_no_password_proxy(self):
        good_proxy = EfspConnection(
            url=base_url,
            api_key=api_key,
            default_jurisdiction=jurisdiction,
        )

        empty_resp = good_proxy.authenticate_user()
        self.assertTrue(empty_resp.is_ok())
        self.assertEqual(empty_resp.data["tokens"], {})


class TestClass(unittest.TestCase):

    def setUp(self):
        # Constants
        self.jurisdiction = jurisdiction
        self.court = "adams"  # "appeals:acsj"
        self.record_court = "tazewell"  # "535"
        self.docket_number = "2022-SC-000005"  # "99H85SC000016"
        self.bar_number = "6224951"  # "012345A" # This MA value is still not correct
        self.filing_filename = "opening_affidavit_adams.json"  # no MA equivalent yet
        self.verbose = False

        # Actual setup
        self.user_email = os.getenv("TYLER_USER_EMAIL")
        self.user_password = os.getenv("TYLER_USER_PASSWORD")
        if not base_url:
            print("Need to pass the Proxy Server URL")
            exit(1)
        if not api_key:
            print("You need to have the PROXY_API_KEY env var set; not running tests")
            exit(2)
        self.proxy_conn = EfspConnection(
            url=base_url, api_key=api_key, default_jurisdiction=jurisdiction
        )
        self.proxy_conn.set_verbose_logging(self.verbose)
        self.setup_authenticate()

    def tearDown(self):
        self.proxy_conn.proxy_client.close()

    def basic_assert(self, resp: ApiResponse):
        if self.verbose or not resp.is_ok():
            print(resp)
        self.assertTrue(resp.is_ok())
        return resp

    def setup_authenticate(self):
        print("\n\n### Authenticate ###\n\n")
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
                    # and jurisdiction not in url
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
        nm = self.basic_assert(
            self.proxy_conn.update_user(myself.data["userID"], middle_name="Stephen")
        )
        bad_spelling = self.basic_assert(self.proxy_conn.get_user())
        self.assertEqual(bad_spelling.data["middleName"], "Stephen")
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
        for n in filter(lambda n: n["code"] == "SERVICEUNDELIVERABLE", new_notifs.data):
            self.assertFalse(n["isActive"])
        last_update = self.proxy_conn.update_notification_preferences(
            [{"code": "SERVICEUNDELIVERABLE", "isActive": True}]
        )
        self.assertEqual(last_update.response_code, 200)

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
        self.assertGreater(len(my_list.data), 1)
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

        self.basic_assert(self.proxy_conn.get_users())
        # With paging, there are now limits to how many users we can see
        # Also, we have 203 users now because removing them doesn't remove them, lol
        # assert len(all_users.data) == len(all_initial_users.data) + 1

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
        assert self.court in courts.data

    @unittest.skip("Tyler issue, have to wait on them")
    def test_global_payment_accounts(self):
        print("\n\n### Global payment accounts ###\n\n")
        all_accounts = self.proxy_conn.get_global_payment_account_list()
        if self.verbose:
            print(all_accounts)
        self.assertEqual(all_accounts.response_code, 200)
        self.assertIsNone(all_accounts.data[0]["firmID"])
        account_id = all_accounts.data[0]["paymentAccountID"]
        account = self.proxy_conn.get_global_payment_account(
            global_payment_account_id=account_id
        )
        if self.verbose:
            print(account)
        self.assertEqual(account.response_code, 200)
        self.assertEqual(account.data["paymentAccountID"], account_id)

        update_account = self.proxy_conn.update_global_payment_account(
            account_id, account_name="New, Better Name"
        )
        if self.verbose:
            print(update_account)
        self.assertEqual(update_account.response_code, 200)
        better_account = self.proxy_conn.get_global_payment_account(account_id)
        self.assertEqual(better_account.response_code, 200)
        self.assertEqual(better_account.data["accountName"], "New, Better Name")

        update_account = self.proxy_conn.update_global_payment_account(
            account_id, account_name=account.data["accountName"]
        )
        self.assertEqual(update_account.response_code, 200)

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
        self.basic_assert(self.proxy_conn.get_payment_account_list(self.court))

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
        # NOTE(brycew): Illinois turned off search by case name, so turning it off here.
        # Maybe consider testing this on another jurisdiction.
        # contact = {}
        # contact["first"] = "John"
        # contact["last"] = "Brown"

        cases = self.basic_assert(
            self.proxy_conn.get_cases_raw(
                self.record_court, docket_number=self.docket_number
            )  # person_name=contact)
        )
        self.assertGreater(len(cases.data), 0)
        case_id = cases.data[0]["value"]["caseTrackingID"]["value"]
        case_info = self.basic_assert(
            self.proxy_conn.get_case(self.record_court, case_id)
        )
        doc_resp = self.proxy_conn.get_document(self.record_court, case_id)
        self.assertEqual(doc_resp.response_code, 405)
        serv_info = self.basic_assert(
            self.proxy_conn.get_service_information(self.record_court, case_id)
        )
        history_serv_info = self.basic_assert(
            self.proxy_conn.get_service_information_history(self.record_court, case_id)
        )

        if len(serv_info.data) > 0:
            serv_id = serv_info.data[0]
            attach_cases = self.proxy_conn.get_service_attach_case_list(
                self.record_court, serv_id
            )
            if self.verbose:
                print(attach_cases)

    def test_attorneys(self):
        print("\n\n### Attorneys ###\n\n")
        new_attorney = self.basic_assert(
            self.proxy_conn.create_attorney(
                bar_number=self.bar_number,
                first_name="Valarie",
                middle_name="DONTUSE_IS_REAL_PERSON",
                last_name="Franklin",
            )
        )
        assert new_attorney.response_code == 200
        new_attorney_id = new_attorney.data

        attorney_list = self.basic_assert(self.proxy_conn.get_attorney_list())
        assert any(map(lambda a: a["barNumber"] == self.bar_number, attorney_list.data))

        updated_attorney = self.basic_assert(
            self.proxy_conn.update_attorney(new_attorney_id, middle_name="Lobert")
        )
        self.assertIsNotNone(updated_attorney.data)

        full_new_attorney = self.basic_assert(
            self.proxy_conn.get_attorney(new_attorney_id)
        )
        self.assertEqual(full_new_attorney.data["middleName"], "Lobert")

        deleted_maybe = self.proxy_conn.remove_attorney(new_attorney_id)
        self.assertEqual(deleted_maybe.response_code, 200)

    def test_filings(self):
        print("\n\n### Filings ###\n\n")
        filing_list = self.basic_assert(
            self.proxy_conn.get_filing_list(
                self.court,
                start_date=datetime.today() - timedelta(days=3),
                before_date=datetime.today(),
            )
        )
        policy = self.basic_assert(self.proxy_conn.get_policy(self.court))

        cdir = Path(__file__).resolve().parent
        with open(cdir.joinpath(self.filing_filename), "r") as f:
            all_vars = json.load(f)
        base_url = self.proxy_conn.base_url
        fees_resp = self.basic_assert(
            self.proxy_conn.calculate_filing_fees(self.court, all_vars=all_vars)
        )
        checked_resp = self.basic_assert(
            self.proxy_conn.check_filing(self.court, all_vars=all_vars)
        )

        # IDK if I want to make a new filing each time, even if we cancel it
        # filing_resp = self.basic_assert(self.proxy_conn.file_for_review(court, all_vars=all_vars))

        # for filing_id in filing_resp.data["filingIds"]:
        #    status_resp = self.basic_assert(
        #        self.proxy_conn.get_filing_status(court, filing_id)
        #    )
        #    detail_resp = self.basic_assert(
        #        self.proxy_conn.get_filing(court, filing_id)
        #    )
        #    cancel_resp = self.basic_assert(
        #        self.proxy_conn.cancel_filing_status(court, filing_id)
        #    )

    def test_codes(self):
        print("\n\n### Codes ###\n\n")
        self.basic_assert(self.proxy_conn.get_court_list())
        self.basic_assert(self.proxy_conn.get_court(self.court))
        self.basic_assert(self.proxy_conn.get_datafield(self.court, "GlobalPassword"))
        self.basic_assert(self.proxy_conn.get_disclaimers(self.court))
        categories = self.basic_assert(
            self.proxy_conn.get_case_categories(self.court)
        ).data
        for idx, cat in enumerate(categories):
            if idx > 5:
                break
            self.basic_assert(self.proxy_conn.get_case_types(self.court, cat["code"]))

    def test_logs(self):
        print("\n\n### Test Logs ###\n\n")
        server_id = self.basic_assert(self.proxy_conn.get_server_id()).data
        all_logs = self.basic_assert(self.proxy_conn.get_logs())
        for l in all_logs.data:
            self.assertEqual(l.split("|")[1].strip(), server_id)


if __name__ == "__main__":
    unittest.main()
