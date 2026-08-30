# Harness adapters

> **Brief:** Harness adapters translate one stable launcher contract into
> terminal-specific commands. Codex, Claude Code, Pi, and Prime Agent are
> included without making any one harness the Orchestrator's identity.

Each executable adapter receives:

```text
ADAPTER REPOSITORY WORKTREE PROMPT_FILE MODEL EFFORT
```

It validates any harness-specific requirements, changes to the worktree, and
replaces itself with the terminal harness. The common launcher supplies tmux,
the active dossier, raw-log capture, and the runtime receipt surface.

Included adapters:

- `codex.sh` — passes the worktree, repository, model, effort, workspace
  sandbox, and on-request approval policy.
- `claude-code.sh` — passes the worktree context, model, effort, and manual
  permission mode.
- `pi.sh` — starts Pi with the assignment prompt; model configuration remains
  inside Pi until a stable cross-version CLI flag is adopted.
- `prime-agent.sh` — starts Prime Agent with the assignment prompt; model
  configuration remains inside the harness until a stable flag is adopted.
- `custom.sh` — minimal contract for another terminal executable.

Before unattended use, compare an adapter with the installed CLI's `--help` and
record its version in the runtime receipt. A recognized harness name does not
prove installation, authentication, model selection, or effective authority.

Official references: [Codex CLI documentation][codex],
[Claude Code documentation][claude], [Pi documentation][pi], and
[Prime Agent documentation][prime-agent].

[claude]: https://docs.anthropic.com/en/docs/claude-code
[codex]: https://developers.openai.com/codex/cli
[pi]: https://pi.dev/docs/latest
[prime-agent]: https://github.com/PrimeIntellect-ai/prime-agent
