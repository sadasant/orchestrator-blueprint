# Operator trail

> **Brief:** Operator trails preserve what was attempted, observed, and
> concluded without pretending that an operator's own account is independent
> evidence. Instances append concise monthly records for substantive work.

Create `operator-trails/YYYY-MM.md` when the first substantive operation occurs.
Each entry should include:

- stable entry ID;
- UTC time range;
- actor or process role;
- trigger and intended scope;
- attempts, including failures and retries;
- observations and their source;
- receipts such as commits, process identities, checks, and artifacts;
- outcome and unresolved follow-up.

Never place secrets, raw prompts, raw transcripts, personal information, or
host inventories in an operator trail. Prefer stable repository-relative paths
and commit IDs over machine-specific absolute paths.
