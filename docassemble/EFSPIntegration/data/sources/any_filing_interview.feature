@interviews_start
Feature: Make any type of filing

  Runs the `any_filing_interview.yml` to completion a few different ways

  @any_filing_interview
  Scenario: any_filing_interview starts
    Given I start the interview at "any_filing_interview.yml"
    And the maximum seconds for each Step in this Scenario is 50
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I get to the question id "Additional parties" with this data:
      | var | value | trigger |
      | trial_court | peoria | |
      | filing_interview_initial_or_existing | existing_case | |
      | do_what_choice | docket_lookup | |
      | docket_id_from_user | 22-AD-00005 | |
      | user_ask_role | defendant | |
    Then I see the phrase "Are you adding any additional parties to this filing?"

  @any_filing_interview
  Scenario: any_filing_interview can handle a pro-se user
    Given I start the interview at "any_filing_interview.yml"
    And the maximum seconds for each Step in this Scenario is 300
    And I tap to continue
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I get to the question id "ready to efile" with this data:
      | var | value | trigger |
      | trial_court | peoria | |
      | filing_interview_initial_or_existing | existing_case | |
      | do_what_choice | docket_lookup | |
      | docket_id_from_user | 22-AD-00005 | |
      | user_ask_role | defendant | |
      | is_adding_new_parties | False | |
      | other_parties.there_are_any | False | |
      | existing_parties_new_atts.there_are_any | False | |
      | lead_contact.email | example@example.com | |
      | lead_contact.name.first | Bob | |
      | lead_contact.name.last | Ma | |
      | x.filing_type | 145445 | lead_doc.filing_type |
      | x.filing_description | example description | lead_doc.filing_type |
      | x.exhibits[0].pages | example_upload.pdf | lead_doc.filing_type |
      | x.document_type_code | 7688 | lead_doc.document_type_code |
      | x.filing_component_code | 332 | lead_doc.filing_component_code |
      | x[i].pages.target_number | 1 | lead_doc.exhibits[0].pages.there_is_another |
      | x.existing_parties_payment_dict['3d5553d6-112f-4aec-894f-a5441c1fc304'] | True | lead_doc.existing_parties_payment_dict |
      | service_contacts.there_are_any | True | |
      | service_contacts[i].contact_id | d19d0890-05c2-4aa6-942f-4834e73bcea2 | service_contacts[0].contact_id |
      | service_contacts[i].service_type | -580 | service_contacts[0].service_type |
      | service_contacts.target_number | 1 | |
      | x.filing_action | efile_and_serve | lead_doc.filing_action |
      | x.optional_services.there_are_any | False | lead_doc.optional_services.there_are_any |
      | al_court_bundle.target_number | 1 | |
      | tyler_payment_id | 75950d4b-f3c3-4748-8bfb-0e22790d19d7 | |
      | review_fees | agrees_to_pay_fees | |
    Then I see the phrase "Below is your Lead Filing Doc"
