# Fumula

Fumula helps you track your incense ingredients, build recipes from them, and print measurement sheets.

## What is Fumula?

Fumula is a tool for managing incense recipes. It keeps track of the ingredients you have on hand, helps you create new recipes from those ingredients, and generates printable recipe sheets with gram measurements.

Ingredients are organized into categories (wood, resin, binder, or any category you define). When building a recipe, you first set the blend of categories, then within each category set the blend of individual ingredients — all by percentage. When you print a recipe sheet, you specify one or more target batch sizes and the sheet calculates the gram amounts for every ingredient.

Your data is stored in your browser — nothing is saved to a server. Use **Export JSON** to save a local backup at any time, and **Import JSON** to restore it later.

A default profile with sample ingredients and recipes is available via **Load Defaults** (if configured). You can clear it and start fresh at any time.

## Features

- Ingredient library organized by category (wood, resin, binder, or custom)
- Recipes with category-level and per-ingredient percentage breakdowns
- Auto-balancing: one member per group automatically fills to 100%
- Group related recipes into families (e.g. two versions of the same base)
- Visual donut chart showing recipe composition
- Printable recipe sheets with target gram calculations
- Export and import data as JSON

## Running locally

```bash
pip install flask gunicorn
python flask_app.py
```

Then open `http://localhost:5000`.

## Usage modes

### Shared/deployed mode (each user's data lives in their own browser)

```bash
python flask_app.py
```

Optionally provide a defaults file that new users receive on first visit:

```bash
python flask_app.py --defaults defaults.json
```

### Personal/local mode (data stored in a file on the server)

```bash
python flask_app.py --data-file myrecipes.json
```

The file will be created if it doesn't exist. All changes are saved immediately.

## Navbar buttons

| Button | When visible | What it does |
|--------|-------------|--------------|
| Load Defaults | localStorage mode + `--defaults` specified | Replaces your data with the defaults file |
| Reset Data | localStorage mode | Clears all your ingredients and recipes |
| Export JSON | Always | Downloads your data as a JSON file |
| Import JSON | Always | Loads data from a JSON file |

## Deployment (Render)

Set the start command to:
```
gunicorn flask_app:app
```

To serve a defaults file on Render, commit `defaults.json` to the repo and set the environment variable `DEFAULTS_FILE=defaults.json` in Render's dashboard.

> **Note:** Render's free tier spins down inactive services. If no one has accessed the app in a while, the first load may take a minute.
