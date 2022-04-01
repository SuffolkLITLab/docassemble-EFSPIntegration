@interviews_start
Feature: The interviews run without erroring

  This file:
  [x] Test that each interview starts without an error.
  [x] Contains some additional example Steps. They use fake values and are commented out with a "#" so they won't run.

  These tests are made to work with the ALKiln testing framework, an automated testing framework made under the Document Assembly Line Project.

  @admin_interview 
  Scenario: admin_interview.yml runs
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 20
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Attorneys-tab" element
    And I tap the "create_attorney" element
    Then I see the phrase "Comment: Tyler validates the bar number" 

  @admin_interview
  Scenario: multiple-times through attach/detach
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 20
    And I set the variable "my_username" to secret "PROSE_EMAIL"
    And I set the variable "my_password" to secret "PROSE_PASSWORD"
    And I tap to continue
    And I tap the "Tests-Service_contacts-tab" element
    And I tap the "attach_service_contact" element
    And I set the variable "do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "trial_court" to "peoria"
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
    And I tap the "Tests-Service_contacts-tab" element
    And I tap the "attach_service_contact" element
    And I set the variable "do_what_choice" to "docket_lookup"
    And I tap to continue
    And I set the variable "trial_court" to "peoria"
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
