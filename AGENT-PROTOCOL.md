# Agent workspaces and correspondence

> **Brief:** Give each active agent its own worktree and register its running
> CLI in tmux. Changed Markdown can address that agent. Replies belong in the
> shared repository; delivery and completion are tracked separately so an
> unavailable session does not silently lose work.

## One correspondence system

This implements the [shared kernel][kernel]. Root and peers use the same
routing, delivery, and acknowledgement protocol. The channel uses ordinary configured
Git authentication; it does not implement the proposed guarded credential
interface or issue credentials. Linked worktrees share Git configuration and may
inherit configured authentication. They isolate files and indexes, not account
access; apply the instance's credential policy before launching an agent.

The current root is addressed as `orchestrator`. Peer names come from
[sub-agents/active.md][active], using the existing six-column table, a lowercase
name, literal comma-separated relative owned paths, and State `active`. The
root name is reserved. A role row gives a name meaning; local pane registration
makes the current instance reachable. Neither supplies credentials.

## Give an agent a worktree

Publish the peer's role and active authority row first. Then run:

```sh
scripts/agent-channel.py worktree billing
```

The command acquires the repository writer lease, fetches the configured branch,
creates an adjacent agent worktree on `agents/billing`, and prints its path.
It preserves an existing branch and refuses a mismatched worktree. Custom hooks
require explicit composition before automatic setup proceeds.

The root also uses `worktree orchestrator`. Each generated worktree has its own `orchestrator.agent` Git setting
and prepare-commit-msg hook. Ordinary commits receive an `Orchestrator-Agent`
trailer automatically. A shared main checkout keeps its existing identity and
hooks. Do not remove the agent trailer: it distinguishes ordinary agent work
from collaborator input. It is a routing convention, not authentication.

Run the existing launcher with the printed worktree path and an active dossier,
or start the chosen CLI there manually. Launcher invocation remains:

```sh
scripts/launch-agent.sh billing HARNESS WORKTREE [MODEL] [EFFORT]
```

Once the CLI is ready to receive input, bind its exact pane:

```sh
scripts/orchestrator-wake.sh -a billing register PANE HARNESS
scripts/orchestrator-wake.sh -a billing status
```

Registration is explicit; the launcher does not guess when an unfamiliar CLI
is ready. Re-register after restarting or replacing the CLI. Pane identity
checks detect changed pane metadata, but cannot prove that a same-command child
process is still the same conversation. Direct tmux access remains available to
collaborators and peers through their existing terminal clients.

## Initialize and start polling

Every new channel requires an explicit starting commit. Fetch the configured
branch, review existing work, and select the full SHA through which no work
needs to be routed. Later commits will be scanned on the first poll:

```sh
scripts/agent-channel.py initialize BASE_SHA
scripts/watch-remote.sh
scripts/install-watcher.sh
```

Use the current fetched head for a fresh instance only after reviewing it. The
initializer verifies that the base belongs to the configured remote history and
refuses to overwrite an existing ledger. Polling without initialization fails;
it never silently treats the latest head as handled.

Polls route new commits and retry definitely undelivered messages, including
when the remote head has not changed. The watcher fetches objects but never
checks out or executes newly fetched code. Deploy reviewed script updates
explicitly; merging an implementation does not activate a running instance.

## Transition an existing instance

1. Stop its scheduled watcher and finish or pause active publication under the
   writer lease. Back up local runtime state, including pending receipts, before
   updating the reviewed scripts. Keep the backup outside Git.
2. Inspect unfinished root work and any published response. In the old state,
   `processed-head` records handled work; `notified-head` only records a notice
   submitted to a pane. Never use the latter as proof of completion. Resolve
   an already submitted turn before replaying its input, so external actions
   are not repeated merely because transport changed.
3. If `agent-channel.json` already exists, retain it unchanged: its cursor and
   every pending, sent, uncertain, or acknowledged event remain in use. Do not
   reinitialize. Otherwise choose the last actually reconciled commit and run
   `initialize BASE_SHA`. Unhandled commits after that base become durable
   messages on the next poll. The old receipt files are left intact for review;
   the running channel neither reads nor updates them.
4. Re-register every running CLI, including root, using `-a AGENT register`.
   All registrations now live in `panes/AGENT` and use the same agent marker.
   An old `root-pane` file is not a usable registration. Keep agent worktrees
   intact and update their reviewed scripts and role instructions as needed.
5. Inspect `status`, run a manual poll, and verify pending messages and pane
   targets. Reinstall the scheduler to replace its generated launcher. Record
   the chosen base or retained ledger and unresolved work in the operator trail.

There is no routing-mode switch or root-only fallback. Root remains addressed
as `orchestrator`; its role determines what it does with the same kind of message.

## What addresses someone

- A collaborator's added mention outside fenced examples, indented code, or
  tables addresses that name. Unknown names route to root for inspection.
- An agent addresses a peer by opening a paragraph with its name, for example
  `@billing please inspect this finding`. Wrapped continuations do not address.
- A change confined to one peer's owned paths reaches that peer. Its own work
  does not wake it. Unaddressed collaborator changes elsewhere reach root;
  unaddressed agent work elsewhere stays silent.
- Several mentions of one recipient in a commit produce one message. Self
  mentions, unknown agent-author trailers, and `_unread/`-only changes do not
  create ordinary collaborator wakes.
- The sixth message from one agent to the same peer within an hour goes to root
  for inspection. Other pairs remain independent.

The scanner follows first-parent history, so a merge's net changes are considered
once, under that merge commit's attribution. An `Orchestrator-Agent` trailer can
be forged by a repository writer; this channel is not a sender-authentication
system. Receiving a notice does not broaden the recipient's role or permissions.

## Receive and reply

The terminal receives only a fixed locator:

```text
# orchestrator-message MESSAGE_ID COMMIT for AGENT: ...
```

Validate the 32-character lowercase hexadecimal message ID and the 40-character
commit SHA. In the intended repository, inspect the durable envelope:

```sh
scripts/agent-channel.py show MESSAGE_ID
```

Check its recipient and commit against the notice. Read the complete committed
files named by the envelope, including their authority boundaries, before acting.
A locator is not the instruction itself. Check for an existing reply before
repeating work after a retry.

Draft in your own worktree. Reply beside the question, or link there to the
canonical result. Commit the staged reply with its message ID:

```sh
git commit -m 'Answer the repository question' \
  --trailer 'Orchestrator-Reply-To: MESSAGE_ID'
```

At publication, acquire the shared writer lease, fetch, and rebase onto the
configured remote branch. Preserve concurrent input; a conflict needs semantic
reconciliation, not deletion of the other party's work. Push normally and
inspect the actual hosted branch head. Once the reply is included in both local
history and the fetched remote branch, acknowledge under the same lease:

```sh
scripts/agent-channel.py --lease-held acknowledge MESSAGE_ID RESPONSE_SHA
scripts/orchestrator-lock.sh release
```

Acknowledgement requires the reply commit to descend from the triggering commit,
carry the matching agent and reply trailers, and be included in local and fetched
remote history. The receipt records the observed remote head separately, allowing
another writer's subsequent commit to remain intact. It is a publication receipt,
not an automated judgment of answer quality. Ordinary instance correspondence may publish directly
to its agreed shared branch; changes to Blueprint go through pull requests.

## Inspect and recover

```sh
scripts/agent-channel.py status
scripts/agent-channel.py show MESSAGE_ID
```

| Status | Meaning | Next action |
| --- | --- | --- |
| pending | No submission succeeded; recipient may be unavailable | Repair registration; the next poll retries |
| sending | Submission began but no terminal result was recorded | A subsequent poll marks it uncertain |
| sent | tmux accepted the input operation | Wait for a repository reply; this is not proof of model reception |
| uncertain | Submission failed or was interrupted after it began | Inspect the session and existing replies before retrying |
| held | The pending recipient lost its active role | Review the assignment before reactivating or retrying |
| acknowledged | A matching reply was published and verified | Preserve the receipt |

After inspection, explicitly permit a new attempt:

```sh
scripts/agent-channel.py retry MESSAGE_ID
```

The next poll uses the same message ID. It may duplicate a prior submission;
recipients use the ID and existing reply to avoid repeating an external action.
No automatic retry is attempted after an ambiguous submission. A held message
also needs this explicit review even if the role is subsequently re-added.

State lives in a mode-0600 local agent-channel.json beside the existing runtime
state. Its scan cursor and per-recipient events are saved together before any
submission. The cursor means scanned, not answered. Missing recipients do not block other recipients,
and lease contention never authorizes deleting someone else's lock.

Pending work survives watcher restarts on this host. This first implementation
has one host-local delivery ledger; cross-host transfer, receipt pruning, and
credential brokering remain future work. Back up local state before migration.

[kernel]: ./proposals/shared-kernel.md
[active]: ./sub-agents/active.md
