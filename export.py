from __future__ import annotations
import os
import webbrowser
from models import Recipe, Ingredient

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "recipe_sheet.html")

CSS = """
body { font-family: Georgia, serif; margin: 20px; color: #222; }
h1 { font-size: 1.1em; margin-bottom: 4px; }
.recipe { margin-bottom: 40px; page-break-after: always; }
.recipe:last-child { page-break-after: avoid; }
table { border-collapse: collapse; width: auto; margin-top: 8px; }
th, td { border: 1px solid #aaa; padding: 6px 12px; text-align: right; }
th:first-child, td:first-child { text-align: left; }
th:nth-child(2), td:nth-child(2) { text-align: center; }
th { background: #f0ece4; }
.notes { font-style: italic; color: #666; font-size: 0.9em; margin-top: 4px; }
@media print {
    body { margin: 0; }
    .recipe { page-break-after: always; }
    .recipe:last-child { page-break-after: avoid; }
}
"""


def _ingredient_rows(recipe: Recipe, ingredients: list[Ingredient], target_grams: list[float]) -> list[dict]:
    """Return flat list of {name, category, abs_pct, amounts} for each recipe ingredient."""
    rows = []
    for rc in recipe.categories:
        for ri in rc.ingredients:
            ing = next((i for i in ingredients if i.id == ri.ingredient_id), None)
            name = ing.name if ing else f"(unknown)"
            abs_pct = rc.percentage * ri.percentage / 100.0
            amounts = [abs_pct / 100.0 * g for g in target_grams]
            rows.append({
                "name": name,
                "category": rc.category.capitalize(),
                "abs_pct": abs_pct,
                "amounts": amounts,
            })
    return rows


def _recipe_table(recipe: Recipe, ingredients: list[Ingredient], target_grams: list[float]) -> str:
    rows = _ingredient_rows(recipe, ingredients, target_grams)

    gram_headers = "".join(f"<th>{g:g}g</th>" for g in target_grams)
    header = f"<tr><th>Ingredient</th><th>Category</th><th>% of Batch</th>{gram_headers}</tr>"

    body_rows = []
    for r in rows:
        gram_cells = "".join(f"<td>{a:.3f}</td>" for a in r["amounts"])
        body_rows.append(
            f"<tr><td>{r['name']}</td><td>{r['category']}</td>"
            f"<td>{r['abs_pct']:.1f}%</td>{gram_cells}</tr>"
        )

    notes_html = f'<p class="notes">{recipe.notes}</p>' if recipe.notes else ""
    return (
        f'<div class="recipe">'
        f"<h1>{recipe.name}</h1>"
        f"{notes_html}"
        f"<table><thead>{header}</thead><tbody>{''.join(body_rows)}</tbody></table>"
        f"</div>"
    )


def generate_and_open(recipes: list[Recipe], ingredients: list[Ingredient], target_grams: list[float]) -> None:
    """Generate HTML recipe sheet and open in default browser."""
    tables = "\n".join(_recipe_table(r, ingredients, target_grams) for r in recipes)
    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>Recipe Sheet</title><style>{CSS}</style></head><body>{tables}</body></html>"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(f"file:///{OUTPUT_FILE.replace(os.sep, '/')}")
