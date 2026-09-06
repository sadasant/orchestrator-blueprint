"""Offline Git and transport integration tests; no model or account is used."""
from contextlib import redirect_stdout
import io
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("channel", SOURCE / "scripts/agent-channel.py")
channel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(channel)


class ChannelTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="blueprint-test-")
        self.base = Path(self.tmp.name)
        self.repo = self.base / "main checkout"
        self.remote = self.base / "remote.git"
        self.state = self.base / "state"
        self.repo.mkdir(); self.state.mkdir()
        self.env = patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
            "ORCHESTRATOR_STATE_DIR": str(self.state)}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.tmp.cleanup)
        self.cmd("git", "init", "--bare", "-q", str(self.remote))
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture" + "@" + "example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("remote", "add", "origin", str(self.remote))
        shutil.copytree(SOURCE / "scripts", self.repo / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(SOURCE / ".githooks", self.repo / ".githooks")
        self.write("sub-agents/active.md", "| Agent ID | Harness | Assignment | Owned paths | Started | State |\n| --- | --- | --- | --- | --- | --- |\n| billing | codex | example | projects/billing | now | active |\n| surveyor | custom | example | projects/map | now | active |\n")
        self.write("README.md", "# Fixture\n")
        self.head = self.commit("seed")
        self.push()
        self.fake = self.base / "tmux"
        self.fake.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state=Path(os.environ['ORCHESTRATOR_STATE_DIR'])
a=sys.argv[1:]
def flag(n): return a[a.index(n)+1]
if a[0]=='display-message':
 p=flag('-t')
 if (state/('missing'+p)).exists(): sys.exit(1)
 pid='999' if (state/('changed'+p)).exists() else '123'
 result=p+'|'+pid+'|/dev/pts/1|0|python|$1|@1'
 if '@orchestrator_root' in a[-1]:
  f=state/('marker'+p)
  result+='|'+(f.read_text() if f.exists() else '')
 print(result)
elif a[0]=='set-option':
 p=flag('-t'); f=state/('marker'+p)
 if '-u' in a:
  f.unlink(missing_ok=True)
 else: f.write_text(a[-1])
elif a[0]=='send-keys':
 with (state/'typed').open('a') as f: f.write(json.dumps(a)+'\\n')
 if (state/'fail-send').exists(): sys.exit(1)
else: sys.exit(2)
''')
        self.fake.chmod(0o755)
        os.environ["ORCHESTRATOR_TMUX"] = str(self.fake)
        self.addCleanup(lambda: os.environ.pop("ORCHESTRATOR_TMUX", None))

    def cmd(self, *args, cwd=None):
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True).stdout.strip()

    def git(self, *args, repo=None):
        return self.cmd("git", "-C", str(repo or self.repo), *args)

    def write(self, name, text):
        p = self.repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)

    def commit(self, message, agent=None, reply=None, repo=None):
        repo = repo or self.repo
        self.git("add", "-A", repo=repo)
        args = ["commit", "-q", "-m", message]
        if agent: args += ["--trailer", "Orchestrator-Agent: " + agent]
        if reply: args += ["--trailer", "Orchestrator-Reply-To: " + reply]
        self.git(*args, repo=repo)
        return self.git("rev-parse", "HEAD", repo=repo)

    def push(self, repo=None):
        self.git("push", "-q", "origin", "HEAD:main", repo=repo)

    def data(self):
        return channel.read_state(self.state)

    def scan(self):
        data = {"version": 1, "cursor": self.head, "events": []}
        channel.scan(self.repo, data, self.git("rev-parse", "HEAD"), 100)
        return data

    def poll(self):
        with redirect_stdout(io.StringIO()):
            channel.poll(self.repo, self.state, "origin", "main")

    def register(self, agent="billing", pane="%1"):
        self.cmd(str(self.repo / "scripts/orchestrator-wake.sh"), "-a", agent, "register", pane, "custom")

    def typed(self):
        p = self.state / "typed"
        return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []

    def test_first_poll_initializes_and_unchanged_poll_is_silent(self):
        self.poll(); self.poll()
        self.assertEqual(self.data()["events"], [])
        self.assertEqual(self.typed(), [])
        self.assertFalse((self.state / "processed-head").exists())

    def test_human_change_routes_to_root_or_owner(self):
        self.write("projects/billing/question.md", "a question\n")
        self.commit("question")
        self.assertEqual([e['recipient'] for e in self.scan()['events']], ['billing'])
        self.write("other.md", "an unaddressed question\n"); self.commit("other")
        self.assertEqual(self.scan()['events'][-1]['recipient'], 'orchestrator')

    def test_agent_mentions_require_paragraph_and_ignore_examples(self):
        self.write("notes.md", "about a peer\n@billing wrapped continuation\n\n```\n@billing fixture\n```\n\n| @billing | roster |\n")
        self.commit("records", agent="surveyor")
        self.assertEqual(self.scan()['events'], [])
        self.write("notes.md", "intro\n\n@billing please inspect this\n")
        self.commit("address", agent="surveyor")
        self.assertEqual([e['recipient'] for e in self.scan()['events']], ['billing'])

    def test_self_work_unknown_agent_and_machine_state_do_not_loop(self):
        self.write("projects/billing/note.md", "@billing self\n"); self.commit("own", agent="billing")
        self.write("stranger.md", "@billing ping\n"); self.commit("unknown", agent="retired")
        self.write("_unread/device.json", "{}\n"); self.commit("machine")
        self.assertEqual(self.scan()['events'], [])

    def test_indented_first_line_and_fenced_mentions_are_not_speech(self):
        self.write('example.md', '    @billing code\n')
        self.commit('indented example', agent='surveyor')
        self.assertEqual(self.scan()['events'], [])

    def test_invalid_notice_does_not_type_and_unpublished_reply_cannot_ack(self):
        self.register()
        wake = str(self.repo / 'scripts/orchestrator-wake.sh')
        with self.assertRaises(subprocess.CalledProcessError):
            self.cmd(wake, '-a', 'billing', 'message', '../bad', 'a' * 40)
        self.assertEqual(self.typed(), [])
        self.poll(); self.write('ask.md', '@billing go\n'); self.commit('ask'); self.push(); self.poll()
        data = self.data(); event = data['events'][0]
        self.write('reply.md', 'reply\n'); unpublished = self.commit('reply', agent='billing', reply=event['id'])
        with self.assertRaises(subprocess.CalledProcessError):
            channel.acknowledge(self.repo, data, event['id'], unpublished, 'origin', 'main')
        self.assertEqual(event['status'], 'sent')

    def test_multiple_mentions_coalesce_and_unknown_target_is_visible(self):
        self.write("a.md", "@billing first\n\n@billing second\n\n@ghost third\n")
        self.commit("mentions")
        self.assertEqual([e['recipient'] for e in self.scan()['events']], ['billing', 'orchestrator'])

    def test_pair_budget_redirects_sixth_message_to_root(self):
        for n in range(6):
            self.write(f"notes/{n}.md", "@billing question\n"); self.commit("ask", agent="surveyor")
        events = self.scan()['events']
        self.assertEqual([e['recipient'] for e in events], ['billing'] * 5 + ['orchestrator'])
        self.assertEqual(events[-1]['reason'], 'peer rate limit')

    def test_missing_peer_retried_on_unchanged_head_without_retyping_success(self):
        self.poll(); self.register()
        self.write("ask.md", "@billing one\n\n@surveyor two\n"); self.commit("ask"); self.push()
        self.poll()
        self.assertEqual([e['status'] for e in self.data()['events']], ['sent', 'pending'])
        self.assertEqual(len(self.typed()), 2)
        self.register("surveyor", "%2"); self.poll(); self.poll()
        self.assertEqual([e['status'] for e in self.data()['events']], ['sent', 'sent'])
        self.assertEqual(len(self.typed()), 4)
        message = self.typed()[0][-1]
        self.assertTrue(message.startswith('# orchestrator-message '))
        self.assertNotIn('one', message)

    def test_failed_submission_becomes_uncertain_and_requires_explicit_retry(self):
        self.poll(); self.register(); (self.state / 'fail-send').touch()
        self.write("ask.md", "@billing go\n"); self.commit("ask"); self.push(); self.poll()
        self.assertEqual(self.data()['events'][0]['status'], 'uncertain')
        count = len(self.typed()); self.poll()
        self.assertEqual(len(self.typed()), count)
        event_id = self.data()['events'][0]['id']
        (self.state / 'fail-send').unlink()
        self.cmd(sys.executable, str(self.repo / 'scripts/agent-channel.py'), 'retry', event_id)
        self.poll()
        self.assertEqual(self.data()['events'][0]['status'], 'sent')

    def test_restarted_pane_needs_registration_again(self):
        self.poll(); self.register(); (self.state / 'changed%1').touch()
        self.write('ask.md', '@billing go\n'); self.commit('ask'); self.push(); self.poll()
        self.assertEqual(self.data()['events'][0]['status'], 'pending')
        self.assertEqual(self.typed(), [])
        self.register(); self.poll()
        self.assertEqual(self.data()['events'][0]['status'], 'sent')

    def test_removed_recipient_is_held_until_review(self):
        self.poll(); self.write('ask.md', '@billing go\n'); self.commit('ask'); self.push(); self.poll()
        self.write('sub-agents/active.md', '| surveyor | custom | x | projects/map | now | active |\n')
        self.commit('retire'); self.push(); self.poll()
        self.assertEqual(self.data()['events'][0]['status'], 'held')

    def test_scan_crash_and_corrupt_state_never_silently_drop_messages(self):
        self.write('ask.md', '@billing go\n'); self.commit('ask')
        data = self.scan(); data['events'][0]['status'] = 'sending'
        channel.save_state(self.state, data)
        channel.deliver(self.repo, self.state, channel.read_state(self.state), channel.agents(self.repo, 'HEAD'))
        self.assertEqual(self.data()['events'][0]['status'], 'uncertain')
        (self.state / 'agent-channel.json').write_text('{bad')
        with self.assertRaises(ValueError): self.data()

    def test_worktrees_are_isolated_named_and_share_state(self):
        first = channel.ensure_worktree(self.repo, 'billing', 'origin', 'main')
        second = channel.ensure_worktree(self.repo, 'surveyor', 'origin', 'main')
        (first / 'private-edit.md').write_text('unfinished\n')
        self.assertFalse((second / 'private-edit.md').exists())
        self.assertFalse((self.repo / 'private-edit.md').exists())
        self.assertEqual(channel.ensure_worktree(self.repo, 'billing', 'origin', 'main'), first)
        self.assertEqual(channel.state_directory(first), channel.state_directory(second))
        commit = self.commit('work', repo=first)
        self.assertEqual(channel.author(first, commit), 'billing')
        self.assertEqual(channel.author(self.repo, self.head), '')
        with self.assertRaises(ValueError): channel.ensure_worktree(self.repo, '../escape', 'origin', 'main')
        with self.assertRaises(ValueError): channel.ensure_worktree(self.repo, 'ghost', 'origin', 'main')

    def test_default_runtime_namespace_is_shared_by_worktrees(self):
        tree = channel.ensure_worktree(self.repo, 'billing', 'origin', 'main')
        with patch.dict(os.environ):
            os.environ.pop('ORCHESTRATOR_STATE_DIR', None)
            os.environ['XDG_STATE_HOME'] = str(self.base / 'xdg')
            expected = (self.base / 'xdg' / self.repo.name).resolve()
            self.assertEqual(channel.state_directory(tree), expected)
            self.assertEqual(channel.state_directory(self.repo), expected)
            self.cmd(str(tree / 'scripts/orchestrator-wake.sh'), '-a', 'billing', 'register', '%3', 'custom')
            self.cmd(str(self.repo / 'scripts/orchestrator-wake.sh'), '-a', 'billing', 'status')
            self.assertTrue((expected / 'panes/billing').exists())

    def test_opt_in_watcher_dispatch_and_legacy_no_change(self):
        watcher = str(self.repo / 'scripts/watch-remote.sh')
        self.cmd(watcher)
        self.assertTrue((self.state / 'processed-head').exists())
        self.assertFalse((self.state / 'agent-channel.json').exists())
        with patch.dict(os.environ, {'ORCHESTRATOR_AGENT_ROUTING': '1'}):
            self.cmd(watcher)
            self.write('ask.md', '@billing hello\n'); self.commit('ask'); self.push()
            self.cmd(watcher)
            self.assertEqual(self.data()['events'][0]['status'], 'pending')
            self.register()
            self.cmd(watcher)
            self.assertEqual(self.data()['events'][0]['status'], 'sent')
        self.assertEqual((self.state / 'processed-head').read_text().strip(), self.head)

    def test_end_to_end_reply_rebase_publish_and_acknowledge(self):
        self.poll(); self.register()
        tree = channel.ensure_worktree(self.repo, 'billing', 'origin', 'main')
        self.write('ask.md', '@billing answer here\n'); self.commit('ask'); self.push(); self.poll()
        event = self.data()['events'][0]
        self.git('pull', '--rebase', 'origin', 'main', repo=tree)
        (tree / 'ask.md').write_text('@billing answer here\n\n## Reply\nAnswer recorded.\n')
        reply = self.commit('reply', reply=event['id'], repo=tree)
        self.write('concurrent.md', 'parallel work\n'); self.commit('concurrent'); self.push()
        with self.assertRaises(subprocess.CalledProcessError): self.push(repo=tree)
        self.git('fetch', 'origin', repo=tree); self.git('rebase', 'origin/main', repo=tree)
        reply = self.git('rev-parse', 'HEAD', repo=tree); self.push(repo=tree)
        self.git('pull', '--ff-only', 'origin', 'main')
        self.write('after.md', 'work after the reply landed\n'); later = self.commit('later'); self.push()
        data = self.data(); channel.acknowledge(tree, data, event['id'], reply, 'origin', 'main'); channel.save_state(self.state, data)
        self.assertEqual(self.data()['events'][0]['verified_head'], later)
        self.assertEqual(self.data()['events'][0]['status'], 'acknowledged')
        self.assertTrue((tree / 'concurrent.md').exists())
        self.poll()
        self.assertEqual(len([e for e in self.data()['events'] if e['recipient'] == 'billing']), 1)
        bad = self.data(); bad['events'][0]['status'] = 'sent'
        with self.assertRaises(subprocess.CalledProcessError): channel.acknowledge(tree, bad, event['id'], self.head, 'origin', 'main')

    def test_active_lease_and_diverged_cursor_fail_without_reset(self):
        with channel.lease(self.state):
            with self.assertRaises(FileExistsError):
                with channel.lease(self.state): pass
        self.assertFalse((self.state / 'run.lock').exists())
        self.poll(); data = self.data(); data['cursor'] = 'f' * 40
        channel.save_state(self.state, data)
        with self.assertRaises(subprocess.CalledProcessError): self.poll()
        self.assertEqual(self.data()['cursor'], 'f' * 40)

    def test_legacy_root_registration_and_notify_still_work(self):
        self.register('orchestrator')
        wake = str(self.repo / 'scripts/orchestrator-wake.sh')
        self.cmd(wake, 'notify', 'a' * 40, 'b' * 40)
        self.assertTrue(self.typed()[0][-1].startswith('# orchestrator-wake '))
        self.register('billing', '%2')
        (self.state / 'notified-head').write_text('a' * 40)
        self.cmd(wake, '-a', 'billing', 'unregister')
        self.assertTrue((self.state / 'notified-head').exists())


    def test_merge_introduced_messages_are_not_lost_or_duplicated(self):
        self.git('checkout', '-q', '-b', 'topic')
        self.write('topic.md', '@billing review the merged change\n'); self.commit('topic')
        self.git('checkout', '-q', 'main')
        self.write('parallel.md', 'parallel\n'); self.commit('parallel')
        self.git('merge', '--no-ff', '-m', 'merge topic', 'topic')
        events = self.scan()['events']
        self.assertEqual(len([e for e in events if e['recipient'] == 'billing']), 1)

    def test_custom_hooks_and_unrelated_existing_worktree_are_preserved(self):
        self.git('config', 'core.hooksPath', 'custom-hooks')
        with self.assertRaises(ValueError): channel.ensure_worktree(self.repo, 'billing', 'origin', 'main')
        self.assertEqual(self.git('config', '--get', 'core.hooksPath'), 'custom-hooks')

    def test_symlink_state_and_duplicate_authority_rows_are_rejected(self):
        external = self.base / 'external'; external.write_text('{}')
        (self.state / 'agent-channel.json').symlink_to(external)
        with self.assertRaises(ValueError): self.data()
        with self.assertRaises(ValueError): channel.save_state(self.state, {'version': 1})
        self.assertEqual(external.read_text(), '{}')
        self.write('sub-agents/active.md', '| billing | x | x | x | now | active |\n' * 2)
        self.commit('duplicate')
        with self.assertRaises(ValueError): channel.agents(self.repo, 'HEAD')

    @unittest.skipUnless(os.environ.get('BLUEPRINT_REAL_TMUX') == '1', 'opt-in isolated tmux smoke test')
    def test_real_tmux_receives_locator_without_using_an_agent(self):
        import shlex
        import time
        executable = shutil.which('tmux')
        self.assertIsNotNone(executable)
        socket = self.base.name
        def tmux(*args):
            return self.cmd(executable, '-L', socket, *args)
        self.addCleanup(lambda: subprocess.run([executable, '-L', socket, 'kill-server'], capture_output=True))
        wrapper = self.base / 'isolated-tmux'
        wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(executable) + ' -L ' + shlex.quote(socket) + ' "$@"\n')
        wrapper.chmod(0o755)
        os.environ['ORCHESTRATOR_TMUX'] = str(wrapper)
        receiver = self.base / 'receiver.py'
        ready = self.base / 'ready'; received = self.base / 'received'
        receiver.write_text('import sys\nfrom pathlib import Path\nPath(sys.argv[1]).touch()\nfor line in sys.stdin:\n with Path(sys.argv[2]).open("a") as f: f.write(line)\n')
        command = 'exec ' + ' '.join(shlex.quote(x) for x in [sys.executable, '-u', str(receiver), str(ready), str(received)])
        pane = tmux('new-session', '-d', '-P', '-F', '#{pane_id}', '-s', 'fixture', command)
        for _ in range(100):
            if ready.exists(): break
            time.sleep(0.02)
        self.assertTrue(ready.exists())
        self.poll(); self.register('billing', pane)
        self.write('ask.md', '@billing a real transport check\n'); self.commit('ask'); self.push(); self.poll()
        for _ in range(100):
            if received.exists(): break
            time.sleep(0.02)
        self.assertTrue(received.exists())
        message = received.read_text()
        self.assertTrue(message.startswith('# orchestrator-message '))
        self.assertIn(self.data()['events'][0]['id'], message)
        self.poll()
        self.assertEqual(received.read_text(), message)


if __name__ == '__main__':
    unittest.main()
