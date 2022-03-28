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
    And I get to the question id "display case" with this data:
      | var | value | trigger |
      | trial_court | peoria | |
      | filling_interview_initial_or_existing | existing_case | |
      | do_what_choice | docket_lookup | |
      | docket_id_from_user | 22-AD-00005 | |
    And I see the phrase "IMPOUNDED ADOPTION"
    And I tap to continue
    And I get to the question id "Additional parties" with this data:
      | var | value | trigger |
      | user_ask_role | defendant | |
    Then I see the phrase "Are you adding any additional parties to this filing?"
