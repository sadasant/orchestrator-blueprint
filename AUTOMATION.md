# Repository wake automation

> **Brief:** One local watcher scans committed input, records messages for each
> recipient, and sends fixed locators to registered tmux panes. Root and peers
> publish replies through the same protocol.

## Boundary

The watcher fetches the configured remote branch, parses changed Markdown,
persists recipient events and a scan cursor together, validates exact pane
registrations, and submits fixed locators. It retries pending delivery even
when the remote head is unchanged. It does not check out or execute fetched
files, start harnesses, edit repository files, commit, push, or issue credentials.

Follow [the agent protocol][agents] for initialization, transition from an older
instance, addressing, replies, and recovery. Scanning, submission, and verified
reply publication are separate states; a scan cursor is never proof of completion.

## Local state

The default namespace uses the main checkout's basename, shared by its worktrees:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/<repository-name>/
  agent-channel.json
  panes/
    orchestrator
    billing
  run.lock/
```

The ledger retains pending messages and publication receipts. Registrations bind
pane ID, pane PID, TTY, current command, session ID, window ID, declared harness,
and a marker identifying the repository and agent. Re-register after a change.
No pane contents or credentials belong in these files.

## Registration and validation

Once the intended CLI is ready, register its exact pane. The default agent name
is `orchestrator`; `-a AGENT` selects any other recipient:

```sh
scripts/orchestrator-wake.sh -a orchestrator register PANE HARNESS
scripts/orchestrator-wake.sh -a orchestrator status
scripts/orchestrator-wake.sh -a orchestrator dry-run MESSAGE_ID COMMIT
```

The dry run validates the same 32-character message ID, 40-character commit SHA,
and registration as delivery, then prints the locator without typing it. The
leading `#` in a locator makes accidental delivery to an empty shell a comment;
exact registration is still required. `unregister` disables that recipient's
delivery, leaving its messages pending.

## Watcher lifecycle

Verify non-interactive Git authentication, review the starting commit, and run:

```sh
GIT_TERMINAL_PROMPT=0 git ls-remote origin refs/heads/main
scripts/agent-channel.py initialize BASE_SHA
scripts/watch-remote.sh
scripts/install-watcher.sh
```

Initialization is performed once; existing ledgers must be retained. On macOS,
installation generates and loads a user LaunchAgent. On Linux with systemd it
generates and enables a user service and timer. Generated launchers and logs stay
outside Git. Installation and reviewed script deployment are explicit operator
actions. Reply acknowledgement belongs to `agent-channel.py acknowledge`, for
every recipient, after verified publication under the writer lease.

[agents]: ./AGENT-PROTOCOL.md
