Feature: Example Test
    As a user
    I want to test the example functionality
    So that I can verify the BDD setup works correctly

    Scenario: Navigate to example.com
        Given I open the browser
        When I navigate to "https://example.com"
        Then I should see the page title "Example Domain"
