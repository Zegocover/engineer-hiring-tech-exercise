# python-developer-test

# Setup the Virtual Environment

Create the virtual environment.

```bash
pyenv install 3.13.5
pyenv local 3.13.5
pyenv virtualenv 3.13.5 url-crawler
pyenv activate url-crawler
```

## Install Dependencies

This will install any required pacakges. Re-run this command if dependencies change.

```bash
pip install -r requirements.txt
```

## Run

```bash
python src\__main__.py https://www.zego.com/ --log=error --use-cache
```

## Test

```bash
python
```

# Notes
IDE: VSCode
AI: Copilot

Added a lot of notes within the code, but here's a high level explanation of my approach:

The first step was to solve the problem, so I focused on having a working solution before starting working on performance, more about it below.

Created a module with a main crawler class that contains the business logic. The class is also composed (by dependency injection) with an http retriever and a html parser.

Added some basic logging as well as some caching to exemplify the advantages of having a separate class that downloads the html.

The CLI piece is a concrete client of the module and was built with argparse.

## Performance

For the performance side concurrency is the clear path. While python is single threaded and bound to the GLI, a multi-threaded solution actually has a performance advantage due to the IO blocking nature of the downloads, in contrast to cpu intensive tasks.

There are a lot of ways to approach concurrency in python, asyncio with async and await functions, multithreading and multiprocessing.

I chose a thread pool with consumers of a shared queue. Choose this because asyncio may be the most common implementation out there, so I figured I could show a less common implementation.

Added unit and integration tests.