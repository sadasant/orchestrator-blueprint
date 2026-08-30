# Decisions

> **Brief:** This ledger separates adopted operating choices from provisional,
> superseded, and pending decisions. New instances should preserve decision IDs
> and record why a choice changed.

## Adopted

### D-001 — Git is the durable collaboration surface

Repository records and commits carry durable working state across harness
instances. Live process state is useful but not authoritative by itself.

### D-002 — tmux is the session and wake transport

The portable core uses ordinary tmux. Wake delivery targets one explicitly
registered pane and sends only a fixed SHA notice.

### D-003 — Harnesses are adapters

Codex, Claude Code, Pi, Prime Agent, and future terminal harnesses share the
same repository protocol. Harness-specific command lines remain isolated under
`harnesses/`.

### D-004 — macOS and Linux are first-class hosts

Core scripts use POSIX shell and common Unix tools. Host scheduling is isolated
behind `launchd` and `systemd --user` installers.

### D-005 — One writer lease protects repository reconciliation

Interactive and scheduled writers share one local lease held through final
publication, verification, and checkpoint acknowledgement.

### D-006 — Sensitive and host-specific state remains local

Credentials, raw transcripts, exact home paths, pane registrations, logs, and
machine configuration are ignored or stored outside the repository.

## Provisional

- Five-minute remote polling is the default detection fallback. Event-driven
  delivery may replace it without changing wake-message or reconciliation
  semantics.
- The included harness adapters are reference implementations and should be
  verified against installed CLI versions before unattended use.

## Pending

- Choose whether a specific instance needs a public or private remote.
- Choose its authenticated Git transport and credential lifecycle.
- Choose which harness is the initial root and which may run bounded agents.

## Superseded

None.
