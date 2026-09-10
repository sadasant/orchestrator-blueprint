#!/usr/bin/env python3
"""Worktrees and durable peer messages for the repository channel."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
EVENT = re.compile(r"[0-9a-f]{32}\Z")
MENTION = re.compile(r"(?<![\w@])@([a-z0-9]+(?:-[a-z0-9]+)*)(?![\w-])")
ROOT = "orchestrator"


def run(*args, cwd=None):
    return subprocess.run(
        args, cwd=cwd, text=True, capture_output=True, check=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).stdout.strip()


def git(repo, *args):
    return run("git", "-C", str(repo), *args)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main_checkout(repo):
    for line in git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            return Path(line[9:]).resolve()
    raise ValueError("main checkout unavailable")


def state_directory(repo):
    default = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / main_checkout(repo).name
    return Path(os.environ.get("ORCHESTRATOR_STATE_DIR", str(default))).resolve()


@contextmanager
def lease(state, held=False):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = state / "run.lock"
    if held:
        require(lock.is_dir(), "--lease-held requires the existing writer lease")
    else:
        lock.mkdir(mode=0o700)  # Never steal an existing lease based on its age.
    try:
        yield
    finally:
        if not held:
            lock.rmdir()


def read_state(state):
    path = state / "agent-channel.json"
    if not path.exists():
        return {"version": 1, "cursor": None, "events": []}
    require(not path.is_symlink(), "channel state must not be a symlink")
    data = json.loads(path.read_text())
    require(data.get("version") == 1 and isinstance(data.get("events"), list), "invalid channel state")
    require(data.get("cursor") is None or SHA.fullmatch(data["cursor"]), "invalid channel cursor")
    for event in data["events"]:
        require(EVENT.fullmatch(event["id"]) and SHA.fullmatch(event["commit"])
                and NAME.fullmatch(event["recipient"]), "invalid stored message")
        require(event["status"] in {"pending", "sending", "sent", "uncertain", "acknowledged", "held"}, "invalid message status")
    return data


def save_state(state, data):
    path = state / "agent-channel.json"
    require(not path.is_symlink(), "channel state must not be a symlink")
    fd, temporary = tempfile.mkstemp(prefix="channel-", dir=state)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def blob(repo, ref, path):
    try:
        return subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{path}"],
            check=True, capture_output=True, text=True,
        ).stdout
    except subprocess.CalledProcessError:
        return ""


def agents(repo, ref):
    """The existing authority table is the single source for peer names."""
    found = {ROOT: []}
    for line in blob(repo, ref, "sub-agents/active.md").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if len(cells) != 6 or not NAME.fullmatch(cells[0]) or cells[5] != "active":
            continue
        require(cells[0] not in found, "duplicate or reserved active agent name")
        paths = []
        for value in cells[3].split(","):
            value = value.strip().strip("`").rstrip("/")
            if value:
                require(not value.startswith(("/", "-")) and ".." not in Path(value).parts
                        and not any(c.isspace() for c in value), "owned paths must be relative paths, comma separated")
                paths.append(value)
        found[cells[0]] = paths
    return found


def author(repo, commit):
    values = git(repo, "show", "-s", "--format=%(trailers:key=Orchestrator-Agent,valueonly)", commit).splitlines()
    require(len(values) <= 1, "ambiguous agent trailer")
    if not values:
        return ""
    require(NAME.fullmatch(values[0]), "invalid agent trailer")
    return values[0]


def added_prose(repo, commit, path):
    """Added Markdown lines with paragraph boundaries, excluding fenced examples."""
    lines = blob(repo, commit, path).splitlines()
    eligible = {}
    fence = None
    for number, line in enumerate(lines, 1):
        mark = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if mark:
            token = mark[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence or line.startswith(("    ", "\t")) or line.lstrip().startswith("|"):
            continue
        previous = lines[number - 2].strip() if number > 1 else ""
        opens = not previous or previous == ">" or previous.startswith("#")
        eligible[number] = (line, opens)
    patch = git(repo, "diff", "--unified=0", "--no-ext-diff", "--no-textconv", f"{commit}^", commit, "--", path)
    number = 0
    for line in patch.splitlines():
        match = re.match(r"^@@ .* \+(\d+)(?:,\d+)? @@", line)
        if match:
            number = int(match[1])
        elif line.startswith("+") and not line.startswith("+++"):
            if number in eligible:
                yield eligible[number]
            number += 1
        elif line.startswith(" "):
            number += 1


def route(repo, commit, known):
    who = author(repo, commit)
    if who and who not in known:
        return []  # Retired or unknown agent traffic does not impersonate a person.
    paths = subprocess.run(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only",
         "-r", "-z", "-m", "--first-parent", commit],
        check=True, capture_output=True, text=True,
    ).stdout.split("\0")
    paths = [p for p in paths if p and not p.startswith("_unread/")]
    if not paths:
        return []
    targets = set()
    addressed = False
    for path in paths:
        if not path.endswith(".md"):
            continue
        for text, opens in added_prose(repo, commit, path):
            body = re.sub(r"^\s*>\s?", "", text).lstrip()
            mentions = MENTION.findall(body)
            if who:
                head = re.match(r"^(?:[-*] )?(?:`|\*\*)?@([a-z0-9]+(?:-[a-z0-9]+)*)(?![\w-])", body)
                mentions = [head[1]] if opens and head else []
            for name in mentions:
                addressed = True
                if name != who:
                    targets.add(name if name in known else ROOT)
    if not addressed:
        owners = []
        for name, prefixes in known.items():
            if prefixes and all(any(p == prefix or p.startswith(prefix + "/") for prefix in prefixes) for p in paths):
                owners.append(name)
        if len(owners) == 1:
            if owners[0] != who:
                targets.add(owners[0])
        elif not who:
            targets.add(ROOT)
    return [(name, who, paths) for name in sorted(targets)]


def scan(repo, data, head, now):
    require(SHA.fullmatch(head), "invalid remote head")
    require(data["cursor"] is not None, "channel not initialized; run initialize BASE_SHA after reviewing existing work")
    git(repo, "merge-base", "--is-ancestor", data["cursor"], head)
    known = agents(repo, head)
    commits = git(repo, "rev-list", "--reverse", "--first-parent", f'{data["cursor"]}..{head}').splitlines()
    existing = {e["id"] for e in data["events"]}
    for commit in commits:
        for recipient, who, paths in route(repo, commit, known):
            limited = False
            if who and recipient != ROOT:
                recent = sum(e["author"] == who and e["recipient"] == recipient and now - e["created"] < 3600 for e in data["events"])
                if recent >= 5:
                    recipient, limited = ROOT, True
            event_id = hashlib.sha256(f"{commit}:{recipient}".encode()).hexdigest()[:32]
            if event_id in existing:
                continue
            data["events"].append({"id": event_id, "commit": commit, "recipient": recipient,
                "author": who, "paths": paths, "created": now, "status": "pending",
                "reason": "peer rate limit" if limited else "addressed change", "attempts": 0})
            existing.add(event_id)
    data["cursor"] = head


def deliver(repo, state, data, known):
    wake = repo / "scripts/orchestrator-wake.sh"
    env = {**os.environ, "ORCHESTRATOR_STATE_DIR": str(state)}
    for event in data["events"]:
        if event["status"] == "sending":
            event["status"] = "uncertain"  # Previous process stopped during submission.
        if event["status"] != "pending":
            continue
        if event["recipient"] not in known:
            event["status"] = "held"
            event["error"] = "recipient is no longer active; explicit review required"
            continue
        argv = [str(wake), "-a", event["recipient"]]
        check = subprocess.run([*argv, "status"], env=env, capture_output=True, text=True)
        if check.returncode:
            event["error"] = "recipient registration unavailable or changed"
            continue
        event["status"] = "sending"
        event["attempts"] += 1
        save_state(state, data)  # A crash from this point must not cause blind retyping.
        result = subprocess.run([*argv, "message", event["id"], event["commit"]], env=env, capture_output=True, text=True)
        event["status"] = "sent" if result.returncode == 0 else "uncertain"
        event["error"] = "" if result.returncode == 0 else "submission outcome uncertain; inspect before retry"
        save_state(state, data)
    save_state(state, data)


def initialize(repo, state, base, remote, branch):
    require(SHA.fullmatch(base), "initialization requires a full reviewed base SHA")
    require(not (state / "agent-channel.json").exists()
            and not (state / "agent-channel.json").is_symlink(), "channel already exists; preserve its cursor and receipts")
    git(repo, "fetch", "--quiet", remote, f"refs/heads/{branch}:refs/remotes/{remote}/{branch}")
    head = git(repo, "rev-parse", f"refs/remotes/{remote}/{branch}")
    git(repo, "merge-base", "--is-ancestor", base, head)
    save_state(state, {"version": 1, "cursor": base, "events": []})
    print(json.dumps({"cursor": base}))


def poll(repo, state, remote, branch):
    # Fetch objects only. Never execute or check out newly fetched scripts.
    git(repo, "fetch", "--quiet", remote, f"refs/heads/{branch}:refs/remotes/{remote}/{branch}")
    head = git(repo, "rev-parse", f"refs/remotes/{remote}/{branch}")
    data = read_state(state)
    scan(repo, data, head, time.time())
    save_state(state, data)  # Persist events and scan cursor together before delivery.
    deliver(repo, state, data, agents(repo, head))
    print(json.dumps({"cursor": head, "outstanding": sum(e["status"] != "acknowledged" for e in data["events"])}))


def ensure_worktree(repo, name, remote, branch):
    require(NAME.fullmatch(name), "invalid agent name")
    main = main_checkout(repo)
    git(main, "fetch", "--quiet", remote, branch)
    ref = f"refs/remotes/{remote}/{branch}"
    require(name in agents(main, ref), "agent must have an active authority row before worktree creation")
    target = main.parent / (main.name + "-agents") / name
    agent_branch = "agents/" + name
    if target.exists():
        require(target.resolve() == Path(git(target, "rev-parse", "--show-toplevel")).resolve(), "not an exact worktree root")
        require(main_checkout(target) == main and git(target, "branch", "--show-current") == agent_branch, "worktree belongs to another repository or branch")
        require(git(target, "config", "--worktree", "--get", "orchestrator.agent") == name, "worktree identity missing or changed")
        require(git(target, "config", "--worktree", "--get", "core.hooksPath") == str(target / ".githooks"), "worktree hook configuration changed")
        require(os.access(target / ".githooks/prepare-commit-msg", os.X_OK), "worktree attribution hook is absent")
        return target
    git(main, "cat-file", "-e", ref + ":.githooks/prepare-commit-msg")
    # Preserve custom hooks. Adoption must compose them explicitly.
    current = subprocess.run(["git", "-C", str(main), "config", "--get", "core.hooksPath"], capture_output=True, text=True)
    require(not current.stdout.strip(), "custom hooks configured; compose the agent hook before automatic worktree setup")
    target.parent.mkdir(parents=True, exist_ok=True)
    exists = subprocess.run(["git", "-C", str(main), "show-ref", "--verify", "--quiet", "refs/heads/" + agent_branch]).returncode == 0
    git(main, "worktree", "add", *([] if exists else ["-b", agent_branch]), str(target), agent_branch if exists else ref)
    git(main, "config", "extensions.worktreeConfig", "true")
    git(target, "config", "--worktree", "orchestrator.agent", name)
    git(target, "config", "--worktree", "core.hooksPath", str(target / ".githooks"))
    return target


def acknowledge(repo, data, event_id, response, remote, branch):
    require(EVENT.fullmatch(event_id) and SHA.fullmatch(response), "invalid acknowledgement")
    event = next(e for e in data["events"] if e["id"] == event_id)
    require(event["status"] in {"sent", "uncertain", "sending", "acknowledged"}, "message was not submitted")
    git(repo, "fetch", "--quiet", remote, branch)
    verified_head = git(repo, "rev-parse", f"refs/remotes/{remote}/{branch}")
    # Another writer may advance the branch after this reply landed. Preserve
    # that work: verify inclusion instead of requiring a new empty reply commit.
    git(repo, "merge-base", "--is-ancestor", response, "HEAD")
    git(repo, "merge-base", "--is-ancestor", response, verified_head)
    git(repo, "merge-base", "--is-ancestor", event["commit"], response)
    require(author(repo, response) == event["recipient"], "response agent does not match recipient")
    replies = git(repo, "show", "-s", "--format=%(trailers:key=Orchestrator-Reply-To,valueonly)", response).splitlines()
    require(event_id in replies, "response lacks the message reply trailer")
    event.update(status="acknowledged", response=response, verified_head=verified_head, error="")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--lease-held", action="store_true", help="caller already holds this repository's writer lease")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("initialize"); init.add_argument("base")
    commands.add_parser("poll")
    commands.add_parser("status")
    worktree = commands.add_parser("worktree"); worktree.add_argument("name")
    show = commands.add_parser("show"); show.add_argument("id")
    retry = commands.add_parser("retry"); retry.add_argument("id")
    ack = commands.add_parser("acknowledge"); ack.add_argument("id"); ack.add_argument("response")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    state = state_directory(repo)
    remote = os.environ.get("ORCHESTRATOR_REMOTE", "origin")
    branch = os.environ.get("ORCHESTRATOR_BRANCH", "main")
    require(not remote.startswith("-") and not branch.startswith("-"), "invalid remote or branch")
    if args.command in {"status", "show"}:
        data = read_state(state)
        if args.command == "show":
            require(EVENT.fullmatch(args.id), "invalid message ID")
            data = next(e for e in data["events"] if e["id"] == args.id)
        print(json.dumps(data, indent=2))
        return
    with lease(state, args.lease_held):
        if args.command == "poll":
            poll(repo, state, remote, branch)
        elif args.command == "initialize":
            initialize(repo, state, args.base, remote, branch)
        elif args.command == "worktree":
            print(ensure_worktree(repo, args.name, remote, branch))
        else:
            data = read_state(state)
            if args.command == "acknowledge":
                acknowledge(repo, data, args.id, args.response, remote, branch)
            else:
                require(EVENT.fullmatch(args.id), "invalid message ID")
                event = next(e for e in data["events"] if e["id"] == args.id)
                require(event["status"] in {"sent", "uncertain", "sending", "held"}, "only unresolved submissions or held messages need an explicit retry")
                event.update(status="pending", error="")
            save_state(state, data)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, StopIteration, KeyError, TypeError) as error:
        print(f"agent channel blocked: {error}", file=sys.stderr)
        sys.exit(1)
