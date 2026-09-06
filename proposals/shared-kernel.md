# A shared kernel for working repositories

> **Brief:** Give each agent a clear role, its own worktree, a space in shared
> records, and a reachable terminal session. Keep common mechanics in Blueprint
> while each working repository retains its people, projects, and history.
> Return tested lessons to Blueprint for deliberate adoption elsewhere.

## Proposal status

This document proposes a direction for discussion. It does not change the
current runtime, grant credentials, launch agents, or supersede adopted
decisions. Here, **kernel** means the small shared set of collaboration
conventions and supporting scripts; it does not select a packaging mechanism.

The current Blueprint already has harness adapters, an agent launcher, a writer
lease, and remote-change notices for one registered root pane. Automatic
per-agent worktree management, mention routing, a guarded authentication
interface, and a versioned adoption workflow are proposed additions.

## K-01 — A place to work and a role to inhabit

> **Brief:** Agents cooperate through clear responsibilities and shared records.
> Each has its own worktree so concurrent edits do not disturb another agent's
> index or unfinished work. Those worktrees contribute to one shared repository.

An agent's space includes a role description, current assignment, working notes,
and pointers to the records it maintains. A domain owner and a functional helper
may work on the same project. Owned paths express responsibility; whether they
also restrict writes is an explicit local choice. They need not prevent peers
from contributing to the same document.

Role clarity and cooperative convention are the ordinary coordination mechanism.
Mechanical checks address costly mistakes and observed failures. Worktrees
isolate unfinished edits; concurrent pushes still require fetch, reconciliation,
and force-free publication. Introducing worktrees does not silently remove the
current writer-lease rule. Its scope must be reviewed alongside that change.

## K-02 — Names, roles, assignments, and instances

> **Brief:** Keep the address, continuing responsibility, present task, and
> running process separately legible. Each can change without requiring all the
> others to change with it.

| Field | Meaning | Example |
| --- | --- | --- |
| Name | The address used to reach an agent role | billing or surveyor |
| Role | Its continuing responsibility or method | Maintaining billing; surveying a codebase |
| Assignment | Its current scope and completion condition | Map one project's integration boundaries |
| Instance | The running harness carrying the role | A CLI session with a worktree and registered tmux pane |

A domain name can survive a change of method. A method name can survive a change
of subject. The role's current scope must be recorded when it evolves; its name
alone does not authorize work in a new repository.

Keep canonical project knowledge separate from an agent's working notes and
runtime receipt. A replacement instance should recover the role from named
records without requiring the earlier process to survive. Some assignments may
benefit from continuing the same session; that choice belongs to the role's
working contract. Retiring a process does not by itself retire its role.

## K-03 — Two complementary communication paths

> **Brief:** Shared files carry durable conversation. tmux makes a running CLI
> reachable by collaborators and other agents, regardless of harness. Both
> paths matter, including access through remote and accessible terminal clients.

| Path | Purpose | Shared expectation |
| --- | --- | --- |
| Repository correspondence | Questions, findings, decisions, and handoffs that remain inspectable | Reply beside the question or link to the resulting canonical record |
| Direct terminal conversation | Immediate interaction with a particular running agent | Resolve and validate the intended session before delivering input |

Mentions in changed files should be able to activate registered recipients.
Routing should distinguish an address from bookkeeping, examples, and ordinary
self-authored work. It should suppress self-triggering, bound repeated peer
messages, and make undeliverable work visible and recoverable.

For automatic repository wakes, deliver a bounded locator to the complete
committed instruction. Record delivery separately from the recipient's reply
or completed work. Direct conversation remains available without requiring a
commit for every exchange; consequential outcomes return to the shared record.

## K-04 — Guarded authentication without manual credentials per agent

> **Brief:** Provide a common interface for agents to use managed authentication
> within declared scope. Avoid making manual credential issuance a prerequisite
> for every new role or CLI session.

The interface should identify the requesting agent, target repository, permitted
operation, and applicable local policy. An underlying provider may issue
short-lived credentials or execute an authorized operation on the agent's
behalf. The provider and enforcement mechanism remain open design choices.

Role descriptions explain expected conduct; the authentication mechanism must
state which boundaries it actually enforces. A name, Git author field, or
caller-supplied role is not sufficient proof of identity. Record the operation
and result without exposing credential material. Declining one operation must
not silently fall back to a more privileged account.

This proposal chooses neither a credential service nor a new permission grant.
The next design step is to inventory existing mechanisms in working instances
and select the smallest interface that meets their actual needs.

## K-05 — Common mechanics, local working lives

> **Brief:** Share conventions and tested mechanics. Keep the actual roles,
> conversations, project knowledge, authority choices, and runtime addresses
> in each working repository.

| Common in Blueprint | Local to an instance |
| --- | --- |
| Role, assignment, and runtime record conventions | Actual roles, assignments, and continuity needs |
| Worktree and session lifecycle mechanics | Workspaces, running processes, and pane registrations |
| Addressing, routing, and delivery behavior | Correspondence and recipient assignments |
| Authentication interface and behavioral tests | Credential provider, grants, and account configuration |
| Reconciliation and compatibility checks | Project decisions, evidence, and operating history |

Compatibility means the shared operations and records have predictable meaning.
It does not require identical rosters, directory layouts, model choices, or
approval policies. Local extensions should name where they depart from the
common contract rather than quietly changing its meaning.

## K-06 — A return path for lessons

> **Brief:** Working repositories discover problems. Blueprint receives the
> general lesson and a way to test it. Each instance then deliberately adopts
> a known revision while preserving its local records and choices.

1. Record the observed problem and the attempted repair in the working instance.
2. Extract the reusable behavior into a Blueprint proposal, using synthetic
   examples when the originating records are private.
3. Add a regression case or a concrete review example appropriate to the change.
4. Review and publish a named revision of the common behavior.
5. Let each instance review the difference, adopt it, and record its base
   revision, local deviations, and validation result.
6. Return problems found during adoption to Blueprint for the next revision.

Do not synchronize instance conversations or credentials back into Blueprint.
Do not overwrite local policy simply to match a newer template. Whether common
files arrive through a package, vendored copies, or another update mechanism
remains open; the first requirement is an inspectable adoption history.

## Questions for this review

> **Brief:** Agree on the shared contract before choosing distribution and
> authentication machinery. Feedback can stay beside the section it concerns.

- Does the common/local boundary in K-05 preserve enough room for each instance?
- Which existing authentication mechanism should inform K-04's first adapter?
- Should the first implementation join worktrees, registration, and mention
  delivery, or establish revision tracking and adoption first?

After this review, the next PR can specify one small end-to-end path: give an
agent a worktree, register its session, address it from a file, receive its reply,
and preserve that reply through concurrent publication. Acceptance should cover
an unavailable recipient and a restarted instance as well as successful delivery.
