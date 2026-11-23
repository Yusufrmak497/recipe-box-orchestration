# Week 7 — Agent Orchestration: The Recipe Box Sprint

**Student:** Yusuf Irmak

> **Process note:** Every agent in this lab is a Claude Code CLI session (`claude -p`). I set up the
> worktrees, rules and rubric, launched and supervised the agents, reviewed their diffs, and merged.

## 1. Concurrent agents (Part I)

**Tasks:** 1 (shopping list) and 2 (tag filter) from `docs/TASKS.md`.

**Worktree setup**
```bash
git worktree add ../recipe-task-a -b task-a    # agent A: shopping list
git worktree add ../recipe-task-b -b task-b    # agent B: tag filter
```
Both agents were launched as background processes **at the same moment** and ran side by side.
Agent A ran 22:30:51 → 22:31:55, and agent B ran 22:30:51 → 22:31:26 (see `evidence/agent-*-transcript.md`).
Each one's tool-call log shows it only touched files inside its own worktree.

| Agent | Branch | Result | Tests added |
|---|---|---|---|
| A | `task-a` → `fa3fb67` | `GET /shopping-list?ids=1,2,3`: ingredients from several recipes are merged, de-duplicated (ignoring case and spacing), and kept in order. Unknown ids → 404, and bad, empty or too many ids → 422 | 12 in `test_shopping_list.py` |
| B | `task-b` → `dd78c46` | `GET /recipes?tag=breakfast`: exact tag match, and no tag returns all recipes | 4 in `test_tag_filter.py` |

Both were merged with `--no-ff` (`7cd4a74`, `a482645`). **The merge had no conflicts**, and the combined suite gave
19 passed.

**How collisions were prevented**
1. **Separate worktrees.** Each agent has its own checkout and its own branch, so there are no shared files on disk.
2. **Separate test databases.** Before forking, I added an autouse fixture in `conftest.py` that gives every test a
   temporary SQLite file. Without it, both agents' test runs would write to the same `recipes.db`, and one
   agent's data would make the other's assertions flaky.
3. **Rules that reduce conflicts** in `AGENTS.md`: put new tests in a *new* file `test_<feature>.py` (not
   `test_main.py`), add new routes at the *end* of `main.py`, never touch `conftest.py`/`AGENTS.md` or other worktrees, and
   never commit or merge. That is why both changes to `main.py` landed in different hunks: B changed
   `list_recipes`, and A appended at the end of the file.
4. **The human integrates.** Agents can't commit. I reviewed each diff, then committed and merged one at a time, running the
   full suite after each merge.

**Remaining risks:** both tasks changed `main.py`. Had they edited the same function (e.g. two filters on
`GET /recipes`), git would have needed a manual merge, or the result could have been a *semantic* conflict that git
can't see: both merge cleanly, but the combined behaviour is wrong. That is why the suite runs after each merge. The
agents also shared one `.venv`, which is safe here only because neither agent installed anything.

## 2. Generator–critic loop (Part II): Task 3, ingredient scaling

**Setup:** [`scripts/generator_critic.sh`](scripts/generator_critic.sh), run in worktree `../recipe-task-c`.
- **Generator:** one Claude Code session, **resumed** each round (`--resume <session-id>`), so it remembers its
  own earlier choices. It is allowed to edit files and run pytest.
- **Critic:** a **fresh, read-only** session each round (no Edit/Write tools). It judges only the code against
  [`reviews/RUBRIC.md`](reviews/RUBRIC.md), which covers correctness, tests and clarity, and it signs off only when all three pass.
- The loop stops at `VERDICT: SIGN-OFF` (or after a maximum of 5 rounds).

**What happened** (full text: `reviews/generator-round-N.md`, `reviews/critique-round-N.md`):

| Round | Critic verdict | Issues raised | Generator's revision | Tests |
|---|---|---|---|---|
| 0 | n/a | n/a | Initial solution: parses ints, decimals, fractions, mixed numbers and ranges | 46 pass |
| 1 | **REVISE** (Correctness FAIL, Clarity FAIL) | ① it added a `"factor"` key, so the **response shape no longer matched** `GET /recipes/{id}`; ② `"1/4 tsp"` × 0.01 rendered as **`"0 tsp"`**; ③ the parse helper had no docstring; ④ the route docstring didn't list the formats | Removed `factor`, rewrote the formatter so it never prints 0, added docstrings | 51 pass |
| 2 | **REVISE** (Correctness FAIL) | ① a cap `factor ≤ 100` rejects valid positive factors; ② **`"1,000 g flour"` × 2 gave `"2 g flour"`** (the comma was read as a decimal point); ③ `"1/8 tsp"` became `"0.12"` instead of `0.125` | Removed the cap but kept `allow_inf_nan=False` (rejects `inf`/`nan`/`1e400`); a comma is a decimal point only before 1–2 digits; exact `Fraction` arithmetic with ≥3 significant digits | 59 pass |
| 3 | **SIGN-OFF** (all PASS) | none | n/a | 59 pass |

**Two revision rounds**, and each round found real bugs that the generator's own tests had missed. The
generator's tests were green at every stage.

**My check before merging:** I read the final diff and probed it directly:
`"200 g flour"×2 → "400 g flour"`, `"1 1/2 cups sugar"×2 → "3 cups sugar"`, `"1/8 tsp salt"×1 → "0.125 tsp salt"`,
`"1,000 g flour"×2 → "2000 g flour"`, `"0.1 l oil"×3 → "0.3 l oil"`, `"2-3 eggs"×2 → "4-6 eggs"`,
`"salt to taste"` unchanged. My one change was to move imports the generator had put mid-file (with
`# noqa: E402`) to the top. Merged as `aff64d3`, and the suite gave 59 passed.

**Observation:** the critic enforces the rubric *literally*. In round 2 it made the generator remove the
`factor ≤ 100` cap, a reasonable guard against absurd requests, because the rubric only said "positive number". The
generator kept the protection that matters (`inf`/`nan`/overflow rejected). Still, a rubric is a specification: if it
leaves something out, the critic will push to remove it.

## 3. Autonomy levels and supervision

| Agent | Could do | Could not do | Supervision |
|---|---|---|---|
| Concurrent agents A/B | Read, edit and write inside their worktree; run `pytest` only (`--allowedTools` allow-list, `acceptEdits`) | Any other shell command, git, network, other worktrees | Diff reviewed before commit; full suite after each merge |
| Generator | Same as A/B, in `recipe-task-c` | Commit, merge, other shell commands | Gated by the critic, then my diff review and probes |
| Critic | Read, `git diff`, `pytest` | **Any** edit (no Edit/Write tools) | Its verdicts were checked against the code by probing |

I gave the agents enough autonomy to write and test code without waiting for approval. Anything that changes
shared state (commits, merges, `main`) stayed with me. The critic's read-only setting matters: a critic
that could "just fix it" would stop being an independent check.

## 4. What I learned
<!-- Yusuf: 3–5 sentences on orchestrating agents. -->
