from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _create(title, ingredients):
    r = client.post("/recipes", json={"title": title, "ingredients": ingredients})
    assert r.status_code == 200
    return r.json()["id"]


def test_merges_and_dedupes_preserving_order():
    a = _create("Pancakes", ["flour", "milk", "eggs"])
    b = _create("Omelette", ["eggs", "milk", "cheese"])
    r = client.get(f"/shopping-list?ids={a},{b}")
    assert r.status_code == 200
    assert r.json() == ["flour", "milk", "eggs", "cheese"]


def test_dedupe_ignores_case_and_surrounding_whitespace():
    a = _create("A", ["Flour", "  milk "])
    b = _create("B", ["flour", "MILK", "salt"])
    r = client.get(f"/shopping-list?ids={a},{b}")
    assert r.status_code == 200
    # first-seen spelling wins, trimmed
    assert r.json() == ["Flour", "milk", "salt"]


def test_single_recipe():
    a = _create("Toast", ["bread", "butter"])
    r = client.get(f"/shopping-list?ids={a}")
    assert r.status_code == 200
    assert r.json() == ["bread", "butter"]


def test_repeated_id_counts_once():
    a = _create("Toast", ["bread", "butter"])
    r = client.get(f"/shopping-list?ids={a},{a}")
    assert r.status_code == 200
    assert r.json() == ["bread", "butter"]


def test_tolerates_spaces_in_ids():
    a = _create("A", ["x"])
    b = _create("B", ["y"])
    r = client.get(f"/shopping-list?ids={a}, {b}")
    assert r.status_code == 200
    assert r.json() == ["x", "y"]


def test_recipe_without_ingredients():
    a = _create("Water", [])
    b = _create("Tea", ["tea leaves"])
    r = client.get(f"/shopping-list?ids={a},{b}")
    assert r.status_code == 200
    assert r.json() == ["tea leaves"]


def test_blank_ingredients_are_skipped():
    a = _create("A", ["", "   ", "salt"])
    r = client.get(f"/shopping-list?ids={a}")
    assert r.status_code == 200
    assert r.json() == ["salt"]


def test_unknown_id_returns_404():
    a = _create("A", ["x"])
    r = client.get(f"/shopping-list?ids={a},99999")
    assert r.status_code == 404
    assert "99999" in r.json()["detail"]


def test_missing_ids_param_returns_422():
    r = client.get("/shopping-list")
    assert r.status_code == 422


def test_empty_ids_returns_422():
    r = client.get("/shopping-list?ids=")
    assert r.status_code == 422


def test_non_integer_id_returns_422():
    r = client.get("/shopping-list?ids=1,abc")
    assert r.status_code == 422


def test_too_many_ids_returns_422():
    ids = ",".join(str(i) for i in range(1, 102))
    r = client.get(f"/shopping-list?ids={ids}")
    assert r.status_code == 422
