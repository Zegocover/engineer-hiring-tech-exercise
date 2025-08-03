# python-developer-test

# Local Development

Create the virtual environment.

```bash
pyenv install 3.13.5
pyenv local 3.13.5
pyenv virtualenv 3.13.5 url-crawler
pyenv activate url-crawler
```

## Install Dependencies

This will install any required packages. Re-run this command if dependencies change.

```bash
pip install -r requirements.dev
```

## Run

```bash
python src\__main__.py https://www.zego.com/ --log=error --cache
```

## Test

```bash
python
```

## Lint

```bash
black .
```

# Test Notes
IDE: VSCode
AI: Copilot

Added a lot of notes within the code, but here's a high level explanation of my approach:

The first step was to solve the problem (First Commit), so I focused on having a working solution before starting working on performance.

Created a module with a main crawler class that contains the business logic. The class is also composed (by dependency injection) with an http retriever and a html parser.

Added some basic logging as well as some caching as an hypothetical scenario to exemplify the advantages of having a separate class that downloads the html (Plus it was useful while developing).

The CLI piece is a concrete client of the urlparser module, uses standard argparse.

## Performance

To improve performance: concurrency, more specifically multi-threading. While python is single threaded and bound to the GLI, a multi-threaded solution actually has a performance advantage in this case due to the IO blocking nature of the downloads. In comparison a multi-process approach is prefered for CPU intensive tasks.

There are a lot of ways to approach multithreading in python. asyncio with async and await functions is probably the most common. I chose a thread pool with consumers of a shared queue instead, as I figured I could showcase some less AI, less common implementation.

## Tests

Added unit and integration tests.