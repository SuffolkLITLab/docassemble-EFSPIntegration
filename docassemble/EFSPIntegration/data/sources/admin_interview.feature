@interviews_start
Feature: The interviews run without erroring

  This file:
  [x] Test that each interview starts without an error.
  [x] Contains some additional example Steps. They use fake values and are commented out with a "#" so they won't run.

  These tests are made to work with the ALKiln testing framework, an automated testing framework made under the Document Assembly Line Project.

  @admin_interview 
  Scenario: admin_interview.yml runs
    Given I start the interview at "admin_interview.yml"
    And the maximum seconds for each Step in this Scenario is 50
    And I set the variable "my_username" to secret "TYLER_EMAIL"
    And I set the variable "my_password" to secret "TYLER_PASSWORD"
    When I tap to continue
    Then I see the phrase "Admin Tasks"