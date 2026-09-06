# Repository wake automation

> **Brief:** A silent local watcher detects remote changes and sends one fixed
> SHA notice to an explicitly registered tmux pane. The root harness alone
> fetches, reconciles, publishes, verifies, and acknowledges work under the
> writer lease.

## Peer-routing mode

This document describes the default legacy root route. With
`ORCHESTRATOR_AGENT_ROUTING=1`, the watcher instead uses the [agent protocol][peers]:
it fetches objects, scans new commits, persists recipient events, and retries
pending delivery under the same writer lease. It does not advance the legacy
root checkpoint or check out fetched code. See that protocol before switching
an existing instance; its first poll establishes a new scan baseline.

## Boundary

The watcher:

- resolves the configured remote branch without fetching into the checkout;
- compares it with the last acknowledged checkpoint;
- validates one exact tmux pane registration;
- submits one fixed notice followed by the tmux Enter key;
- records only local SHA, pane, and status receipts.

It does not inspect changed content, execute remote files, start a root harness,
edit the repository, commit, push, or handle credentials.

## Fixed wake message

```text
# orchestrator-wake REMOTE after PREVIOUS: REMOTE_NAME/BRANCH advanced. Acquire
the repository writer lease, fetch the exact remote range, reconcile
collaborator input, record the operator trail, commit, fetch and rebase again,
push normally, verify the hosted head, acknowledge the checkpoint, and release
the lease.
```

The leading `#` makes accidental delivery to an ordinary empty shell prompt a
comment. Exact pane validation is still mandatory.

## Local state

By default, local state lives under:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/<repository-name>/
  processed-head
  notified-head
  root-pane
  run.lock/
  watcher.log
```

`processed-head` is the hosted response already handled by the root.
`notified-head` suppresses duplicate delivery of one pending remote head.
`root-pane` contains tmux identity and declared harness fields, never captured
pane content or credentials.

## Registration

Start the intended root harness inside tmux. From the same pane:

```sh
scripts/orchestrator-wake.sh register "$TMUX_PANE" HARNESS
scripts/orchestrator-wake.sh status
```

The registration binds pane ID, pane PID, TTY, current command, session ID,
window ID, harness name, and an exact tmux marker. If any observed identity
changes, delivery fails closed until explicit re-registration.

Exercise validation without typing into the pane:

```sh
scripts/orchestrator-wake.sh dry-run \
  0000000000000000000000000000000000000000 \
  1111111111111111111111111111111111111111
```

Disable delivery with:

```sh
scripts/orchestrator-wake.sh unregister
```

## Watcher lifecycle

First verify ordinary non-interactive Git authentication and initialize state:

```sh
GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/main
scripts/watch-remote.sh
```

Then install the host scheduler:

```sh
scripts/install-watcher.sh
```

On macOS this generates and loads a user LaunchAgent. On Linux with systemd it
generates and enables a user service and timer. Generated files contain local
paths and remain outside the repository.

After the root publishes and fetches the verified response head:

```sh
scripts/orchestrator-wake.sh acknowledge RESPONSE_HEAD
```

Acknowledgement requires local `HEAD` and the configured remote-tracking branch
to equal the supplied commit. Only then should the root release the writer
lease.

[peers]: ./AGENT-PROTOCOL.md
