# Codespaces

--8<-- "snippets/bizevent-codespaces.js"

GitHub Codespaces gives you a fully configured cloud development environment — Kind cluster, Arc Store, and all tooling pre-installed — without any local setup.

---

## 1. Launch Codespace

Click the badge below to open a new Codespace from the `main` branch:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/joshdynatrace/dtctl-ai-bug-demo){target="_blank"}

---

## 2. Codespace Configuration

!!! tip "Machine sizing & secrets"
    **Machine type**

    Select **4-core** for enough resources to run the Kind cluster and all Arc Store services.

    **Secrets** — enter your credentials in the following Codespace secrets before launching:

    | Secret | Description |
    |--------|-------------|
    | `DT_ENVIRONMENT_ID` | Your Dynatrace environment ID, e.g. `abc12345` from `https://abc12345.live.dynatrace.com` |
    | `DT_ENVIRONMENT_TYPE` | Your environment type: `live`, `sprint`, or `dev`. If unsure, use `live`. |
    | `DT_API_TOKEN` | Dynatrace Operator token — used to manage Dynatrace components in the Kubernetes cluster |
    | `DT_DATA_INGEST_TOKEN` | Dynatrace data ingest token — used to send logs, metrics, and traces |

---

## 3. What Gets Deployed

Once the Codespace finishes initialising, the following is ready for you:

- A local **Kind** Kubernetes cluster
- The **Arc Store** frontend, backend, and load generator — deployed to the `arc-store` namespace
- The Dynatrace OneAgent

The load generator starts automatically and produces continuous traffic against the Arc Store, which will eventually trigger an error calling the tax service.

---

## 4. Troubleshooting

### Exposing the Arc Frontend locally

Make sure to run:

```bash
nohup kubectl port-forward svc/arc-frontend 3000:80 -n arc-store > /tmp/arc-frontend-port-forward.log 2>&1 &
```

### Cluster health

Confirm the Kind cluster is running:

```bash
kubectl cluster-info
```

### Pod status

Check that all Arc Store services are up:

```bash
kubectl get pods -n arc-store
```

All pods should show `Running`. If any are in `CrashLoopBackOff` or `Pending`, check the logs:

```bash
kubectl logs -f deployment/<pod-name> -n arc-store
```

<div class="grid cards" markdown>
- [Phase 1: Detection :octicons-arrow-right-24:](phase-1-detection.md)
</div>
