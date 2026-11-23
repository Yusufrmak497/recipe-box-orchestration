I fixed all 3 issues in the `recipe-task-c` worktree. `$VENV/bin/pytest -q` gives **59 passed**, and nothing is committed.

**1. Cap on `factor`**
- I removed `MAX_SCALE_FACTOR` and the `le=` bound; nothing else in the code referred to them. Any finite factor greater than 0 is now accepted.
- I replaced the cap with `allow_inf_nan=False`, so `inf`, `-inf`, `nan` and overflow values like `1e400` still return 422. Zero, negative, non-numeric and missing factors also still return 422.
- The route docstring now says `factor` must be "a finite number > 0".
- **Tests:** I removed the `"101"` case and added `1e400` to the 422 cases. A new test checks that factor 150 returns 200 with exactly `["30000 g flour", "75 tsp salt"]`.

**2. Thousands separator read as a decimal comma**
- The quantity pattern now accepts comma thousands groups (`\d{1,3}(?:,\d{3})+`). A comma counts as a decimal point only when 1–2 digits follow it (`,\d{1,2}(?!\d)`).
- `_parse_qty` removes the commas from a thousands-style number and turns a decimal comma into a dot. Its docstring and the route docstring now list thousands separators as a supported format.
- **Tests:** `1,000 g flour` ×2 gives `2000 g flour` (both as a helper case and through the endpoint), `1,250,000 mg` ×2 gives `2500000 mg`, and `1,25 l` ×2 still gives `2.5 l`.

**3. Rounding changing real quantities**
- I rewrote `_format_qty` to use exact fraction arithmetic instead of floats. It keeps at least 3 decimals and at least 3 significant digits, rounds half up, and strips trailing zeros.
- So `1/8` gives `0.125`, `3/8` gives `0.375`, and `0.0025` stays `0.0025`. A positive quantity still never prints as `0`.
- **Tests:** `1/8 tsp salt` ×1 gives `0.125 tsp salt`, ×3 gives `0.375 tsp salt`, and `1.5 cups milk` ×3 gives `4.5 cups milk`. The existing `1 egg` ×⅓ case now expects `0.333 egg` instead of `0.33 egg`.

**Still open**
- Values that need more than 3 decimals are still rounded. For example, 1/16 shows as `0.063` and 1/32 as `0.0313`. If the critic wants exact output for those too, the formatter would need to print every finite decimal in full.
- There is no upper limit on `factor` any more, so a very large one (say `1e300`) returns a quantity about 300 digits long. That's harmless, but you may want to set a limit the rubric allows.
