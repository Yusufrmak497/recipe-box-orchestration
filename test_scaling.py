import pytest
from fastapi.testclient import TestClient

from main import app, scale_ingredient

client = TestClient(app)


def _create(ingredients, title="Pancakes", tags=None):
    r = client.post(
        "/recipes", json={"title": title, "ingredients": ingredients, "tags": tags or []}
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_scales_quantities_by_factor():
    rid = _create(["200 g flour", "2 eggs", "300 ml milk"], tags=["breakfast"])
    original = client.get(f"/recipes/{rid}").json()
    r = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert r.status_code == 200
    # Same shape as GET /recipes/{id}; only the ingredients differ.
    assert r.json() == {**original, "ingredients": ["400 g flour", "4 eggs", "600 ml milk"]}


def test_scaling_does_not_modify_stored_recipe():
    rid = _create(["200 g flour"])
    client.get(f"/recipes/{rid}/scaled?factor=3")
    assert client.get(f"/recipes/{rid}").json()["ingredients"] == ["200 g flour"]


def test_fractional_factor():
    rid = _create(["200 g flour", "3 eggs"])
    r = client.get(f"/recipes/{rid}/scaled?factor=0.5")
    assert r.status_code == 200
    assert r.json()["ingredients"] == ["100 g flour", "1.5 eggs"]


@pytest.mark.parametrize(
    "ingredient, factor, expected",
    [
        ("200 g flour", 2, "400 g flour"),
        ("200g flour", 2, "400g flour"),
        ("0.5 l water", 3, "1.5 l water"),
        ("1,5 kg potatoes", 2, "3 kg potatoes"),
        ("1/2 cup sugar", 2, "1 cup sugar"),
        ("1 1/2 cups milk", 2, "3 cups milk"),
        ("2-3 cloves garlic", 2, "4-6 cloves garlic"),
        ("1 egg", 1 / 3, "0.333 egg"),
        ("1/8 tsp salt", 1, "0.125 tsp salt"),
        ("1/8 tsp salt", 3, "0.375 tsp salt"),
        ("1,000 g flour", 2, "2000 g flour"),
        ("1,250,000 mg salt", 2, "2500000 mg salt"),
        ("1,25 l water", 2, "2.5 l water"),
        ("1.5 cups milk", 3, "4.5 cups milk"),
        ("0.1 l oil", 3, "0.3 l oil"),
        ("1/4 tsp salt", 0.01, "0.0025 tsp salt"),
        ("1 g saffron", 0.000001, "0.000001 g saffron"),
        ("salt to taste", 2, "salt to taste"),
        ("eggs", 2, "eggs"),
        ("", 2, ""),
        ("pinch of salt", 2, "pinch of salt"),
        ("1/0 cup nonsense", 2, "1/0 cup nonsense"),
        ("2 eggs, beaten", 1.5, "3 eggs, beaten"),
    ],
)
def test_scale_ingredient(ingredient, factor, expected):
    assert scale_ingredient(ingredient, factor) == expected


def test_tiny_factor_never_rounds_quantity_to_zero():
    rid = _create(["1/4 tsp salt"])
    r = client.get(f"/recipes/{rid}/scaled?factor=0.01")
    assert r.status_code == 200
    assert r.json()["ingredients"] == ["0.0025 tsp salt"]


def test_only_leading_quantity_is_scaled():
    rid = _create(["2 tins of 400 g tomatoes"])
    r = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert r.json()["ingredients"] == ["4 tins of 400 g tomatoes"]


def test_recipe_without_ingredients():
    rid = _create([])
    r = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert r.status_code == 200
    assert r.json()["ingredients"] == []


def test_unknown_recipe_returns_404():
    r = client.get("/recipes/99999/scaled?factor=2")
    assert r.status_code == 404


def test_missing_factor_returns_422():
    rid = _create(["200 g flour"])
    assert client.get(f"/recipes/{rid}/scaled").status_code == 422


def test_large_factor_is_allowed():
    rid = _create(["200 g flour", "1/2 tsp salt"])
    r = client.get(f"/recipes/{rid}/scaled?factor=150")
    assert r.status_code == 200
    assert r.json()["ingredients"] == ["30000 g flour", "75 tsp salt"]


def test_thousands_separator_endpoint():
    rid = _create(["1,000 g flour"])
    r = client.get(f"/recipes/{rid}/scaled?factor=2")
    assert r.json()["ingredients"] == ["2000 g flour"]


@pytest.mark.parametrize("factor", ["0", "-1", "abc", "nan", "inf", "-inf", "1e400"])
def test_invalid_factor_returns_422(factor):
    rid = _create(["200 g flour"])
    r = client.get(f"/recipes/{rid}/scaled?factor={factor}")
    assert r.status_code == 422
