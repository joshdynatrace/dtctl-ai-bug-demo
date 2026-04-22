--8<-- "snippets/bizevent-cleanup.js"

# Cleanup

To remove the Arc Store from your cluster:

```bash
kubectl delete -f k8s/
```

To delete the Kind cluster entirely:

```bash
kind delete cluster
```

### Dynatrace

Deactivate or delete the API tokens you created in your Dynatrace tenant:

- Navigate to **Settings → Integration → Dynatrace API**
- Find the tokens named for this demo and delete or revoke them

### Anthropic

If you no longer need the Anthropic API key used for this demo, revoke it at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys){target=_blank}.

--8<-- "snippets/feedback-invitation.md"

<div class="grid cards" markdown>
- [What's Next? :octicons-arrow-right-24:](whats-next.md)
</div>
