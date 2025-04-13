## Project Notes

- **Initial Brief Analysis:** The initial review of the project brief suggests a relatively straightforward implementation. However, anticipated complexities, particularly surrounding asynchronous operations with `asyncio`, are hinted at within the project's README documentation.

- **Repository Setup:** The project repository has been initialized with foundational elements:
    - **Dependency Management:** Poetry has been configured for managing project dependencies.
    - **Code Formatting and Linting:** Ruff has been integrated to enforce code style and identify potential issues.
    - **Type Checking:** Pyre is being utilized for static type analysis.
    - **Testing Frameworks:** Pytest and Pytest-BDD have been selected for unit and behavior-driven development, respectively. `pytest-asyncio` is expected to be incorporated for asynchronous testing.
    - **Task Runner:** Invoke has been implemented as the project's task runner.

- **Initial Test Implementation:**
    - An initial feature file was generated using Gemini based on the "The test" section of the README.
    - A preliminary test was created, currently failing, to establish the testing infrastructure. Subsequent development will focus on building the test based on the expected happy path.

- **BDD Test Stubs:**
    - The initial feature file's verbosity was deemed excessive for a simple fixture comparison, leading to potential complexity.
    - Stubbed step definitions were implemented to validate the integrity of the BDD testing framework.

- **Fleshing Out First BDD Tests:**
    - BDD tests are being developed to reflect anticipated user interactions with the application.
    - A local static site is being served using Caddy and Docker Compose, with a corresponding Pytest fixture created for testing purposes.
    - A module with hardcoded responses has been implemented to facilitate the initial passing of BDD tests, allowing for iterative implementation of core logic.

- **Crawler Class Implementation:**
    - A `Crawler` class is being developed to abstract the intricacies of underlying components.
    - A unit test for the `Crawler` class has been implemented, utilizing a hardcoded response. The application's hardcoded response has been replaced with the output from the `Crawler` class.
    - `pytest-asyncio` has been added to the project. Asynchronous methods are being adopted in anticipation of future requirements.
    - The `tasks.py` collection has been updated to include `unit` and `test` tasks.

- **Crawler Class Implementation Details:**
    - The implementation of the `Crawler` class is proceeding with a focus on dependency injection to enable iterative development, starting with a mocked version of dependent objects. This has temporarily resulted in BDD test failures, which will be addressed by developing a hardcoded parser class in the next iteration.
    - Mock parser and fetcher classes, returning hardcoded responses, were implemented to facilitate the development of the core `Crawler` logic, allowing focus on asynchronous behavior within the happy path.
    - The `Crawler` class now exhibits the expected functionality.

- **Fetcher Class Development:**
    - Tests have been written for the `Fetcher` class to cover scenarios involving 404 and 500 status codes, as well as general exceptions during fetch operations.
    - The website fixture has been enhanced to simulate redirects to 404 and 500 error pages as required by the tests.
    - The website fixture has been relocated to the `tests` folder to enable its utilization by both unit and BDD tests.

- **Bug Fix: Premature Task Termination:**
    - An identified bug involved the Parser potentially causing early termination of fetcher tasks, leading to incomplete reporting of results.
    - This issue was resolved by ensuring the Parser waits for the fetcher queue to be `joined()` (empty) before assessing the completion of the workload.

- **Bug Fix: Asynchronous Result Ordering:**
    - Asynchronous operations did not guarantee the order of results in the final report.
    - To address this, the report results are now sorted before being passed to the application. The primary requirement is the presence of results, not their retrieval order.

- **Parser Class Development:**
    - A basic unit test for link parsing on a web page was created, and Gemini was used to generate an initial `Parser` class implementation to pass this test.
    - The initial implementation, while functional, failed static code analysis. After iterative refinement with Gemini, a working but suboptimal solution was produced.
    - The working solution has been refactored into the `Parser` class. Additional use cases will be incorporated over time.

- **External Site Test Case:**
    - The first BDD test case involving external sites is being addressed through the development of a URL filtering system, again employing adversarial TDD with Gemini.
    - Progress has been efficient, with significant development enabled by the test-driven approach.
    - Log analysis has been implemented to verify that external sites are not accessed during testing.

- **BDD Test Refinement:**
    - A significant portion of the BDD test cases initially suggested by Gemini were deemed more appropriate as unit-level tests and have been integrated accordingly.

- **Parser Enhancement:**
    - The `Parser` class has been updated to identify image sources (`src` attributes of `<img>` tags) and link sources (`href` attributes of `<a>` and `<link>` tags). Achieving linting compliance required iterative refinement with Gemini.

- **Fetcher Enhancement:**
    - The `Fetcher` class has been enhanced to perform content type checking. It now sends a HEAD request to inspect the `Content-Type` header and proceeds with the full download only if the content type indicates a text-based resource.

- **Note on Note Tidy-Up:** These notes have been tidied and formatted for clarity with the assistance of the Gemini LLM, maintaining the original voice and intent.