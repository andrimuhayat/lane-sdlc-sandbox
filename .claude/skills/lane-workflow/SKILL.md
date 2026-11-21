---
name: lane-workflow
description: Use at the start of every coding task in this repo to read the Jira story, pick the lane from risk-tiers.yml, and follow its steps through to an open PR.
---

# Lane workflow

## 0. Start from the story
1. Get the Jira key (PROJ1-123) from the prompt or the engineer. With no key, stop and ask for one.
2. Read the story: summary, description, acceptance criteria, linked issues. Take it from the prompt when a runner passed the story text; otherwise use the Atlassian tools; otherwise read `stories/<KEY>.md`.
3. With missing or ambiguous acceptance criteria, stop and ask for the story to be updated.
4. Map each acceptance criterion to at least one test. Name tests with the key, for example `PROJ1_123 rejects an expired token`.
5. Create the branch `PROJ1-123-short-description`.

## 1. Pick the lane
List the files you expect to change and compare them with `paths` in `risk-tiers.yml`. Estimate changed lines. Pick the highest lane that applies and state it in one line before you start.

## 2. Fast lane
1. Make the change.
2. Run `npm test`.
3. Open a PR titled `PROJ1-123: <summary>` with the template. Lane: fast.

## 3. Standard lane
1. Write a plan of 3 to 8 lines: goal, files, tests.
2. Implement with tests, including one per acceptance criterion.
3. Review the diff read-only with pstack `interrogate` for correctness, missing tests and security. Without pstack, run one review subagent with the same brief. Fix what it finds.
4. Run `npm test`.
5. Open a PR titled `PROJ1-123: <summary>` with the plan under `## Plan` and the criterion-to-test map under `## Acceptance criteria`. Lane: standard.

## 4. High-risk lane
1. Write the plan: goal, files, data or API impact, rollback, tests. Open a draft PR titled `PROJ1-123: <summary>` with the plan under `## Plan`, then stop and ask for the plan to be approved.
2. After approval, implement test-first with pstack `tdd`: the failing test for each acceptance criterion, then the code.
3. Run `npm test`.
4. Fill `## Acceptance criteria` and mark the PR ready for review. CI runs the security audit. Fix every blocker it reports.
5. A code owner approves before merge.

## 5. Always
- One implementer per story. Parallel stories use separate branches.
- When any skill offers to merge, choose push and create a PR.
- Stop and ask when the lane is unclear.
