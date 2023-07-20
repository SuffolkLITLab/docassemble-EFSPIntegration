@interviews_start
Feature: The interviews run without erroring

  This file:
  [x] Test that each interview starts without an error.
  [x] Contains some additional example Steps. They use fake values and are commented out with a "#" so they won't run.

  These tests are made to work with the ALKiln testing framework, an automated testing framework made under the Document Assembly Line Project.

  @ai1 @admin_interview @taps @admin @attorneys
  Scenario: admin_interview.yml Admin login
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 30
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Attorneys-tab" tab 
    And I tap the "#create_attorney" element
    Then I should see the phrase "Comment: Tyler validates the bar number" 
  
  @ai2 @admin_interview @taps @prose @service_contacts
  Scenario: admin_interview.yml Pro Se login 
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 40
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    Then I tap the "#attach_service_contact" element

  @ai3 @admin_interview @taps @firm @accessibility
  Scenario: admin_interview.yml Get Firm
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 40
    And I check all pages for accessibility issues
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Firm-tab" tab
    And I tap the "#get_firm" element and wait 5 seconds
    Then I should see the phrase "Suffolk LIT Lab"
    And I tap to continue
    And I tap the "Tests-Firm-tab" tab
    And I tap the "#get_firm" element and wait 5 seconds
    Then I should see the phrase "Suffolk LIT Lab"

  @ai4 @admin_interview @taps @accessibility
  Scenario: admin_interview.yml is accessible
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 70
    And I check all pages for accessibility issues
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Firm-tab" tab
    And I tap the "#get_firm" element and wait 3 seconds
    Then I should see the phrase "Suffolk LIT Lab"
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_courts" element and wait 3 seconds
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_court" element
    And I set the variable "trial_court" to "cook:dr5"
    And I tap to continue

  @ai5 @admin_interview @taps @admin @courts
  Scenario: admin_interview.yml See court information
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 40
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_courts" element and wait 3 seconds
    Then I should see the phrase "cook:tr1"
    Then I should see the phrase "cook:dr5"
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_court" element
    And I set the variable "trial_court" to "cook:dr5" 
    And I tap to continue
    Then I should see the phrase "name: Cook County - Domestic Relations - District 5 - Bridgeview"

  @ai6 @admin_interview @attach
  Scenario: multiple-times through attach
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 60
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    And I tap the "#attach_service_contact" element
    And I set the variable "trial_court" to "peoria"
    And I tap to continue
    And I set the variable "x.do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "x.docket_number_from_user" to "87-SC-01549"
    And I tap to continue
    And I see the phrase "Small Claims"
    And I see the phrase "TOURAINE PAINTS"
    And I tap to continue
    And I set the variable "service_contact_id" to "4fc26680-6b9a-42bd-8934-c67aaee7c97f"
    And I tap to continue
    And I set the variable "case_party_id" to "87bfa962-ce95-43c7-8370-021828672a38"
    And I tap to continue
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    And I tap the "#attach_service_contact" element
    And I set the variable "trial_court" to "peoria"
    And I tap to continue
    And I set the variable "x.do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "x.docket_number_from_user" to "87-SC-01549"
    And I tap to continue
    And I see the phrase "Small Claims"
    And I see the phrase "TOURAINE PAINTS"
    And I tap to continue
    And I set the variable "service_contact_id" to "4fc26680-6b9a-42bd-8934-c67aaee7c97f"
    And I tap to continue
    And I set the variable "case_party_id" to "87bfa962-ce95-43c7-8370-021828672a38"
    And I tap to continue
    And I see the phrase "All ok! (204)"

  @ai7 @admin_interview @attach @prose
  Scenario: earlyish stop attach when no service contacts
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 60
    And I set the variable "jurisdiction_id" to "illinois"
    And I tap to continue
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    And I tap the "#attach_service_contact" element
    And I set the variable "trial_court" to "peoria"
    And I tap to continue
    And I set the variable "x.do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "x.docket_number_from_user" to "87-SC-01549"
    And I tap to continue
    And I see the phrase "Small Claims"
    And I see the phrase "TOURAINE PAINTS"
    And I tap to continue
    Then I see the phrase "You don’t have any service contacts you can add."