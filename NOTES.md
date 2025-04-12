- Initial study of the brief. Seems fairly straightforward but certain there will be some complexities around asyncio which the README is hinting at.
- Setup repo with some basics. 
    - Using Poetry for dependency management.
    - Ruff for formating and linting.
    - Trying out Pyre for typechecking.
    - Pytest and Pytest-BDD for testing frameworks. Will likely need pytest-asycio at some point.
    - Using invoke as a task runner

- Initial test
    - Add initial feature file by asking Gemini to generate a feature file based on the "The test" section of the README
    - Generate a test that runs but is red. Will build up the initial test using the happy path.
 
- Add stubs for BDD test
    - Feature file was a bit wordy and would mean a lot of faff for a simple comparison of a known fixture.
    - Implemented stub steps to check the BDD test infrastructure is correct.

- Flesh out first BDD tests with expectations of how the user will want to interact with the application.
    - Used caddy and docker compose to serve a basic static site then created a pytest fixture
    - Implemented a module with hardcoded responses to pass the BDD tests knowing I can fill in the pieces as I go.

- Implement Crawler class that will hide the complexity of the underlying pieces. 
    - Implemented a unit test for the class, hard code response and replace hard coded response from the application with return from crawler class.
    - Added `pytest-asyncio`. Have started with async methods as I can feel them coming in soon.
    - Updated tasks collection with `unit` ad `test`

- Start building the implementation details of the the Crawler class. I have opted for dependency injection so that I can start with a basic mocked version of the object and ubild it up. Consequently, I have vroken the BDD test but I can rectify that building a hardcoded parser class on my next iteration.