from __future__ import annotations
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
from models import Ingredient, Recipe, RecipeCategory, RecipeIngredient
import copy


class RecipeEditor(tk.Toplevel):
    """
    Modal dialog for creating or editing a recipe.

    Layout
    ------
    - Recipe name entry at the top
    - "Category Percentages" section: one row per category in the recipe
      (radio | name | slider | entry%)
    - Per-category ingredient sections, each with the same row style
    - "Add ingredient" button per category section
    - Notes text area
    - Save / Cancel buttons
    """

    def __init__(self, parent, recipe: Recipe | None, app):
        super().__init__(parent)
        self.title("New Recipe" if recipe is None else f"Edit — {recipe.name}")
        self.minsize(640, 500)
        self.grab_set()
        self.result: Recipe | None = None
        self._app = app

        # Work on a deep copy so cancelling doesn't mutate the original
        self._recipe: Recipe = copy.deepcopy(recipe) if recipe else self._blank_recipe()

        # Guard flag: prevents slider↔entry callbacks from re-entering each other
        self._updating = False

        # Widget maps keyed by (group_key, member_idx)
        # group_key: "categories" | category_name (for ingredient groups)
        self._sliders: dict[tuple, ttk.Scale] = {}
        self._slider_vars: dict[tuple, tk.DoubleVar] = {}
        self._entries: dict[tuple, ttk.Entry] = {}
        self._entry_vars: dict[tuple, tk.StringVar] = {}
        self._radio_vars: dict[str, tk.IntVar] = {}   # group_key → IntVar holding auto member idx

        self._build()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _blank_recipe(self) -> Recipe:
        """Create a new recipe pre-seeded with every known category from inventory."""
        cats_in_inventory = list(dict.fromkeys(i.category for i in self._app.ingredients))
        if not cats_in_inventory:
            cats_in_inventory = ["wood", "resin", "binder"]
        n = len(cats_in_inventory)
        even = round(100.0 / n, 1) if n else 0.0
        categories = []
        for idx, cat in enumerate(cats_in_inventory):
            is_auto = idx == n - 1  # last one is auto by default
            pct = even if idx < n - 1 else 0.0
            categories.append(RecipeCategory(category=cat, percentage=pct, is_auto=is_auto))
        if categories:
            # Fix auto member to remainder
            s = sum(c.percentage for c in categories if not c.is_auto)
            auto = next(c for c in categories if c.is_auto)
            auto.percentage = max(0.0, 100.0 - s)
        return Recipe(name="New Recipe", categories=categories)

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build(self):
        # Top bar: name
        top = ttk.Frame(self, padding=8)
        top.pack(fill=X)
        ttk.Label(top, text="Recipe Name:", font="-weight bold").pack(side=LEFT)
        self._name_var = tk.StringVar(value=self._recipe.name)
        ttk.Entry(top, textvariable=self._name_var, width=40).pack(side=LEFT, padx=8)

        # Scrollable main area
        self._scroll = ScrolledFrame(self, autohide=True)
        self._scroll.pack(fill=BOTH, expand=True, padx=4, pady=4)
        self._content = self._scroll

        self._render_all()

        # Notes
        notes_frame = ttk.LabelFrame(self._content, text="Notes")
        notes_frame.pack(fill=X, padx=8, pady=4)
        self._notes = tk.Text(notes_frame, height=3, wrap=WORD)
        self._notes.insert("1.0", self._recipe.notes)
        self._notes.pack(fill=X, padx=4, pady=4)

        # Buttons
        btn_frame = ttk.Frame(self, padding=8)
        btn_frame.pack(fill=X)
        ttk.Button(btn_frame, text="Save", bootstyle=SUCCESS, command=self._save).pack(side=RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", bootstyle=SECONDARY, command=self.destroy).pack(side=RIGHT)

        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window()

    def _render_all(self):
        """Render/re-render the entire percentage editor area."""
        # Destroy existing widgets in content area (except notes/buttons added after)
        for w in list(self._content.winfo_children()):
            w.destroy()
        self._sliders.clear()
        self._slider_vars.clear()
        self._entries.clear()
        self._entry_vars.clear()
        self._radio_vars.clear()

        # Category percentages section
        cat_frame = ttk.LabelFrame(self._content, text="Category Percentages")
        cat_frame.pack(fill=X, padx=8, pady=4)
        self._build_pct_group(cat_frame, "categories", self._recipe.categories,
                               label_fn=lambda c: c.category.capitalize())

        # Per-category ingredient sections
        for rc in self._recipe.categories:
            self._build_ingredient_section(rc)

    def _build_pct_group(self, parent, group_key: str, members, label_fn):
        """
        Build a group of (radio | label | slider | entry) rows.
        members: list of RecipeCategory or RecipeIngredient
        """
        # Determine which member is currently auto
        auto_idx = next((i for i, m in enumerate(members) if m.is_auto), len(members) - 1)
        var = tk.IntVar(value=auto_idx)
        self._radio_vars[group_key] = var

        for idx, member in enumerate(members):
            row = ttk.Frame(parent)
            row.pack(fill=X, pady=2)

            # Radio button
            rb = ttk.Radiobutton(
                row, variable=var, value=idx,
                command=lambda gk=group_key, mems=members: self._on_radio_change(gk, mems),
                bootstyle="round-toggle",
            )
            rb.pack(side=LEFT)

            # Lock indicator label
            self._lock_labels = getattr(self, "_lock_labels", {})
            lbl_lock = ttk.Label(row, text="⟳", width=2, foreground="gray")
            lbl_lock.pack(side=LEFT)
            self._lock_labels[(group_key, idx)] = lbl_lock

            # Name label
            ttk.Label(row, text=label_fn(member), width=18, anchor=W).pack(side=LEFT, padx=(2, 8))

            # Slider
            slider_var = tk.DoubleVar(value=member.percentage)
            slider = ttk.Scale(
                row, from_=0, to=100, orient=HORIZONTAL, variable=slider_var, length=260,
                command=lambda val, gk=group_key, i=idx, mems=members, sv=slider_var:
                    self._on_slider(gk, i, mems, sv),
            )
            slider.pack(side=LEFT, padx=4)
            self._sliders[(group_key, idx)] = slider
            self._slider_vars[(group_key, idx)] = slider_var

            # Entry
            entry_var = tk.StringVar(value=f"{member.percentage:.1f}")
            entry = ttk.Entry(row, textvariable=entry_var, width=7)
            entry.pack(side=LEFT)
            ttk.Label(row, text="%").pack(side=LEFT)
            entry_var.trace_add("write", lambda *a, gk=group_key, i=idx, mems=members, ev=entry_var:
                                self._on_entry(gk, i, mems, ev))
            self._entries[(group_key, idx)] = entry
            self._entry_vars[(group_key, idx)] = entry_var

        # Disable auto member's slider/entry and update lock icons
        self._update_auto_state(group_key, members)

    def _build_ingredient_section(self, rc: RecipeCategory):
        """Build the ingredient sub-section for one category."""
        group_key = f"ing:{rc.category}"
        frame = ttk.LabelFrame(self._content,
                                text=f"{rc.category.capitalize()} Ingredients ({rc.percentage:.1f}% of batch)")
        frame.pack(fill=X, padx=8, pady=4)
        frame.category = rc.category  # tag for later lookup

        if rc.ingredients:
            self._build_pct_group(
                frame, group_key, rc.ingredients,
                label_fn=lambda ri: self._ingredient_name(ri.ingredient_id),
            )
        else:
            ttk.Label(frame, text="No ingredients added yet.", foreground="gray").pack(anchor=W)

        # Add ingredient button
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=X, pady=(6, 0))
        available = [i for i in self._app.ingredients if i.category == rc.category
                     and i.id not in {ri.ingredient_id for ri in rc.ingredients}]
        if available:
            combo_var = tk.StringVar()
            combo = ttk.Combobox(btn_row, textvariable=combo_var, state="readonly", width=24,
                                  values=[i.name for i in available])
            combo.pack(side=LEFT, padx=(0, 4))
            combo.set(available[0].name)
            ttk.Button(
                btn_row, text="Add Ingredient", bootstyle=OUTLINE,
                command=lambda cv=combo_var, av=available, r=rc: self._add_ingredient(r, av, cv),
            ).pack(side=LEFT)
        else:
            ttk.Label(btn_row, text="All available ingredients already added.", foreground="gray").pack(side=LEFT)

        # Remove ingredient buttons
        if rc.ingredients:
            rem_row = ttk.Frame(frame)
            rem_row.pack(fill=X, pady=(2, 0))
            for ri in rc.ingredients:
                name = self._ingredient_name(ri.ingredient_id)
                ttk.Button(
                    rem_row, text=f"✕ {name}", bootstyle="danger-outline",
                    command=lambda r=rc, rid=ri.ingredient_id: self._remove_ingredient(r, rid),
                ).pack(side=LEFT, padx=(0, 4))

    # ------------------------------------------------------------------
    # Percentage logic
    # ------------------------------------------------------------------

    def _recalculate_auto(self, group_key: str, members):
        """Recalculate the auto member so the group sums to 100."""
        auto_idx = self._radio_vars[group_key].get()
        if auto_idx >= len(members):
            auto_idx = len(members) - 1
        others_sum = sum(m.percentage for i, m in enumerate(members) if i != auto_idx)
        new_val = max(0.0, min(100.0, 100.0 - others_sum))
        members[auto_idx].percentage = new_val
        self._update_widgets(group_key, auto_idx, new_val)

    def _update_widgets(self, group_key: str, idx: int, value: float):
        """Push a value to slider + entry for (group_key, idx) without triggering callbacks."""
        # Set via the backing DoubleVar — this moves the thumb even when the slider is disabled
        slider_var = self._slider_vars.get((group_key, idx))
        if slider_var:
            slider_var.set(value)
        # Update via StringVar so readonly entries are updated too
        entry_var = self._entry_vars.get((group_key, idx))
        if entry_var:
            entry_var.set(f"{value:.1f}")

    def _update_auto_state(self, group_key: str, members):
        """Update lock icon, slider disabled state, and entry readonly state for all members."""
        auto_idx = self._radio_vars.get(group_key)
        if auto_idx is None:
            return
        a = auto_idx.get()
        for i in range(len(members)):
            is_auto = (i == a)
            lbl = self._lock_labels.get((group_key, i))
            if lbl:
                lbl.configure(text="⟳" if is_auto else "  ",
                               foreground="#0d6efd" if is_auto else "gray")
            slider = self._sliders.get((group_key, i))
            if slider:
                slider.configure(state="disabled" if is_auto else "normal")
            entry = self._entries.get((group_key, i))
            if entry:
                entry.configure(state="readonly" if is_auto else "normal")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _max_for(self, group_key: str, idx: int, members) -> float:
        """Max value this member can take without pushing the auto member below 0."""
        auto_idx = self._radio_vars[group_key].get()
        others_sum = sum(m.percentage for i, m in enumerate(members)
                         if i != auto_idx and i != idx)
        return max(0.0, 100.0 - others_sum)

    def _on_slider(self, group_key: str, idx: int, members, slider_var: tk.DoubleVar):
        if self._updating:
            return
        self._updating = True
        val = round(slider_var.get(), 1)
        val = min(val, self._max_for(group_key, idx, members))
        members[idx].percentage = val
        # Snap slider and entry back if the value was clamped
        slider_var.set(val)
        entry_var = self._entry_vars.get((group_key, idx))
        if entry_var:
            entry_var.set(f"{val:.1f}")
        self._recalculate_auto(group_key, members)
        self._refresh_ingredient_labels()
        self._updating = False

    def _on_entry(self, group_key: str, idx: int, members, entry_var: tk.StringVar):
        if self._updating:
            return
        try:
            val = float(entry_var.get())
        except ValueError:
            return
        val = max(0.0, min(self._max_for(group_key, idx, members), val))
        self._updating = True
        members[idx].percentage = val
        slider = self._sliders.get((group_key, idx))
        if slider:
            slider.configure(value=val)
        self._recalculate_auto(group_key, members)
        self._refresh_ingredient_labels()
        self._updating = False

    def _on_radio_change(self, group_key: str, members):
        """User switched which member is auto — immediately recalculate."""
        # Un-auto all, set the newly selected one
        new_auto = self._radio_vars[group_key].get()
        for i, m in enumerate(members):
            m.is_auto = (i == new_auto)
        self._update_auto_state(group_key, members)
        self._recalculate_auto(group_key, members)

    # ------------------------------------------------------------------
    # Ingredient add/remove
    # ------------------------------------------------------------------

    def _add_ingredient(self, rc: RecipeCategory, available: list[Ingredient], combo_var: tk.StringVar):
        name = combo_var.get()
        ing = next((i for i in available if i.name == name), None)
        if not ing:
            return
        if not rc.ingredients:
            # First ingredient — make it auto
            rc.ingredients.append(RecipeIngredient(ingredient_id=ing.id, percentage=100.0, is_auto=True))
        else:
            # Add at 0% and mark last one as auto (or keep existing auto)
            rc.ingredients.append(RecipeIngredient(ingredient_id=ing.id, percentage=0.0, is_auto=False))
            if not any(ri.is_auto for ri in rc.ingredients):
                rc.ingredients[-1].is_auto = True
        self._re_render()

    def _remove_ingredient(self, rc: RecipeCategory, ingredient_id: str):
        rc.ingredients = [ri for ri in rc.ingredients if ri.ingredient_id != ingredient_id]
        # Ensure one is auto
        if rc.ingredients and not any(ri.is_auto for ri in rc.ingredients):
            rc.ingredients[-1].is_auto = True
        self._re_render()

    def _re_render(self):
        """Re-render the entire content area, preserving notes."""
        notes_text = self._notes.get("1.0", END) if hasattr(self, "_notes") else ""
        for w in list(self._content.winfo_children()):
            w.destroy()
        self._sliders.clear()
        self._slider_vars.clear()
        self._entries.clear()
        self._entry_vars.clear()
        self._radio_vars.clear()
        self._lock_labels = {}

        cat_frame = ttk.LabelFrame(self._content, text="Category Percentages")
        cat_frame.pack(fill=X, padx=8, pady=4)
        self._build_pct_group(cat_frame, "categories", self._recipe.categories,
                               label_fn=lambda c: c.category.capitalize())
        for rc in self._recipe.categories:
            self._build_ingredient_section(rc)

        notes_frame = ttk.LabelFrame(self._content, text="Notes")
        notes_frame.pack(fill=X, padx=8, pady=4)
        self._notes = tk.Text(notes_frame, height=3, wrap=WORD)
        self._notes.insert("1.0", notes_text.rstrip())
        self._notes.pack(fill=X, padx=4, pady=4)

    def _refresh_ingredient_labels(self):
        """Update category section header labels with current %."""
        for w in self._content.winfo_children():
            if isinstance(w, ttk.LabelFrame) and hasattr(w, "category"):
                rc = next((c for c in self._recipe.categories if c.category == w.category), None)
                if rc:
                    w.configure(text=f"{rc.category.capitalize()} Ingredients ({rc.percentage:.1f}% of batch)")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _ingredient_name(self, ingredient_id: str) -> str:
        ing = next((i for i in self._app.ingredients if i.id == ingredient_id), None)
        return ing.name if ing else f"(unknown {ingredient_id[:6]})"

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self):
        name = self._name_var.get().strip()
        if not name:
            tk.messagebox.showwarning("Validation", "Recipe name is required.", parent=self)
            return
        self._recipe.name = name
        self._recipe.notes = self._notes.get("1.0", END).strip()

        # Sync is_auto from radio vars back to model
        for rc_idx, rc in enumerate(self._recipe.categories):
            gk = "categories"
            auto_idx = self._radio_vars.get(gk)
            if auto_idx is not None:
                for i, cat in enumerate(self._recipe.categories):
                    cat.is_auto = (i == auto_idx.get())
            ing_gk = f"ing:{rc.category}"
            ing_auto = self._radio_vars.get(ing_gk)
            if ing_auto is not None:
                for i, ri in enumerate(rc.ingredients):
                    ri.is_auto = (i == ing_auto.get())

        self.result = self._recipe
        self.destroy()
