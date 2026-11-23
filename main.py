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
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
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
def list_recipes():
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY id").fetchall()
    return [_row_to_recipe(r) for r in rows]


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
