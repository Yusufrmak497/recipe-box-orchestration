#!/usr/bin/env bash
# Generator–critic loop for Task 3, run in the recipe-task-c worktree.
# The generator keeps one Claude Code session (resumed each round); the critic is a fresh,
# read-only session every round so it judges the code, not the conversation.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; WT="$ROOT/../recipe-task-c"; VENV="$ROOT/.venv"
MAX_ROUNDS=${MAX_ROUNDS:-5}; GEN_SESSION=$(uuidgen | tr 'A-Z' 'a-z')
TASK='3. Ingredient scaling — GET /recipes/{id}/scaled?factor=2 returns the recipe with quantities scaled (assume ingredients like "200 g flour").'
run_claude() { env -u ANTHROPIC_API_KEY VENV="$VENV" claude -p "$@" --output-format json < /dev/null 2>/dev/null \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['result'])"; }
cd "$WT"
echo "## Round 0 — generator (initial solution)" | tee "$ROOT/reviews/generator-round-0.md"
run_claude "Read AGENTS.md (VENV=$VENV). Implement: \"$TASK\". Tests go in test_scaling.py. Run \$VENV/bin/pytest -q until green. Do not commit. Report what you built." \
  --session-id "$GEN_SESSION" --permission-mode acceptEdits \
  --allowedTools "Read,Edit,Write,Grep,Glob,Bash($VENV/bin/pytest:*)" >> "$ROOT/reviews/generator-round-0.md"
for round in $(seq 1 "$MAX_ROUNDS"); do
  run_claude "You are a strict CRITIC. Do not edit files. Read $ROOT/reviews/RUBRIC.md, then review the implementation of Task 3 in this worktree (git diff, main.py, test_scaling.py) and run \$VENV/bin/pytest -q (VENV=$VENV). You may also probe behaviour by reading code carefully. Output exactly:
CORRECTNESS: PASS|FAIL
TESTS: PASS|FAIL
CLARITY: PASS|FAIL
ISSUES:
1. <file:line> <concrete problem> -> <required fix>
VERDICT: SIGN-OFF|REVISE
Only list issues that violate the rubric." \
    --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash($VENV/bin/pytest:*)" > "$ROOT/reviews/critique-round-$round.md"
  echo "--- critique round $round: $(grep -E '^VERDICT' "$ROOT/reviews/critique-round-$round.md")"
  grep -q 'VERDICT: SIGN-OFF' "$ROOT/reviews/critique-round-$round.md" && { echo "critic signed off after $round round(s)"; exit 0; }
  run_claude "The critic reviewed your work against $ROOT/reviews/RUBRIC.md and asked for revisions:

$(cat "$ROOT/reviews/critique-round-$round.md")

Fix every issue. Run \$VENV/bin/pytest -q until green. Do not commit. Report what you changed per issue." \
    --resume "$GEN_SESSION" --permission-mode acceptEdits \
    --allowedTools "Read,Edit,Write,Grep,Glob,Bash($VENV/bin/pytest:*)" > "$ROOT/reviews/generator-round-$round.md"
  echo "--- generator revision $round done"
done
echo "no sign-off after $MAX_ROUNDS rounds"; exit 1
