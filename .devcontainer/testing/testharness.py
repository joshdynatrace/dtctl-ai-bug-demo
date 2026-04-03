import subprocess
import os, threading
from helpers import *

# TODO: Please read
# This is a semi "undocumented" token
# If you're running E2E tests, make sure to define a Dynatrace API token
# with `apiTokens.write` permissions
# This token will be used in helpers.py/create_dt_api_token to create other short-lived tokens
# These other tokens will correctly scoped (you pass the scopes to this function) and the tokens are only for 1 day.
# TLDR:
# 1. export DT_API_TOKEN_TESTING=dt0c01.****.****
# 2. Start up codespace
DT_API_TOKEN_TESTING = os.getenv("DT_API_TOKEN_TESTING","")

# Use the main token
# To create short lived tokens
# To run the test harness
# Use these short-lived tokens during the test harness.
DT_TENANT_APPS, DT_TENANT_LIVE = build_dt_urls(dt_env_id=DT_ENVIRONMENT_ID, dt_env_type=DT_ENVIRONMENT_TYPE)
DT_API_TOKEN_TO_USE = create_dt_api_token(token_name="[devrel e2e testing] DT_SYSLOG_E2E_TEST_TOKEN", scopes=["logs.ingest"], dt_rw_api_token=DT_API_TOKEN_TESTING, dt_tenant_live=DT_TENANT_LIVE)
store_env_var(key="DT_API_TOKEN", value=DT_API_TOKEN_TO_USE)

steps = get_steps(f"/workspaces/{REPOSITORY_NAME}/.devcontainer/testing/steps.txt")
INSTALL_PLAYWRIGHT_BROWSERS = False

def run_command_in_background(step):
    # first, check whether snippet even exists
    # if it does, this will return with a returncode=0
    # it the snippet doesn't exity, returncode=1
    output = ["runme", "print", step]
    if output.returncode != 0:
        logger.error(f"e2e test failed. Must send alert: {step} {output}")
        payload = payload = {
            "specversion": "1.0",
            "id": "1",
            "source": f"github.com/{GITHUB_REPOSITORY}",
            "type": "e2e.test.failed",
            "data": {
                "step": step,
                "output.stdout": output.stdout,
                "output.stderr": output.stderr,
                "message": "Command not found. Please check steps.txt to ensure your command exists and is named correctly."
            }
        }
        send_business_event(dt_tenant_live=DT_TENANT_LIVE, dt_rw_api_token=DT_API_TOKEN_TESTING, content_json=payload)
        exit("Command not found. Please check steps.txt to ensure your command exists and is named correctly.")
    command = ["runme", "run", step]
    with open("nohup.out", "w") as f:
        subprocess.Popen(["nohup"] + command, stdout=f, stderr=f)

# Installing Browsers for Playwright is a time consuming task
# So only install if we need to
# That means if running in non-dev mode (dev mode assumes the person already has everything installed)
# AND the steps file actually contains a playwright test (no point otherwise!)
if DEV_MODE == "FALSE":
    for step in steps:
        if "test_" in step:
            INSTALL_PLAYWRIGHT_BROWSERS = True

if INSTALL_PLAYWRIGHT_BROWSERS:
    subprocess.run(["playwright", "install", "chromium-headless-shell", "--only-shell", "--with-deps"])

for step in steps:
    step = step.strip()
    logger.info(f"Running {step}")

    if step.startswith("//") or step.startswith("#"):
        logger.info(f"[{step}] Ignore this step. It is commented out.")
        continue
    
    if "test_" in step:
        logger.info(f"[{step}] This step is a Playwright test.")
        if DEV_MODE == "FALSE": # Standard mode. Run test headlessly
            output = subprocess.run(["pytest", "--capture=no", f"{TESTING_BASE_DIR}/{step}"], capture_output=True, text=True)
        else: # Interactive mode (when a maintainer is improving testing. Spin up the browser visually.
            output = subprocess.run(["pytest", "--capture=no", "--headed", f"{TESTING_BASE_DIR}/{step}"], capture_output=True, text=True)

        if output.returncode != 0 and DEV_MODE == "FALSE":
            logger.error(f"e2e test failed. Must send alert: {step} {output}")
            payload = payload = {
                "specversion": "1.0",
                "id": "1",
                "source": f"github.com/{GITHUB_REPOSITORY}",
                "type": "e2e.test.failed",
                "data": {
                    "step": step,
                    "output.stdout": output.stdout,
                    "output.stderr": output.stderr
                }
            }
            send_business_event(dt_tenant_live=DT_TENANT_LIVE, dt_rw_api_token=DT_API_TOKEN_TESTING, content_json=payload)
            #create_github_issue(output, step_name=step)
        else:
            logger.info(output)
    else:
        # first, check whether snippet even exists
        # if it does, this will return with a returncode=0
        # it the snippet doesn't exity, returncode=1
        output = ["runme", "print", step]
        if output.returncode != 0:
            payload = payload = {
                "specversion": "1.0",
                "id": "1",
                "source": f"github.com/{GITHUB_REPOSITORY}",
                "type": "e2e.test.failed",
                "data": {
                    "step": step,
                    "output.stdout": output.stdout,
                    "output.stderr": output.stderr,
                    "message": "Command not found. Please check steps.txt to ensure your command exists and is named correctly."
                }
            }
            send_business_event(dt_tenant_live=DT_TENANT_LIVE, dt_rw_api_token=DT_API_TOKEN_TESTING, content_json=payload)
            exit("Command not found. Please check steps.txt to ensure your command exists and is named correctly.")

        command = ["runme", "run", step]

        # If task should be run in background
        # TODO: This is tech debt
        # and should be refactored when
        # runme beta run supports backgrounding
        if "[background]" in step:
            # Run the command in the background and capture the output
            # Create a thread to run the command
            thread = threading.Thread(target=run_command_in_background, args=(step,))
            thread.start()
        else:    
            output = subprocess.run(command, capture_output=True, text=True)
            logger.info(output)
            if output.returncode != 0 and DEV_MODE == "FALSE":
                logger.error(f"e2e test failed. Must send alert: {step} {output}")
                payload = payload = {
                    "specversion": "1.0",
                    "id": "1",
                    "source": f"github.com/{GITHUB_REPOSITORY}",
                    "type": "e2e.test.failed",
                    "data": {
                        "step": step,
                        "output.stdout": output.stdout,
                        "output.stderr": output.stderr
                    }
                }
                send_business_event(dt_tenant_live=DT_TENANT_LIVE, dt_rw_api_token=DT_API_TOKEN_TESTING, content_json=payload)
            else:
                logger.info(output)
