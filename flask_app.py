from __future__ import annotations
import sys, os, uuid, argparse, json
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, send_from_directory, abort
import storage
from models import Ingredient, Recipe

parser = argparse.ArgumentParser()
parser.add_argument('--data-file', default=os.environ.get('DATA_FILE'))
parser.add_argument('--defaults', default=os.environ.get('DEFAULTS_FILE'))
args, _ = parser.parse_known_args()

SERVER_MODE = args.data_file is not None
DEFAULTS_FILE = os.path.abspath(args.defaults) if args.defaults else None
if SERVER_MODE:
    storage.DATA_FILE = os.path.abspath(args.data_file)

app = Flask(__name__, static_folder="static", static_url_path="/static")


def _load():
    return storage.load_data()

def _save(ingredients, recipes):
    storage.save_data(ingredients, recipes)


# ── Config ────────────────────────────────────────────────────────────────────

@app.route("/api/config")
def config():
    return jsonify({"server_mode": SERVER_MODE, "has_defaults": DEFAULTS_FILE is not None})

@app.route("/api/defaults")
def defaults():
    if not DEFAULTS_FILE or not os.path.exists(DEFAULTS_FILE):
        abort(404)
    with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── Ingredients ───────────────────────────────────────────────────────────────

@app.route("/api/ingredients", methods=["GET"])
def list_ingredients():
    ings, _ = _load()
    return jsonify([i.to_dict() for i in ings])

@app.route("/api/ingredients", methods=["POST"])
def create_ingredient():
    ings, recipes = _load()
    d = request.json
    ing = Ingredient(name=d["name"], category=d["category"], source_url=d.get("source_url", ""))
    ings.append(ing)
    _save(ings, recipes)
    return jsonify(ing.to_dict()), 201

@app.route("/api/ingredients/<id>", methods=["PUT"])
def update_ingredient(id):
    ings, recipes = _load()
    ing = next((i for i in ings if i.id == id), None)
    if not ing:
        abort(404)
    d = request.json
    ing.name = d["name"]
    ing.category = d["category"]
    ing.source_url = d.get("source_url", "")
    _save(ings, recipes)
    return jsonify(ing.to_dict())

@app.route("/api/ingredients/<id>", methods=["DELETE"])
def delete_ingredient(id):
    ings, recipes = _load()
    ings = [i for i in ings if i.id != id]
    _save(ings, recipes)
    return "", 204


# ── Recipes ───────────────────────────────────────────────────────────────────

@app.route("/api/recipes", methods=["GET"])
def list_recipes():
    _, recipes = _load()
    return jsonify([r.to_dict() for r in recipes])

@app.route("/api/recipes", methods=["POST"])
def create_recipe():
    ings, recipes = _load()
    data = {**request.json, "id": str(uuid.uuid4())}
    recipe = Recipe.from_dict(data)
    recipes.append(recipe)
    _save(ings, recipes)
    return jsonify(recipe.to_dict()), 201

@app.route("/api/recipes/<id>", methods=["PUT"])
def update_recipe(id):
    ings, recipes = _load()
    idx = next((i for i, r in enumerate(recipes) if r.id == id), None)
    if idx is None:
        abort(404)
    recipes[idx] = Recipe.from_dict({**request.json, "id": id})
    _save(ings, recipes)
    return jsonify(recipes[idx].to_dict())

@app.route("/api/recipes/<id>", methods=["DELETE"])
def delete_recipe(id):
    ings, recipes = _load()
    recipes = [r for r in recipes if r.id != id]
    _save(ings, recipes)
    return "", 204


# ── Import / Export ───────────────────────────────────────────────────────────

@app.route("/api/import", methods=["POST"])
def import_data():
    data = request.json
    try:
        ings = [Ingredient.from_dict(d) for d in data["ingredients"]]
        recipes = [Recipe.from_dict(d) for d in data["recipes"]]
    except (KeyError, TypeError):
        abort(400)
    _save(ings, recipes)
    return "", 204


if __name__ == "__main__":
    print("Starting Fumula at http://localhost:5000")
    app.run(debug=True, port=5000)
