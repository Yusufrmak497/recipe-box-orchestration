"""Recipe Box — starter app for Week 7.

A tiny FastAPI service for recipes and tags, with a static frontend. Use it as the
playground for concurrent multi-agent work and a generator-critic loop.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload
    # open http://localhost:8000/
Test:
    pytest
"""
import json
import math
import re
import sqlite3
from contextlib import closing
from fractions import Fraction
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

BASE = Path(__file__).parent
DB_PATH = BASE / "recipes.db"

app = FastAPI(title="Recipe Box")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS recipes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                ingredients TEXT NOT NULL,  -- JSON list of strings
                tags        TEXT NOT NULL   -- JSON list of strings
            )"""
        )
        conn.commit()


init_db()


class RecipeIn(BaseModel):
    title: str
    ingredients: list[str] = []
    tags: list[str] = []


def _row_to_recipe(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": json.loads(row["ingredients"]),
        "tags": json.loads(row["tags"]),
    }


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/recipes")
def create_recipe(recipe: RecipeIn):
    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO recipes (title, ingredients, tags) VALUES (?, ?, ?)",
            (recipe.title, json.dumps(recipe.ingredients), json.dumps(recipe.tags)),
        )
        conn.commit()
        rid = cur.lastrowid
    return {"id": rid, **recipe.model_dump()}


@app.get("/recipes")
def list_recipes(tag: str | None = None):
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    recipes = [_row_to_recipe(r) for r in rows]
    if tag is not None:
        recipes = [rec for rec in recipes if tag in rec["tags"]]
    return recipes


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int):
    with closing(get_db()) as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown recipe")
    return _row_to_recipe(row)


MAX_SHOPPING_LIST_IDS = 100


def _parse_ids(raw: str) -> list[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise HTTPException(status_code=422, detail="ids must contain at least one recipe id")
    if len(parts) > MAX_SHOPPING_LIST_IDS:
        raise HTTPException(
            status_code=422, detail=f"at most {MAX_SHOPPING_LIST_IDS} ids allowed"
        )
    try:
        ids = [int(p) for p in parts]
    except ValueError:
        raise HTTPException(status_code=422, detail="ids must be comma-separated integers")
    return list(dict.fromkeys(ids))  # drop repeats, keep order


@app.get("/shopping-list")
def shopping_list(ids: str):
    """Merge ingredients of the given recipes into a de-duplicated list.

    Order follows the requested ids, then each recipe's ingredient order. Duplicates are
    detected case-insensitively after trimming whitespace; the first spelling seen wins.
    """
    recipe_ids = _parse_ids(ids)
    placeholders = ",".join("?" * len(recipe_ids))
    with closing(get_db()) as conn:
        rows = conn.execute(
            f"SELECT * FROM recipes WHERE id IN ({placeholders})", recipe_ids
        ).fetchall()
    by_id = {r["id"]: _row_to_recipe(r) for r in rows}
    missing = [rid for rid in recipe_ids if rid not in by_id]
    if missing:
        raise HTTPException(
            status_code=404, detail=f"unknown recipe id(s): {', '.join(map(str, missing))}"
        )

    seen: set[str] = set()
    items: list[str] = []
    for rid in recipe_ids:
        for ingredient in by_id[rid]["ingredients"]:
            name = ingredient.strip()
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                items.append(name)
    return items


# --- Ingredient scaling -------------------------------------------------------------


# A single quantity: mixed number ("1 1/2"), fraction ("1/2"), or a number with optional
# thousands separators ("1,000") and an optional decimal part ("0.5", or "1,5" — a comma
# counts as a decimal point only when 1-2 digits follow it, otherwise it's a thousands separator).
_QTY = r"\d+\s+\d+/\d+|\d+/\d+|(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+|,\d{1,2}(?!\d))?"
_THOUSANDS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
# Leading quantity, optionally a range ("2-3", "2 - 3"), followed by the rest of the text.
_LEADING_QTY = re.compile(rf"^(\s*)({_QTY})(?:(\s*-\s*)({_QTY}))?(?=\s|[^\d/.,]|$)(.*)$", re.S)


def _parse_qty(text: str) -> Fraction | None:
    """Parse one quantity token into an exact Fraction.

    Accepted formats: integer ("200"), integer with thousands separators ("1,000"),
    decimal with "." or "," ("1.5", "1,5"), simple fraction ("1/2") and mixed number
    ("1 1/2"). Returns None for anything it cannot parse, e.g. a zero denominator ("1/0").
    """
    if _THOUSANDS.fullmatch(text):
        text = text.replace(",", "")  # "1,000" -> "1000"
    else:
        text = text.replace(",", ".")  # decimal comma: "1,5" -> "1.5"
    try:
        if " " in text:  # mixed number
            whole, frac = text.split(None, 1)
            return Fraction(whole) + Fraction(frac)
        return Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None


def _format_qty(value: Fraction) -> str:
    """Format a quantity readably, using exact arithmetic (no float noise).

    Keeps at least 3 decimals and at least 3 significant digits, rounding half up, then
    strips trailing zeros: 1/8 -> "0.125", 1/3 -> "0.333", 0.0025 -> "0.0025", 400 -> "400".
    A non-zero quantity is therefore never rendered as "0".
    """
    if value <= 0:
        return "0"
    decimals = 3
    while value * 10**decimals < 100:  # fewer than 3 significant digits so far
        decimals += 1
    scaled = math.floor(value * 10**decimals + Fraction(1, 2))  # exact round-half-up
    digits = str(scaled).rjust(decimals + 1, "0")
    whole, frac = digits[:-decimals], digits[-decimals:].rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def scale_ingredient(ingredient: str, factor: float) -> str:
    """Scale the leading quantity of an ingredient string, e.g. "200 g flour" x2 -> "400 g flour".

    Ingredients without a leading number (e.g. "salt to taste") are returned unchanged.
    """
    m = _LEADING_QTY.match(ingredient)
    if not m:
        return ingredient
    lead, first, sep, second, rest = m.groups()
    f = Fraction(str(factor))  # exact decimal value of the factor, e.g. 0.1 -> 1/10
    q1 = _parse_qty(first)
    if q1 is None:
        return ingredient
    out = lead + _format_qty(q1 * f)
    if second is not None:
        q2 = _parse_qty(second)
        if q2 is None:
            return ingredient
        out += sep + _format_qty(q2 * f)
    return out + rest


@app.get("/recipes/{recipe_id}/scaled")
def get_scaled_recipe(
    recipe_id: int,
    factor: float = Query(..., gt=0, allow_inf_nan=False),
):
    """Return the recipe (same shape as GET /recipes/{id}) with scaled ingredient quantities.

    The leading quantity of each ingredient is multiplied by `factor`. Supported formats:
    integers ("200 g flour", "1,000 g"), decimals ("1.5", "1,5"), fractions ("1/2"), mixed
    numbers ("1 1/2") and ranges ("2-3", both ends scaled). Ingredients without a leading
    quantity ("salt to taste", "eggs") are returned unchanged. `factor` must be a finite
    number > 0, otherwise 422; an unknown recipe gives 404. The stored recipe is not
    modified.
    """
    recipe = get_recipe(recipe_id)
    recipe["ingredients"] = [scale_ingredient(i, factor) for i in recipe["ingredients"]]
    return recipe
