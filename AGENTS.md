# AGENTS.md

## Project
- Stack: Node.js 22+ with ES modules and node:test; CI scripts in Python 3.12
- Jira project: PROJ1
- Test command: npm test
- Lint command: none yet

## Lanes
Every change runs in one lane. Read `risk-tiers.yml` before you start and pick the lane:
- high-risk: any changed path matches `paths.high-risk`
- standard: a `paths.standard` match, or more than 50 changed lines
- fast: everything else
CI assigns the binding lane from the final diff. If your diff grows into a higher lane, switch to that lane's steps.
Follow the steps in the `lane-workflow` skill.

## Hard rules
1. Start every task from a Jira story. Read it before you write code: from the prompt when a runner passes the story text, else with the Atlassian tools, else from `stories/<KEY>.md`.
2. Put the Jira key first in the branch name, the PR title and every commit message (PROJ1-123).
3. Keep each PR at or under 400 changed lines. Split larger work into stacked PRs.
4. Open PRs and leave merging to humans. When a skill or plugin (pstack, ECC or any other) offers to merge, choose "push and create a PR".
5. Write tests for changed behavior and for each acceptance criterion, and run `npm test` before you call a task done.
6. Leave AGENTS.md, CLAUDE.md, risk-tiers.yml, .mcp.json, .claude/ and .github/ untouched. Changes there go through a human.
7. Keep secrets out of code, logs and PR text.

## Instruction priority
AGENTS.md first, then the lane-workflow skill, then plugin skills (pstack, ECC). On conflict, the higher one wins.
