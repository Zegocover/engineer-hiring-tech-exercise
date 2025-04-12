Feature: Web Crawler

  As a command-line user
  I want to run a Python application
  So that I can crawl a specific website
  And see the URLs of each page and the links found on them within the same domain.

  Scenario: Crawl a local website and list internal links
    Given I have a base URL for a website
    When I run the web crawler with the base URL
    Then I should see a report of the URLs of each page and the links found on them within the same domain

  Scenario: Ignore external links from localhost
    Given I have a base URL "http://localhost:8888"
    And a page on "http://localhost:8888" contains a link to "https://www.external.com"
    When I run the web crawler with the base URL
    Then it should not print any links with a different domain than "localhost"

  Scenario: Handle different URL schemes (HTTP and HTTPS) on localhost
    Given I have a base URL "http://localhost:8888"
    When I run the web crawler with the base URL
    Then it should process both "http" and "https" versions of internal links on localhost

  Scenario: Prevent infinite loops by tracking visited URLs on localhost
    Given I have a base URL "http://localhost:8888/page1" with a link back to itself
    When I run the web crawler with the base URL
    Then it should process "http://localhost:8888/page1" only once

  Scenario: Handle relative URLs correctly on localhost
    Given I have a base URL "http://localhost:8888/section/"
    And a page at "http://localhost:8888/section/page2" with a relative link "/anotherpage"
    When the crawler processes "http://localhost:8888/section/page2"
    Then it should identify the link as "http://localhost:8888/anotherpage"

  Scenario: Gracefully handle network errors on localhost (if server is down)
    Given I have a base URL "http://localhost:8888"
    And no server is running on that address
    When I run the web crawler with the base URL
    Then it should report that the base URL could not be accessed
    And it should exit gracefully

  Scenario: Handle pages with no links on localhost
    Given I have a base URL "http://localhost:8888/empty-page" with no links
    When the crawler processes "http://localhost:8888/empty-page"
    Then it should print the URL "http://localhost:8888/empty-page"
    And it should not print any links for that page