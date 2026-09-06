# Orchestrator Blueprint

> **Brief:** Orchestrator Blueprint combines Git and tmux into a portable,
> durable collaboration surface for AI agents. It runs on macOS and Linux,
> supports multiple terminal harnesses, and keeps authority, execution,
> decisions, wakes, and operator receipts inspectable.

This repository is a reproducible pattern for a persistent root Orchestrator.
Git holds durable working state. tmux holds live terminal sessions. Small local
scripts detect remote changes, route messages to explicitly registered panes, coordinate
shared publication, and preserve evidence of what happened.

The blueprint is harness-neutral. Codex, Claude Code, Pi, and Prime Agent are
included as adapters; another terminal harness can be added with one executable
adapter. A harness supplies the action loop. It does not own the repository's
identity, authority model, or durable state.

## What the blueprint provides

- A root-agent contract in `AGENTS.md` and a Claude Code bridge in `CLAUDE.md`.
- Decisions, questions, work charters, queues, and agent dossiers as Markdown.
- A force-free Git reconciliation protocol protected by one writer lease.
- A fixed-message remote watcher with exact tmux-pane registration.
- Harness adapters and a common tmux-backed agent launcher.
- `launchd` installation on macOS and `systemd --user` installation on Linux.
- Local-only runtime state, credentials, raw logs, and machine configuration.

## Requirements

- macOS or Linux
- Git
- tmux
- POSIX `sh`
- Python 3 for routing and dossier reconciliation
- At least one supported terminal agent harness

The watcher uses the checkout's ordinary Git authentication. Configure SSH, a
Git credential helper, or another host-appropriate mechanism before enabling
unattended polling. The blueprint does not mint, store, or broker credentials.

## Start an instance

1. Create a repository from this blueprint and clone it to the target host.
2. Customize `PERSONA.md`, `DECISIONS.md`, and `WORK-CHARTERS.md` without adding
   secrets or unnecessary personal information.
3. Create the root's attributed worktree and start the chosen harness there:

   ```sh
   scripts/agent-channel.py worktree orchestrator
   cd PRINTED_WORKTREE_PATH
   tmux new-session -s orchestrator
   codex
   # or: claude, pi, prime-agent
   ```

4. Once the CLI is ready, register its exact pane from another terminal:

   ```sh
   scripts/orchestrator-wake.sh -a orchestrator register PANE codex
   scripts/orchestrator-wake.sh -a orchestrator status
   ```

5. Review existing input, then initialize at the full remote commit SHA through
   which work is reconciled. The first poll routes commits after that base:

   ```sh
   scripts/agent-channel.py initialize BASE_SHA
   scripts/watch-remote.sh
   ```

6. Install the host scheduler after the manual path succeeds:

   ```sh
   scripts/install-watcher.sh
   ```

Read `AUTOMATION.md` before enabling unattended wake delivery. Read
`operator-process.md` before launching assignment-bound agents.

## Peer correspondence

The [agent protocol][agent-protocol] implements separate agent worktrees,
registered tmux recipients, file mentions, and durable reply receipts. This is
the routing system for root and peers. Review its initialization and transition
procedure before updating an existing instance.

## Repository map

- [Shared kernel proposal][shared-kernel] — proposed common principles,
  instance boundaries, communication, authentication, and return of lessons.
- `PERSONA.md` — root Orchestrator identity and working style.
- `TERMS.md` — operating vocabulary and harness-neutral boundaries.
- `DECISIONS.md` — adopted, provisional, superseded, and pending decisions.
- `questions.md` — unresolved choices that require collaborator judgment.
- `WORK-CHARTERS.md` — continuing domains and their authority boundaries.
- `OPERATOR-TRAIL.md` — rules for durable operational receipts.
- `operator-trails/` — append-only monthly trail files created by an instance.
- `AUTOMATION.md` — remote polling, tmux waking, and scheduler setup.
- `PORTABILITY.md` — macOS/Linux compatibility contract.
- `SECURITY.md` — secrets, local state, and publication boundaries.
- `harnesses/` — terminal-harness adapters.
- `queue/` — one-file-per-effort work queue.
- `sub-agents/` — proposed, active, and inactive agent dossiers.
- `scripts/` — portable watcher, lease, wake, launch, and validation tools.

## Design boundary

The repository is a record and coordination surface, not proof that a process
is live, a model was used, or an action succeeded. Runtime claims need receipts.
Agent authority must be explicit, narrow, and removable. A remote commit is
collaboration input—not permission to execute arbitrary repository content.

[shared-kernel]: ./proposals/shared-kernel.md

[agent-protocol]: ./AGENT-PROTOCOL.md
