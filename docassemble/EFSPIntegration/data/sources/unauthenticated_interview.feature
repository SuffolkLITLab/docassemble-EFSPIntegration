@interviews_start
Feature: The unauthenticated interview starts without erroring

  @ui1 @unauthenticated
  Scenario: unauthenticated_interview.yml starts
    Given I start the interview at "unauthenticated_interview.yml"
    And the maximum seconds for each Step in this Scenario is 15