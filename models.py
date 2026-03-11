from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Ingredient:
    name: str
    category: str       # "wood" | "resin" | "binder" | user-defined
    source_url: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "category": self.category, "source_url": self.source_url}

    @classmethod
    def from_dict(cls, d: dict) -> Ingredient:
        return cls(id=d["id"], name=d["name"], category=d["category"], source_url=d.get("source_url", ""))


@dataclass
class RecipeIngredient:
    ingredient_id: str
    percentage: float = 0.0     # % within its category (0–100)
    is_auto: bool = False       # True = this one auto-fills to keep sum at 100

    def to_dict(self) -> dict:
        return {"ingredient_id": self.ingredient_id, "percentage": self.percentage, "is_auto": self.is_auto}

    @classmethod
    def from_dict(cls, d: dict) -> RecipeIngredient:
        return cls(ingredient_id=d["ingredient_id"], percentage=d["percentage"], is_auto=d.get("is_auto", False))


@dataclass
class RecipeCategory:
    category: str
    percentage: float = 0.0     # % of total batch (0–100)
    is_auto: bool = False       # True = this one auto-fills
    ingredients: list[RecipeIngredient] = field(default_factory=list)

    def absolute_ingredient_pct(self, ri: RecipeIngredient) -> float:
        """Return ingredient's absolute % of the whole batch."""
        return self.percentage * ri.percentage / 100.0

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "percentage": self.percentage,
            "is_auto": self.is_auto,
            "ingredients": [i.to_dict() for i in self.ingredients],
        }

    @classmethod
    def from_dict(cls, d: dict) -> RecipeCategory:
        return cls(
            category=d["category"],
            percentage=d["percentage"],
            is_auto=d.get("is_auto", False),
            ingredients=[RecipeIngredient.from_dict(i) for i in d.get("ingredients", [])],
        )


@dataclass
class Recipe:
    name: str
    notes: str = ""
    categories: list[RecipeCategory] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "notes": self.notes,
            "categories": [c.to_dict() for c in self.categories],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Recipe:
        return cls(
            id=d["id"],
            name=d["name"],
            notes=d.get("notes", ""),
            categories=[RecipeCategory.from_dict(c) for c in d.get("categories", [])],
        )
