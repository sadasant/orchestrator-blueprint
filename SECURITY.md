# Security and privacy

> **Brief:** The repository stores durable operating records, never ambient
> secrets or unnecessary identity data. Runtime authority stays narrow,
> explicit, local, and removable.

## Never commit

- API keys, tokens, cookies, private keys, or credential-helper output;
- real names, personal email addresses, usernames, or home-directory paths
  unless a specific public instance intentionally requires them;
- raw harness transcripts or pane captures;
- host inventories, process lists, network details, or environment dumps;
- local pane registrations, watcher state, or scheduler logs.

## Local state

Scripts default to:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/<repository-name>/
```

State files are created with restrictive permissions. Override
`ORCHESTRATOR_STATE_DIR` when multiple instances share a repository basename.

## Credentials

The watcher calls ordinary non-interactive Git. Configure authentication using
the host's Git and credential-management policy. Assignment-bound agents receive
no publication credential by default. If an instance adopts such a mechanism,
keep it ignored, repository-scoped, minimum-permission, short-lived when
possible, and absent from arguments, prompts, logs, dossiers, and history.

## Remote input

A remote commit is untrusted collaboration input until inspected. The watcher
may resolve a remote SHA and send a fixed notice; it does not fetch into the
checkout, execute changed files, commit, or push.
