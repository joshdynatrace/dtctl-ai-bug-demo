# Codespace template for a Kubernetes stack

> Stuck? Email devrel@dynatrace.com and we can help.

Use this template to bootstrap your Kubernetes-based hands on cloud environment.

Includes a documentation stack (mkdocs) in the `docs` folder and full end-to-end testing suite.

## Installing docstack

```
pip install -r docs/requirements.txt
```

Start docs:

```
mkdocs serve -a localhost:8000
# or python -m mkdocs serve -a localhost:8000
```

### Usage Tracking

There are two places you will most likely want to track usage:

1. When the demo is spun up
2. For each documentation page (tracking whether docs are actually used or people are getting stuck)

#### 1. Demo Spin Up

![image](https://github.com/user-attachments/assets/db890cae-67d7-4943-a2ba-01afdd01982c)

After the system spins up, the [postCreateCommand](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/.devcontainer/devcontainer.json#L42) is fired. It is up to you to code logic to fire a log / metric / bizevent to Dynatrace to signal the demo has started.

[Here is an example](https://github.com/Dynatrace/obslab-release-validation/blob/main/utils.py#L386) of sending a bizevent at startup (the utils method is triggered from [environment_installer.py](https://github.com/Dynatrace/obslab-release-validation/blob/main/environment_installer.py) which itself is triggered from the [postCreateCommand](https://github.com/Dynatrace/obslab-release-validation/blob/main/.devcontainer/devcontainer.json#L47)) to Dynatrace via a Lambda function (so that the codespace doesn't need an API token to send this bizevent).

### 2. Documentation Usage

![image](https://github.com/user-attachments/assets/ee925d40-2a3c-440f-9373-ef11015243e8)

When you run `mkdocs gh-deploy`, the docs are automatically built, pushed and hosted at a GitHub pages domain (like [this](https://dynatrace.github.io/obslab-syslog)).
You will need to create a Dynatrace agentless application and replace the dummy snippet in [this file](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/docs/overrides/main.html#L10).

Next, you will use the `dynatrace.sendBizEvent` Javascript method to fire a single event on each page load.
Do this by [including a snippet on each markdown page](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/docs/index.md?plain=1#L5) (we have given some sample snippets, but you may need to create more). These snippets live in this folder.

Don't forget to rebuild and push your docs: `mkdocs gh-deploy`

## 3. End to End Testing Mode

This repo template comes with a full test suite. First ensure you've named your YAML snippets in the markdown docs, like [this](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/docs/getting-started.md?plain=1#L8-L10).

Use those names to populate [steps.txt](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/.devcontainer/testing/steps.txt) to fill out your e2e test. Be sure to update [test_dynatrace_ui.py](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/.devcontainer/testing/test_dynatrace_ui.py) and add it as a step (after you send data to Dynatrace, you need to test that the data makes it into the UI and is visualised correctly. In this case, [steps.txt](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/.devcontainer/testing/steps.txt) may look like this:

```
send log to collector
test_dynatrace_ui.py
```

You can test this e2e test locally (and by showing the browser for visual debugging) like this. [testharness.py](https://github.com/Dynatrace/demo-kubernetes-template/blob/main/.devcontainer/testing/testharness.py) will read steps.txt and run the steps in order.

```
cd .devcontainer/testing

# Create a Dynatrace API token with apiTokens.write permissions
# testharness.py contains logic to create temporary (1 day) tokens for any capabilities you need (see comments in testharness.py)
export DT_API_TOKEN_TESTING=dt0c01.***.***
# Enable debug mode (shows the browser visually)
export DEV_MODE=true
# Install the testing requirements and frameworks
pip install -r requirements.txt
# Install the browser binaries playwright needs to run
playwright install chromium-headless-shell --only-shell --with-deps
# Trigger the test harness
python testharness.py
```

### Automating the tests
When you're happy with your test harness, it's time to run it on a schedule. We can leverage Dynatrace workflows to trigger the creation of a GitHub codespace.
The logic in [environment_installer.py](https://github.com/Dynatrace/demo-kubernetes-template/blob/0d95ea5ae9186137dd290943df5a3c362dbf2ea6/environment_installer.py#L29) will run in "test mode"
when the codespace name starts with `dttest-`. Here's a sample DT workflow to achieve this:

<img width="470" height="557" alt="image" src="https://github.com/user-attachments/assets/bb611686-a758-43ae-ad41-e95d972a3124" />

```
import { execution } from '@dynatrace-sdk/automation-utils';
import { credentialVaultClient } from '@dynatrace-sdk/client-classic-environment-v2';

export default async function ({ execution_id }) {

  /*
   * Define repo
   * This assume you've forked the repo into your own account to run the e2e nightly tests
  */
  const repoName = "agardnerit/obslab-jmeter";

  /* Create a GitHub fine grained PAT with: "Codespaces (rw)" and mandatory "Metadata" (r) permissions
   * This PAT will be used to spin up the codespace
   * Store it in Dynatrace credentials vault
   * Retrieve credential from DT Vault
   */
  const tokenCredentials = await credentialVaultClient.getCredentialsDetails({
    id: 'CREDENTIALS_VAULT-*************'
  });

  /* Standard machines available are:
   * - basicLinux32gb (2 core)
   * - standardLinux32gb (4 core)
   *
   * Rename your codespace as you like, but it MUST start with dttest-
   */
  const payload = {
    "ref": "main",
    "machine": "basicLinux32gb",
    "display_name": "dttest-codespaceobslab-jmeter"
  }

  /*
   * Startup the codespace
   * This is fire and forget
   *
   * The codespace will self delete when the e2e test is complete.
   * See: https://github.com/Dynatrace/demo-kubernetes-template/blob/94b0315372ba8e9af64bf2da08e64a79457cac34/environment_installer.py#L34
   */
  const codespace_creation_result = await fetch("https://api.github.com/repos/" + repoName + "/codespaces", {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + tokenCredentials['token'],
      "X-GitHub-Api-Version": "2022-11-28"
    },
    body: JSON.stringify(payload),
  });

  console.log(codespace_creation_result);
  return codespace_creation_result;
}
```


### Getting Alerts for e2e test failures

If issues occur during the e2e test, you probably want to be notified. The [test harness](https://github.com/Dynatrace/demo-kubernetes-template/blob/9aeb088eda7026797e973f1f78fdfe6dfb012223/.devcontainer/testing/testharness.py#L144) will send a business event (bizevent) to your Dynatrace tenant when a failure occurs. Based on the payload you define, it will look like this:

```
{
  "specversion": "1.0",
  "id": "1",
  "source": f"github.com/you/yourRepo",
  "type": "e2e.test.failed",
  "data": {
    "step": step,
    "output.stdout": output.stdout,
    "output.stderr": output.stderr
  }
}
```

Then you can create a Dynatrace workflow to react to the incoming bizevent and send an email:

<img width="522" height="586" alt="image" src="https://github.com/user-attachments/assets/082eb4e9-d9aa-4cfc-ab0b-a7aee54219fa" />

