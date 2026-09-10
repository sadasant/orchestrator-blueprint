# Orchestrator terms

> **Brief:** These repository-local terms distinguish durable records, harnesses,
> instances, authority, polling, and waking. They are operational definitions,
> not universal classifications or proof that a runtime claim is true.

## State and continuity

- **Durable working state:** Records and artifacts deliberately retained across
  execution instances.
- **Root Orchestrator:** The continuing working role specified by the persona,
  instructions, decisions, and records in one repository instance.
- **Checkpoint:** A recorded point of verified reconciliation or publication.
- **Scan cursor:** The remote commit through which input has been routed; it
  does not mean the resulting messages have been answered.
- **Reply receipt:** A message ID, matching published reply commit, and the
  remote head against which its inclusion was verified.
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

- **Poll:** A background scan of remote changes and retry of definitely
  undelivered messages, including when no new commits arrive.
- **Wake:** Delivery of a validated, fixed notice to one explicitly registered
  tmux pane for one queued recipient event.
- **Pane registration:** Local binding between the intended agent session, its
  exact tmux identities, and its declared harness family.
