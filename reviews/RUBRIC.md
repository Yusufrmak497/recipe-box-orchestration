# Critic rubric — Task 3: Ingredient scaling

Score each criterion PASS or FAIL. Sign off only if **all three** pass.

## 1. Correctness
- `GET /recipes/{id}/scaled?factor=F` returns the recipe (same shape as `GET /recipes/{id}`) with leading
  quantities multiplied by F, for example `"200 g flour"` → `"400 g flour"` when F=2.
- Handles integers, decimals (`1.5 cups milk`), simple fractions (`1/2 tsp salt`) and mixed numbers
  (`1 1/2 cups sugar`).
- Ingredients without a leading quantity (`"salt to taste"`, `"eggs"`) are returned unchanged.
- Output numbers are readable: no float noise like `0.30000000000000004`, and no trailing `.0`.
- `factor` must be a positive number. 0, negative, non-numeric or missing gives 422. An unknown recipe gives 404.
- The stored recipe is never modified.

## 2. Tests
- Every bullet above has at least one test, in `test_scaling.py`.
- The tests assert exact output strings, not only status codes.

## 3. Clarity
- Parsing is in a small, named helper with a docstring, not inline in the route.
- No dead code, and names are clear. The route has a docstring that states the supported formats.
