import subprocess

from pytest_bdd import when


@when("I run the web crawler with the base URL", target_fixture="crawler_report")
def action_run_crawler_on_base_url(website):
    process = subprocess.run(
        ["python", "-m", "crawlspace", website], capture_output=True
    )

    return process.stdout
