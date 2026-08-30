# Work queue

> **Brief:** The queue gives each bounded effort one durable file and one
> current state. It records progress without treating a dashboard as authority
> to execute work.

Use these directories:

- `pending/` — proposed but not started;
- `in-progress/` — actively owned work;
- `done/` — completed work with verification;
- `archived/` — cancelled, obsolete, or intentionally closed work.

Create items from `TEMPLATE.md`. Move files between states without changing
their stable `Q-NNN` identifier. Preserve collaborator feedback and material
history.
