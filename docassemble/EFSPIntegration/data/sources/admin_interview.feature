@interviews_start
Feature: The interviews run without erroring

  This file:
  [x] Test that each interview starts without an error.
  [x] Contains some additional example Steps. They use fake values and are commented out with a "#" so they won't run.

  These tests are made to work with the ALKiln testing framework, an automated testing framework made under the Document Assembly Line Project.

  @admin_interview  @taps @admin @attorneys
  Scenario: admin_interview.yml Admin login
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 20
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Attorneys-tab" tab 
    And I tap the "#create_attorney" element.
    Then I should see the phrase "Comment: Tyler validates the bar number" 
  
  @admin_interview @taps @prose @service_contacts
  Scenario: admin_interview.yml Pro Se login 
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 20
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    Then I tap the "#attach_service_contact" element.

  @admin_interview @taps @firm
  Scenario: admin_interview.yml Get Firm
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 20
    And I check the page for accessibility issues
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I check the page for accessibility issues
    And I tap the "Tests-Firm-tab" tab
    And I tap the "#get_firm" element and wait 5 seconds
    And I check the page for accessibility issues
    Then I should see the phrase "Suffolk FIT Lab"
    And I tap to continue
    And I tap the "Tests-Firm-tab" tab
    And I tap the "#get_firm" element and wait 5 seconds
    Then I should see the phrase "Suffolk FIT Lab"

  @admin_interview @taps @accessibility
  Scenario: admin_interview.yml is accessible
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 50
    Then I check the page for accessibility issues
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    Then I check the page for accessibility issues
    And I tap the "Tests-Firm-tab" tab
    And I tap the "#get_firm" element and wait 5 seconds
    Then I check the page for accessibility issues
    Then I should see the phrase "Suffolk FIT Lab"
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_courts" element and wait 5 seconds
    Then I check the page for accessibility issues
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    Then I check the page for accessibility issues
    And I tap the "#get_court" element.
    And I set the variable "trial_court" to "cook:dr5"
    And I tap to continue
    Then I check the page for accessibility issues

  @admin_interview @taps @admin @courts
  Scenario: admin_interview.yml See court information
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 20
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_courts" element and wait 5 seconds
    Then I should see the phrase "cook:tr1"
    Then I should see the phrase "cook:dr5"
    And I tap to continue
    And I tap the "Tests-Filings-tab" tab
    And I tap the "#get_court" element.
    And I set the variable "trial_court" to "cook:dr5" 
    And I tap to continue
    Then I should see the phrase "name: Cook County - Domestic Relations - District 5 - Bridgeview"

  @admin_interview @attach
  Scenario: multiple-times through attach
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 40
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    And I tap the "#attach_service_contact" element.
    And I set the variable "trial_court" to "peoria"
    And I tap to continue
    And I set the variable "do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "docket_id_from_user" to "22-AD-00005"
    And I tap to continue
    And I see the phrase "IMPOUNDED ADOPTION"
    And I tap to continue
    And I set the variable "service_contact_id" to "4fc26680-6b9a-42bd-8934-c67aaee7c97f"
    And I tap to continue
    And I set the variable "case_party_id" to "66488af3-c376-4500-b99e-3ff665fcc5fd"
    And I tap to continue
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    And I tap the "#attach_service_contact" element.
    And I set the variable "trial_court" to "peoria"
    And I tap to continue
    And I set the variable "do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "docket_id_from_user" to "22-AD-00005"
    And I tap to continue
    And I see the phrase "IMPOUNDED ADOPTION"
    And I tap to continue
    And I set the variable "service_contact_id" to "4fc26680-6b9a-42bd-8934-c67aaee7c97f"
    And I tap to continue
    And I set the variable "case_party_id" to "66488af3-c376-4500-b99e-3ff665fcc5fd"
    And I tap to continue
    And I see the phrase "Service Contact already attached to case."

  @admin_interview @attach @prose
  Scenario: earlyish stop attach when no service contacts
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 40
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" tab 
    And I tap the "#attach_service_contact" element.
    And I set the variable "trial_court" to "peoria"
    And I tap to continue
    And I set the variable "do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "docket_id_from_user" to "22-AD-00005"
    And I tap to continue
    And I see the phrase "IMPOUNDED ADOPTION"
    And I tap to continue
    Then I see the phrase "You don’t have any service contacts you can add."