Feature: Web Crawler

  As a command-line user
  I want to run a Python application
  So that I can crawl a specific website
  And see the URLs of each page and the links found on them within the same domain.

  Scenario: Crawl a local website and list internal links
    Given I have a base URL for a website
    When I run the web crawler with the base URL
    Then I should see a report of the URLs of each page and the links found on them within the same domain
    And no external site was visited
