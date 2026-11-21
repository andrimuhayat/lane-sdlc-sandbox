#!/bin/bash
# Local lane gate. .githooks/pre-push runs the copy of this file on the remote
# main for each branch pushed, so a branch cannot change the gate that judges it.
#
# Usage: local-gate.sh BASE HEAD
#   BASE  the remote main commit; the classifier and risk-tiers.yml come from it
#   HEAD  the commit being pushed
#
# Steps, on a temporary checkout of HEAD under .git/gate/:
#   1. npm test
#   2. classify.py from BASE assigns the lane
#   3. high-risk only: the security-audit skill reviews BASE...HEAD with the
#      engineer's Claude login (no API key); any verdict other than pass fails
#
# PR_LABELS (comma-separated) raises the lane or grants size-cap-exception, as in
# classify.py. Only a human sets it.
# Exit codes: 0 pass, 1 gate failed, 2 setup error.

set -uo pipefail

BASE="${1:?usage: local-gate.sh BASE HEAD}"
HEAD="${2:?usage: local-gate.sh BASE HEAD}"

say() { echo "gate: $*" >&2; }

ROOT=$(git rev-parse --show-toplevel) || exit 2
GITDIR=$(cd "$(git rev-parse --git-common-dir)" && pwd) || exit 2
OUT="$GITDIR/gate"
SHORT=$(git rev-parse --short "$HEAD") || { say "setup error: unknown commit $HEAD"; exit 2; }
WT="$OUT/wt-$SHORT"
mkdir -p "$OUT"

cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1; git worktree prune >/dev/null 2>&1; }
trap cleanup EXIT

fail() { say "FAILED: $*"; exit 1; }

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=python3
"$PY" -c 'import yaml' 2>/dev/null || { say "setup error: PyYAML missing. Run: uv venv && uv pip install pyyaml==6.0.4"; exit 2; }
command -v jq >/dev/null || { say "setup error: jq missing"; exit 2; }

cleanup
git worktree add --quiet --detach "$WT" "$HEAD" || { say "setup error: cannot check out $SHORT"; exit 2; }

# 1. Tests on the pushed commit
if ! (cd "$WT" && npm test) < /dev/null > "$OUT/$SHORT-test.log" 2>&1; then
  fail "npm test (log: $OUT/$SHORT-test.log)"
fi
say "npm test passed"

# 2. Lane, with the classifier and rules from BASE
git show "$BASE:.github/scripts/classify.py" > "$OUT/classify.py" 2>/dev/null \
  || { say "setup error: $BASE has no .github/scripts/classify.py"; exit 2; }
LANE_FILE="$OUT/$SHORT-lane.txt"
: > "$LANE_FILE"
(cd "$WT" && GITHUB_OUTPUT="$LANE_FILE" "$PY" "$OUT/classify.py" "$BASE" "$HEAD") < /dev/null >&2
rc=$?
[ "$rc" -eq 0 ] || fail "classify exit $rc"
LANE=$(sed -n 's/^lane=//p' "$LANE_FILE")
[ -n "$LANE" ] || fail "classify printed no lane"
if [ "$LANE" != "high-risk" ]; then
  say "passed: lane $LANE"
  exit 0
fi

# 3. Security audit on high-risk changes
SCHEMA='{"type":"object","additionalProperties":false,"required":["verdict","findings"],"properties":{"verdict":{"type":"string","enum":["pass","block"]},"findings":{"type":"array","items":{"type":"object","additionalProperties":false,"required":["file","line","severity","title","fix"],"properties":{"file":{"type":"string"},"line":{"type":"integer"},"severity":{"type":"string","enum":["blocker","major","minor"]},"title":{"type":"string"},"fix":{"type":"string"}}}}}}'
AUDIT="$OUT/$SHORT-audit.json"
say "lane high-risk: running security-audit on $BASE...$SHORT"
(cd "$WT" && claude -p "/security-audit Guidance mode only: focused security review of the change from $BASE to $HEAD (run: git diff $BASE...$HEAD). Do not run the six-phase workflow, create an output directory, write files, launch agents, or ask questions. Use verdict block for any exploitable issue. List every finding with file, line and fix. Never print secret values; cite file and line only." \
  --setting-sources project,local \
  --add-dir . \
  --permission-mode dontAsk \
  --allowedTools "Read(./**)" "Grep" "Glob" "Bash(git diff *)" "Bash(git log *)" "Bash(git show *)" \
  --disallowedTools "Bash(git diff *--output*)" "Bash(git diff *--no-index*)" "Read(./.git/**)" \
  --max-turns 60 \
  --max-budget-usd 5 \
  --output-format json \
  --json-schema "$SCHEMA") < /dev/null > "$AUDIT" 2> "$OUT/$SHORT-audit.stderr"

verdict=$(jq -r '.structured_output.verdict // empty' "$AUDIT" 2>/dev/null)
jq -r '.structured_output.findings[]? | "gate:   \(.severity) \(.file):\(.line) \(.title)"' "$AUDIT" >&2 2>/dev/null
jq -r '"gate:   cost_usd \(.total_cost_usd), turns \(.num_turns)"' "$AUDIT" >&2 2>/dev/null
if [ -z "$verdict" ]; then
  fail "security-audit returned no verdict (output: $AUDIT, stderr: $OUT/$SHORT-audit.stderr)"
fi
[ "$verdict" = "pass" ] || fail "security-audit verdict $verdict"
say "passed: lane high-risk, security-audit pass"
