@interviews_start
Feature: Make any type of filing

  Runs the `any_filing_interview.yml` to completion a few different ways

  @any_filing_interview @af1
  Scenario: any_filing_interview goes to end
    Given I start the interview at "any_filing_interview.yml"
    And the maximum seconds for each Step in this Scenario is 50
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I get to the question id "service contact" with this data:
      | var | value | trigger |
      | trial_court | peoria | |
      | filing_interview_initial_or_existing | existing_case | |
      | x.do_what_choice | docket_lookup | case_search.do_what_choice |
      | x.docket_number_from_user | 22-AD-00005 | case_search.docket_number_from_user |
      | x.self_in_case | is_filing | case_search.self_in_case |
      | x.self_partip_choice | case_search.found_case.participants[0] | case_search.self_in_case |
      | user_ask_role | defendant | |
      | other_parties.there_are_any | False | |
      | users.there_is_another | False | |
      | existing_parties_new_atts.there_are_any | False | |
      | lead_contact.email | example@example.com | |
      | lead_contact.name.first | Bob | |
      | lead_contact.name.last | Ma | |
      | x.filing_type | 145436 | |
      | x.filing_description | example description | |
      | x.exhibits[0].pages | example_upload.pdf | |
      | x.document_type | 7688 | lead_doc.document_description |
      | x.user_chosen_filing_component | 332 | lead_doc.user_chosen_filing_component |
      | x[i].pages.target_number | 1 | lead_doc.exhibits[0].pages.there_is_another |
      | x.existing_parties_payment_dict['3d5553d6-112f-4aec-894f-a5441c1fc304'] | True | lead_doc.existing_parties_payment_dict |
      | contacts_to_attach.there_are_any | False | |
      | service_contacts.there_are_any | True | |
    And I set the var "service_contacts[i].contact_id" to "d19d0890-05c2-4aa6-942f-4834e73bcea2"
    And I set the var "service_contacts[i].service_type" to "-580"
    And I set the var "service_contacts[i].attach_service_contact_to_party" to "True"
    And I set the var "service_contacts[i].party_association" to "3d5553d6-112f-4aec-894f-a5441c1fc304"
    And I tap to continue
    And I get to the question id "ready to efile" with this data:
      | var | value | trigger |
      | service_contacts.target_number | 1 | service_contacts.there_is_another |
      | x.filing_action | efile_and_serve | lead_doc.filing_action |
      | x.optional_services.there_are_any | False | lead_doc.optional_services.there_are_any |
      | al_court_bundle.target_number | 1 | |
      | tyler_payment_id | 75950d4b-f3c3-4748-8bfb-0e22790d19d7 | |
      | review_fees['agrees_to_pay_fees'] | True | |
    Then I see the phrase "Below is your Lead Filing Doc"

  @any_filing_interview @prose @af2
  Scenario: any_filing_interview can handle a pro-se user
    Given I start the interview at "any_filing_interview.yml"
    And the maximum seconds for each Step in this Scenario is 50
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I tap to continue
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I get to the question id "service contact" with this data:
      | var | value | trigger |
      | trial_court | peoria | |
      | filing_interview_initial_or_existing | existing_case | |
      | x.do_what_choice | docket_lookup | case_search.do_what_choice |
      | x.docket_number_from_user | 22-AD-00005 | case_search.docket_number_from_user |
      | x.self_in_case | is_self | case_search.self_in_case |
      | x.self_partip_choice | case_search.found_case.participants[0] | case_search.self_in_case |
      | users[0].is_form_filler | False | |
      | user_ask_role | defendant | |
      | users.there_is_another | False | |
      | other_parties.there_are_any | False | |
      | existing_parties_new_atts.there_are_any | False | |
      | lead_contact.email | example@example.com | |
      | lead_contact.name.first | Bob | |
      | lead_contact.name.last | Ma | |
      | x.filing_type | 145436 | |
      | x.filing_description | example description | |
      | x.exhibits[0].pages | example_upload.pdf | |
      | x.document_type | 7688 | lead_doc.document_type |
      | x.user_chosen_filing_component | 332 | lead_doc.user_chosen_filing_component |
      | x[i].pages.target_number | 1 | lead_doc.exhibits[0].pages.there_is_another |
      | x.existing_parties_payment_dict['3d5553d6-112f-4aec-894f-a5441c1fc304'] | True | lead_doc.existing_parties_payment_dict |
      | service_contacts.there_are_any | True | |
    And I set the var "service_contacts[i].contact_id" to "d19d0890-05c2-4aa6-942f-4834e73bcea2"
    And I set the var "service_contacts[i].service_type" to "-580"
    And I set the var "service_contacts[i].attach_service_contact_to_party" to "True"
    And I set the var "service_contacts[i].party_association" to "3d5553d6-112f-4aec-894f-a5441c1fc304"
    And I tap to continue
    And I get to the question id "ready to efile" with this data:
      | var | value | trigger |
      | service_contacts.target_number | 1 | service_contacts.there_is_another |
      | x.filing_action | efile_and_serve | lead_doc.filing_action |
      | x.optional_services.there_are_any | False | lead_doc.optional_services.there_are_any |
      | al_court_bundle.target_number | 1 | |
      | tyler_payment_id | 75950d4b-f3c3-4748-8bfb-0e22790d19d7 | |
      | review_fees['agrees_to_pay_fees'] | True | |
    Then I see the phrase "Below is your Lead Filing Doc"

    @any_filing_interview @accessibility @full_accessible_run @af3
    Scenario: any_filing_interview is accessible
      Given I start the interview at "any_filing_interview.yml"
      And I check all pages for accessibility issues
      And the maximum seconds for each Step in this Scenario is 100
      And I set the variable "jurisdiction_id" to "illinois"
      And I tap to continue
      And I tap to continue
      And I set the variable "my_username" to secret "PROSE_EMAIL"
      And I set the variable "my_password" to secret "PROSE_PASSWORD"
      And I tap to continue
      And I set the variable "trial_court" to "adams"
      And I tap to continue
      And I set the variable "filing_interview_initial_or_existing" to "existing_case"
      And I tap to continue
      And I set the variable "x.do_what_choice" to "party_search"
      And I tap to continue
      And I set the variable "case_search.somebody.person_type" to "ALIndividual"
      And I set the variable "case_search.somebody.name.first" to "John"
      And I set the variable "case_search.somebody.name.last" to "Brown"
      And I tap to continue
      And I wait 30 seconds
      And I get to the question id "ready to efile" with this data:
        | var | value | trigger |
        | x.case_choice | case_search.found_cases[1] | case_search.case_choice |
        | user_ask_role | defendant | |
        | other_parties.there_are_any | False | |
        | existing_parties_new_atts.there_are_any | False | |
        | x.self_in_case | is_self | case_search.self_in_case |
        | x.self_partip_choice | case_search.found_cases[1].participants[1] | case_search.self_in_case |
        | users[0].is_form_filler | False | |
        | lead_contact.email | example@example.com | |
        | users.there_is_another | False | |
        | other_parties.there_is_another | False | |
        | lead_contact.name.first | Bob | |
        | lead_contact.name.last | Ma | |
        | x.filing_type | 142264 | |
        | x.filing_description | example description | |
        | x.exhibits[0].pages | example_upload.pdf | |
        | x.document_type | 5766 | lead_doc.document_type |
        | x.user_chosen_filing_component | 332 | lead_doc.user_chosen_filing_component |
        | x[i].pages.target_number | 1 | lead_doc.exhibits[0].pages.there_is_another |
        | x.existing_parties_payment_dict['350e3cb1-616b-493a-96a0-fca7492dd29b'] | True | lead_doc.existing_parties_payment_dict |
        | service_contacts.there_are_any | False | |
        | x.filing_action | efile_and_serve | lead_doc.filing_action |
        | x.optional_services.there_are_any | False | lead_doc.optional_services.there_are_any |
        | al_court_bundle.target_number | 1 | |
        | tyler_payment_id | 75950d4b-f3c3-4748-8bfb-0e22790d19d7 | |
        | review_fees['agrees_to_pay_fees'] | True | |
      Then I see the phrase "Below is your Lead Filing Doc"
