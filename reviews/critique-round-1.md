CORRECTNESS: FAIL
TESTS: PASS
CLARITY: FAIL
ISSUES:
1. main.py:215 The response adds a `"factor"` key, so it no longer has the same shape as `GET /recipes/{id}` (`id`, `title`, `ingredients`, `tags`). The rubric requires the same shape. -> Remove `recipe["factor"] = factor` and change the assertion in test_scaling.py:26 to compare the whole body against `GET /recipes/{id}` with only `ingredients` replaced.
2. main.py:178-181 `_format_qty` rounds to 2 decimals and then takes `int()`, so very small results turn into zero. For example, `"1/4 tsp salt"` with `factor=0.01` gives 0.0025, which rounds to 0.0 and comes out as `"0 tsp salt"`. A valid positive factor wipes out the quantity, so it is not "multiplied by F". -> Never output 0 for a non-zero result. Either keep enough significant digits (for example, format with `:.3g` and strip trailing zeros) or set a floor such as a minimum of 0.01. Add a test for it.
3. main.py:167 `_parse_qty` is the parsing helper but has no docstring. The rubric asks for a small, named helper with a docstring. -> Add a docstring listing the formats it accepts: integer, decimal with `.` or `,`, `a/b`, `w a/b`. Also say that it returns None for anything it can't parse, such as a zero denominator.
4. main.py:211 The route docstring doesn't state the supported formats, which the rubric requires. -> Extend it to list integers, decimals (`1.5`, `1,5`), fractions (`1/2`), mixed numbers (`1 1/2`) and ranges (`2-3`). Add that ingredients with no leading quantity are returned unchanged, and that `factor` must be greater than 0 and at most `MAX_SCALE_FACTOR`, otherwise the route returns 422.
VERDICT: REVISE

Notes:
- **Test run:** `pytest -q` passed all 46 tests.
- **Issue 2:** I found this by reading the code. My command to probe these edge cases needed approval, so it didn't run.
- **`factor` cap, not listed:** `factor` is capped at 100 (main.py:213), so a positive factor such as 150 gets 422. The rubric only names 0, negative, non-numeric and missing as 422 cases. I didn't list it because the cap looks like a deliberate guard, but the rubric doesn't explicitly allow it.
