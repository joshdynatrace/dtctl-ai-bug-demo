---
name: live-debug
description: Investigate a bug using the Dynatrace Live Debugger via dtctl — set breakpoints, capture snapshots, and produce a root-cause summary with concrete variable-value evidence. Use this skill whenever the user says "debug", "investigate", "set a breakpoint", "capture a snapshot", "live debugger", "use dtctl to debug", or asks to trace a runtime error in the running application.
---

Investigate a bug using the Dynatrace Live Debugger via dtctl.

Target: $ARGUMENTS

## Playbook

Follow these steps in order. Use dtctl in agent mode (`--agent` or `-A`) throughout so outputs are structured and machine-parseable.

1. **Bootstrap** — run the dtctl command catalog first. Only use commands and flags that appear in the catalog output.

2. **Parse the stack trace** — extract file paths and line numbers from the issue or error. Map each frame to a candidate breakpoint target.

3. **Set a namespace filter** before placing any breakpoints. Example:
   ```
   dtctl update breakpoint --filters k8s.namespace.name:arc-store
   ```

4. **Verify target entities** — confirm the target service/deployment exists and note its exact identifier before setting breakpoints.

5. **Set breakpoints** using the full repository-relative file path and line number. Example:
   ```
   dtctl create breakpoint backend/src/main/java/com/arcstore/service/OrderService.java:40
   ```
   For a NullPointerException, set the breakpoint one executable line *before* the exception occurs.

6. **Add breakpoints in priority order** — top failing frame first, then one upstream caller frame if needed.

7. **Capture snapshots** — wait for at least one failing execution to hit the breakpoint and collect local variable values, method inputs, and return values.

8. **Query snapshot data** in full detail. Example:
   ```
   dtctl query "fetch application.snapshots | sort timestamp desc | limit 5" --decode-snapshots=full -o json
   ```
   Explicitly highlight any null values and the object path that produced the null dereference.

9. **Remove temporary breakpoints** after evidence collection.

10. **Corroborate** — cross-check snapshot evidence against logs or traces for the same failing request path and time window.

11. **Report** — produce a root-cause summary including:
    - At least one concrete variable-value proof from a Live Debugger snapshot
    - The stack frame and method context where the null was observed
    - One log or trace corroboration matching the same request path/time window
    - A minimal, low-risk fix recommendation
