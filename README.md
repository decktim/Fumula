# Fumula

A web app for creating and managing incense recipes. Build recipes from ingredient categories, set proportions with interactive sliders, and generate printable recipe sheets.

## Features

- Manage an ingredient library organized by category (wood, resin, binder, etc.)
- Create recipes with category-level and per-ingredient percentage breakdowns
- Auto-balancing: designate one member per group to automatically fill to 100%
- Visual donut chart showing recipe composition
- Print recipe sheets as HTML tables with target gram calculations
- Export and import data as JSON

## Usage

### Shared/deployed mode (each user has their own data in their browser)

```bash
python flask_app.py
```

Optionally provide a defaults file that new users will receive on their first visit:

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

## Installation

```bash
pip install flask gunicorn
python flask_app.py
```

Then open `http://localhost:5000`.

## Deployment (Render)

Set the start command to:
```
gunicorn flask_app:app
```

To serve a defaults file on Render, commit `defaults.json` to the repo and set the start command to:
```
gunicorn flask_app:app -- --defaults defaults.json
```
