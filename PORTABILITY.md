# Portability contract

> **Brief:** The portable core targets macOS and Linux through POSIX shell,
> Git, tmux, and Python 3. Host-specific scheduling and CLI differences stay at
> explicit adapter boundaries.

## Portable core

- Shell scripts use `/bin/sh`, not a platform-specific interactive shell.
- Paths are derived from the checkout and XDG-compatible local state defaults.
- `tmux` provides session identity and fixed-message delivery on both hosts.
- Git supplies remote comparison, reconciliation, and durable checkpoints.
- Python 3 performs dossier archival without third-party packages.

## Host adapters

- macOS uses a generated user LaunchAgent under `~/Library/LaunchAgents`.
- Linux uses generated `systemd --user` service and timer units.
- Hosts without either scheduler may run `scripts/watch-remote.sh` from cron or
  another scheduler after verifying the same environment and paths.

## Harness adapters

Harness command lines evolve independently. Every adapter receives the same
five arguments: repository root, worktree, launch-prompt file, model, and
effort. It must end by replacing itself with the harness process.

Run `scripts/check.sh` on every supported host after changing shell code,
templates, or adapters.
