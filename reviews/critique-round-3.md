CORRECTNESS: PASS
TESTS: PASS
CLARITY: PASS
ISSUES:
None. No rubric violations found.
VERDICT: SIGN-OFF

What I checked (project: recipe-box-orchestration, worktree `recipe-task-c`):

- **Tests:** `pytest -q` gives 59 passed, 0 failed. The only warning is a starlette/httpx deprecation that has nothing to do with this task.
- **Correctness:**
  - The route at `main.py:228` returns `get_recipe(...)` with only the ingredients replaced, so the shape matches `GET /recipes/{id}`.
  - `get_recipe` builds a new dict from the database row, so the stored recipe is never written back.
  - Integers, decimals, fractions and mixed numbers are parsed exactly with `Fraction`.
  - Ingredients with no leading number don't match the pattern and come back unchanged.
  - `_format_qty` rounds exactly, so there's no float noise and no trailing `.0`.
  - A quantity of 0 returns early. Without that check, the loop on line 198 would never end.
  - `Query(gt=0, allow_inf_nan=False)` rejects 0, negative numbers, text, a missing factor, nan, inf and 1e400 with 422. An unknown recipe gives 404 through `get_recipe`.
- **Test coverage (`test_scaling.py`):** every rubric bullet has at least one test, and the scaling results are checked as exact strings (for example `"0.1 l oil"` ×3 gives `"0.3 l oil"`).
- **Clarity:** parsing lives in `_parse_qty`, formatting in `_format_qty` and scaling in `scale_ingredient`, each with a docstring. The route docstring lists the supported formats. There's no dead code: both `None` branches can actually be reached, through inputs like `"1/0"` and `"2-1/0"`.

The permission prompt blocked my extra Python probe, so I checked the edge cases by reading the code. I left out two small style points because the rubric doesn't cover them: the imports in the middle of `main.py` (marked `noqa: E402`) and the short names `m` and `f` in `scale_ingredient`.
