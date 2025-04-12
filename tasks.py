from invoke import task


@task
def format(c):
    c.run("ruff format .")


@task
def lint(c):
    c.run("ruff check --fix --select=I")


@task
def type_check(c):
    c.run("pyre")


@task()
def static(c):
    format(c)
    lint(c)
    type_check(c)


@task()
def bdd(c):
    c.run("pytest tests/bdd")
