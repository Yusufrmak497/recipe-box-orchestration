from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _seed():
    client.post("/recipes", json={"title": "Pancakes", "tags": ["breakfast", "sweet"]})
    client.post("/recipes", json={"title": "Omelette", "tags": ["breakfast"]})
    client.post("/recipes", json={"title": "Soup", "tags": ["dinner"]})
    client.post("/recipes", json={"title": "Plain"})


def test_tag_filter_returns_only_matching_recipes():
    _seed()
    r = client.get("/recipes", params={"tag": "breakfast"})
    assert r.status_code == 200
    assert [rec["title"] for rec in r.json()] == ["Pancakes", "Omelette"]


def test_tag_filter_no_matches_returns_empty_list():
    _seed()
    r = client.get("/recipes", params={"tag": "dessert"})
    assert r.status_code == 200
    assert r.json() == []


def test_tag_filter_is_exact_match_not_substring():
    client.post("/recipes", json={"title": "Brunch", "tags": ["breakfast-ish"]})
    r = client.get("/recipes", params={"tag": "breakfast"})
    assert r.json() == []


def test_no_tag_returns_all_recipes():
    _seed()
    r = client.get("/recipes")
    assert r.status_code == 200
    assert len(r.json()) == 4
