# lane-sdlc-sandbox

Sandbox repo for a lane-based agentic SDLC setup with Claude Code: agent rules in `AGENTS.md`, permissions in `.claude/settings.json`, a `lane-workflow` skill, a vendored `security-audit` skill, and a local pre-push gate that assigns each branch a lane (fast, standard, high-risk) from `risk-tiers.yml`.

The app is a small in-memory todo store. Run the tests with `npm test` (Node 22 or later).

## Local gate

Every `git push` of a branch other than `main` runs `.githooks/pre-push`. The hook takes `.github/scripts/local-gate.sh` from the remote's `main` and runs it on the pushed commit:

1. `npm test`
2. `classify.py` assigns the lane, with the rules in `risk-tiers.yml` on the remote `main`
3. high-risk only: the `security-audit` skill reviews the diff with your Claude login. A `block` verdict, or no verdict, blocks the push.

Logs and the audit output go to `.git/gate/`. Nothing runs on GitHub; GitHub hosts the code and the PRs.

One-time setup per clone:

```sh
git config core.hooksPath .githooks
uv venv && uv pip install pyyaml==6.0.4
claude          # accept the trust dialog for this folder, then /exit
```

`PR_LABELS=lane:high-risk git push` raises the lane, and `PR_LABELS=size-cap-exception` lets a PR exceed 400 changed lines. Both are for humans.
