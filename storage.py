from __future__ import annotations
import json
import os
from models import Ingredient, Recipe

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

def load_data() -> tuple[list[Ingredient], list[Recipe]]:
    if not os.path.exists(DATA_FILE):
        return [], []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        ingredients = [Ingredient.from_dict(d) for d in raw.get("ingredients", [])]
        recipes = [Recipe.from_dict(d) for d in raw.get("recipes", [])]
        return ingredients, recipes
    except Exception:
        return [], []


def save_data(ingredients: list[Ingredient], recipes: list[Recipe]) -> None:
    data = {
        "ingredients": [i.to_dict() for i in ingredients],
        "recipes": [r.to_dict() for r in recipes],
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
