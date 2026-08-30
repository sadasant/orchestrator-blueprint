# Orchestrator terms

> **Brief:** These repository-local terms distinguish durable records, harnesses,
> instances, authority, polling, and waking. They are operational definitions,
> not universal classifications or proof that a runtime claim is true.

## State and continuity

- **Durable working state:** Records and artifacts deliberately retained across
  execution instances.
- **Root Orchestrator:** The continuing working role specified by the persona,
  instructions, decisions, and records in one repository instance.
- **Checkpoint:** The exact remote commit already reconciled and acknowledged
  by the root Orchestrator.
- **Operator trail:** An append-only account of attempts, observations,
  receipts, outcomes, and follow-up. It is an attestation unless independently
  supported.

## Work and execution

- **Assignment:** A bounded request with a completion condition.
- **Work charter:** A continuing domain with a named purpose, authority
  boundary, and current operating shape.
- **Language model:** The configured inference model used by a harness.
- **Agent harness:** The runtime wrapper that supplies context, tools,
  permissions, an action loop, and a session interface. Codex, Claude Code, Pi,
  and Prime Agent are harness families.
- **Agent instance:** One concrete running harness configuration realizing a
  role. Its receipt names the harness, model, process, tmux coordinates,
  worktree, authority, lifespan, and ledgers.
- **Harness adapter:** One executable that translates the common launcher
  contract into a harness-specific invocation.
- **Runtime receipt:** The durable record for one agent instance. Unknown values
  remain unknown; declarations and observations are distinguished.
- **Writer lease:** A local, exclusive directory lock shared by interactive and
  scheduled repository writers.

## Wake transport

- **Poll:** A background check for remote change. A no-change poll does not
  contact the root harness.
- **Wake:** Delivery of a validated, fixed notice to one explicitly registered
  tmux pane after relevant remote state changes.
- **Pane registration:** Local binding between the intended root session, its
  exact tmux identities, and its declared harness family.
