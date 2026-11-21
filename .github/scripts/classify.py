#!/usr/bin/env python3
"""Assign a pull request its lane from risk-tiers.yml.

Usage: classify.py BASE HEAD

BASE and HEAD are git revisions. The rules come from BASE, so a PR cannot
change the rules it is judged by. Labels come from PR_LABELS (comma-separated)
and only raise the lane.

Prints "Lane: <lane>" and writes lane=<lane> to $GITHUB_OUTPUT when set.
Exit codes: 0 lane assigned, 1 size cap exceeded without the exception label,
2 setup error (rules file missing or invalid, bad revision).
"""

import os
import subprocess
import sys
from fnmatch import fnmatchcase

import yaml

LANES = ("fast", "standard", "high-risk")
RULES_FILE = "risk-tiers.yml"
REQUIRED = ("fast_max_lines", "size_cap_lines", "size_cap_exception_label", "paths")


class SetupError(Exception):
    pass


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SetupError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def load_rules(base):
    rules = yaml.safe_load(git("show", f"{base}:{RULES_FILE}"))
    if not isinstance(rules, dict) or rules.get("version") != 1:
        raise SetupError(f"{RULES_FILE} at {base} is missing version: 1")
    missing = [key for key in REQUIRED if key not in rules]
    if missing:
        raise SetupError(f"{RULES_FILE} at {base} is missing {', '.join(missing)}")
    return rules


def changed_files(base, head):
    out = git("diff", "--numstat", "--no-renames", "-z", f"{base}...{head}")
    files = []
    for entry in filter(None, out.split("\0")):
        added, deleted, path = entry.split("\t", 2)
        lines = 0 if added == "-" else int(added) + int(deleted)
        files.append((path, lines))
    return files


def matches(path, patterns):
    return any(fnmatchcase(path, pattern) for pattern in patterns or ())


def classify(rules, files, labels):
    paths = rules["paths"]
    counted = sum(n for path, n in files if not matches(path, rules.get("size_exclude")))
    lane = "fast"
    reasons = []

    def raise_to(target, reason):
        nonlocal lane
        reasons.append(reason)
        if LANES.index(target) > LANES.index(lane):
            lane = target

    for path, _ in files:
        if matches(path, paths.get("high-risk")):
            raise_to("high-risk", f"high-risk path: {path}")
        elif matches(path, paths.get("standard")):
            raise_to("standard", f"standard path: {path}")
    if counted > rules["fast_max_lines"]:
        raise_to("standard", f"{counted} changed lines > fast_max_lines {rules['fast_max_lines']}")
    for label in labels:
        if label.startswith("lane:") and label[len("lane:"):] in LANES:
            raise_to(label[len("lane:"):], f"label {label}")

    over_cap = counted > rules["size_cap_lines"] and rules["size_cap_exception_label"] not in labels
    return lane, counted, reasons, over_cap


def append(env_var, text):
    target = os.environ.get(env_var)
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(text)


def main(argv):
    if len(argv) != 3:
        print("usage: classify.py BASE HEAD", file=sys.stderr)
        return 2
    base, head = argv[1], argv[2]
    labels = [label.strip() for label in os.environ.get("PR_LABELS", "").split(",") if label.strip()]

    try:
        rules = load_rules(base)
        files = changed_files(base, head)
    except SetupError as error:
        print(f"classify: {error}", file=sys.stderr)
        return 2

    lane, counted, reasons, over_cap = classify(rules, files, labels)
    print(f"Lane: {lane}")
    print(f"Changed lines counted: {counted} in {len(files)} files")
    for reason in reasons[:20]:
        print(f"- {reason}")

    append("GITHUB_OUTPUT", f"lane={lane}\nlines={counted}\n")
    append("GITHUB_STEP_SUMMARY", f"### Lane: {lane}\n\n{counted} changed lines counted.\n")

    if over_cap:
        print(
            f"classify: {counted} changed lines exceed size_cap_lines {rules['size_cap_lines']}. "
            f"Split the PR, or add the label {rules['size_cap_exception_label']}.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
