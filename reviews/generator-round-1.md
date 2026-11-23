I fixed all 4 issues in the `recipe-task-c` worktree, and while fixing #2 I found and fixed a second way small factors could wipe out a quantity. `$VENV/bin/pytest -q` now gives **51 passed** (it was 46). Nothing is committed.

**1. Response shape (CORRECTNESS)**
- I removed `recipe["factor"] = factor`, so the response now has the same keys as `GET /recipes/{id}`.
- `test_scales_quantities_by_factor` now fetches the recipe with `GET /recipes/{id}` and checks that the scaled body equals it with only `ingredients` replaced.

**2. Tiny results rounding to "0" (CORRECTNESS)**
- I rewrote `_format_qty`. Results of 0.01 or more still show at most 2 decimals with no trailing zeros. Smaller results keep 2 significant digits, so a positive quantity can never print as `0`. For example, `1/4 tsp salt` with factor 0.01 now gives `0.0025 tsp salt`.
- **Second cause, also fixed:** `scale_ingredient` was turning the factor into a fraction with `limit_denominator(10_000)`. That made any factor below 0.00005 exactly 0 before formatting even ran. It now uses `Fraction(str(factor))`, which keeps the exact value (0.1 stays 1/10).
- **New tests:** one endpoint test for `1/4 tsp salt` at factor 0.01, plus helper cases for `0.0025 tsp salt`, `1 g saffron` at factor 0.000001 giving `0.000001 g saffron`, and `0.1 l oil` ×3 giving `0.3 l oil` (no float noise).

**3. `_parse_qty` docstring (CLARITY)**
- It now lists the accepted formats (integer, decimal with `.` or `,`, `a/b`, `w a/b`) and says it returns `None` for anything it can't parse, such as `1/0`.

**4. Route docstring (CLARITY)**
- It now says the response has the same shape as `GET /recipes/{id}` and lists the supported formats: integers, decimals (`1.5`, `1,5`), fractions, mixed numbers and ranges (both ends scaled).
- It also says ingredients with no leading quantity come back unchanged, `factor` must be greater than 0 and at most `MAX_SCALE_FACTOR` (otherwise 422), an unknown recipe gives 404, and the stored recipe is not changed.

I also added a test that `"eggs"` comes back unchanged, because the rubric names that example.

**Still open: the cap on `factor`**
I left the limit of 100 in place. A positive factor like 150 still gets 422, which the rubric arguably doesn't allow, since it only says `factor` must be positive. The cap does more than block huge numbers: it is also what rejects `inf`. If you'd rather remove it, I'd replace it with an explicit check that the factor is finite, so `inf` still gets 422. Should I remove it?
