# Operator process

> **Brief:** The root Orchestrator proposes bounded work, activates one explicit
> dossier, launches it through a named harness adapter, verifies the result,
> removes authority, and lets the reconciler archive it.

## Dossier lifecycle

1. Create a proposed dossier under `sub-agents/proposed/<agent-id>/` from the
   template in `sub-agents/proposed/README.md`.
2. Resolve model, harness, worktree, path ownership, credential, budget,
   lifespan, and completion questions before launch.
3. Move the dossier to `sub-agents/active/<agent-id>/` and add exactly one row
   to `sub-agents/active.md`.
4. Launch it with:

   ```sh
   scripts/launch-agent.sh AGENT_ID HARNESS WORKTREE [MODEL] [EFFORT]
   ```

5. Record the printed tmux and process receipt in `runtime.md`. Raw `runner.log`
   files are ignored and remain local.
6. Review every modified path and rerun relevant checks from the root role.
7. Record completion or cancellation, remove the authority row, and run:

   ```sh
   python3 scripts/reconcile-agents.py
   ```

The reconciler is the sole archiver. A live tmux session, PID, or dossier
directory never grants authority without the corresponding active row.

## Harness boundary

The common launcher validates the agent ID, exact worktree root, active dossier,
prompt file, and executable adapter. The adapter alone translates model and
effort fields into harness-specific flags. Unsupported fields remain recorded
but must not be fabricated as effective.
