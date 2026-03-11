from __future__ import annotations
import json
import os
from models import Ingredient, Recipe

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

DEFAULT_INGREDIENTS = [
    Ingredient(name="White Cedar",    category="wood",   source_url=""),
    Ingredient(name="Red Sandalwood", category="wood",   source_url=""),
    Ingredient(name="Palo Santo",     category="wood",   source_url=""),
    Ingredient(name="Frankincense",   category="resin",  source_url=""),
    Ingredient(name="Myrrh",          category="resin",  source_url=""),
    Ingredient(name="Benzoin",        category="resin",  source_url=""),
    Ingredient(name="Makko",          category="binder", source_url=""),
]


def load_data() -> tuple[list[Ingredient], list[Recipe]]:
    if not os.path.exists(DATA_FILE):
        return list(DEFAULT_INGREDIENTS), []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        ingredients = [Ingredient.from_dict(d) for d in raw.get("ingredients", [])]
        recipes = [Recipe.from_dict(d) for d in raw.get("recipes", [])]
        return ingredients, recipes
    except Exception:
        return list(DEFAULT_INGREDIENTS), []


def save_data(ingredients: list[Ingredient], recipes: list[Recipe]) -> None:
    data = {
        "ingredients": [i.to_dict() for i in ingredients],
        "recipes": [r.to_dict() for r in recipes],
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
