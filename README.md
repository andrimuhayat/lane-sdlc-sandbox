# lane-sdlc-sandbox

Sandbox repo for a lane-based agentic SDLC setup with Claude Code: agent rules in `AGENTS.md`, permissions in `.claude/settings.json`, a `lane-workflow` skill, a vendored `security-audit` skill, and a CI gate that assigns each PR a lane (fast, standard, high-risk) from `risk-tiers.yml`.

The app is a small in-memory todo store. Run the tests with `npm test` (Node 22 or later).
