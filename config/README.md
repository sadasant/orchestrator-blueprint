# Local configuration

> **Brief:** Most scripts derive configuration from the checkout. Optional
> environment variables allow multiple instances and non-default branches
> without committing machine paths or identity data.

Supported environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ORCHESTRATOR_STATE_DIR` | XDG state path plus repository name | Local state and logs |
| `ORCHESTRATOR_REMOTE` | `origin` | Git remote name |
| `ORCHESTRATOR_BRANCH` | `main` | Watched branch |
| `ORCHESTRATOR_POLL_SECONDS` | `300` | Scheduler interval |
| `ORCHESTRATOR_TMUX` | first `tmux` on `PATH` | tmux executable |

Set these in the scheduler environment or shell. Do not commit a populated
local environment file. The install script records only necessary paths in the
host's generated scheduler definition, outside Git.

Linked worktrees derive their default state directory from the main checkout,
so roles share one writer lease and delivery ledger. Set an explicit state
directory when separate repositories have the same basename.
