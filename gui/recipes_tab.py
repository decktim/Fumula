from __future__ import annotations
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models import Recipe
from gui.recipe_editor import RecipeEditor

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Colours grouped by category
_CAT_PALETTES = {
    "wood":   ["#8B5E3C", "#A0785A", "#C4A882", "#D4B896", "#E8D5B7"],
    "resin":  ["#5B4A8A", "#7B6AAA", "#9B8ACA", "#BBAADF", "#D4C8EF"],
    "binder": ["#2E7D6E", "#3E9D8E", "#5EBDAE", "#8ED8CE", "#B8EDE8"],
}
_CAT_BASE = {cat: colors[0] for cat, colors in _CAT_PALETTES.items()}


class RecipesTab(ttk.Frame):
    """Tab for listing, creating, editing, and deleting recipes."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._fig: Figure | None = None
        self._canvas: FigureCanvasTkAgg | None = None
        self._resize_job = None
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, padx=8, pady=(8, 0))
        ttk.Button(toolbar, text="New Recipe",  bootstyle=SUCCESS, command=self._new).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Edit",        bootstyle=INFO,    command=self._edit).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Delete",      bootstyle=DANGER,  command=self._delete).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Print…",      bootstyle=PRIMARY, command=self._print).pack(side=LEFT, padx=(0, 4))

        # Horizontal paned window: list | detail panel
        pane = ttk.Panedwindow(self, orient=HORIZONTAL)
        pane.pack(fill=BOTH, expand=True, padx=8, pady=8)

        # Left: treeview
        list_frame = ttk.Frame(pane)
        pane.add(list_frame, weight=1)

        cols = ("name", "categories")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name",       text="Recipe Name")
        self.tree.heading("categories", text="Composition")
        self.tree.column("name",       width=150)
        self.tree.column("categories", width=220)
        self.tree.bind("<Double-1>",         lambda e: self._edit())
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        vsb = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        # Right: detail panel
        self._detail = ttk.Frame(pane)
        pane.add(self._detail, weight=2)

        self._notes_var = tk.StringVar()
        self._name_lbl = ttk.Label(self._detail, text="", font="-size 13 -weight bold")
        self._name_lbl.pack(anchor=W, padx=10, pady=(10, 2))

        self._notes_lbl = ttk.Label(self._detail, textvariable=self._notes_var,
                                     wraplength=320, foreground="gray", justify=LEFT)
        self._notes_lbl.pack(anchor=W, padx=10, pady=(0, 6))

        self._chart_frame = ttk.Frame(self._detail)
        self._chart_frame.pack(fill=BOTH, expand=True)

        self._placeholder = ttk.Label(self._chart_frame,
                                       text="Select a recipe to see details",
                                       foreground="gray")
        self._placeholder.pack(expand=True)

        # Create the figure and canvas once; keep them for the lifetime of the tab
        self._fig = Figure(facecolor="none")
        self._canvas = FigureCanvasTkAgg(self._fig, master=self._chart_frame)
        self._canvas.get_tk_widget().pack(fill=BOTH, expand=True)
        self._canvas.get_tk_widget().pack_forget()   # hidden until a recipe is selected

        # Resize figure when the chart frame changes size
        self._chart_frame.bind("<Configure>", self._on_chart_resize)

        self.refresh()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def refresh(self):
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for recipe in self.app.recipes:
            composition = ", ".join(
                f"{rc.category.capitalize()} {rc.percentage:.0f}%"
                for rc in recipe.categories
            )
            self.tree.insert("", END, iid=recipe.id, values=(recipe.name, composition))
        # Restore selection if still present
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])
            self._show_detail(self._get_recipe(sel[0]))
        else:
            self._clear_detail()

    def _get_recipe(self, iid: str) -> Recipe | None:
        return next((r for r in self.app.recipes if r.id == iid), None)

    def _selected(self) -> Recipe | None:
        sel = self.tree.selection()
        return self._get_recipe(sel[0]) if sel else None

    # ------------------------------------------------------------------
    # Detail panel
    # ------------------------------------------------------------------

    def _on_select(self, event=None):
        recipe = self._selected()
        if recipe:
            self._show_detail(recipe)
        else:
            self._clear_detail()

    def _clear_detail(self):
        self._name_lbl.configure(text="")
        self._notes_var.set("")
        self._canvas.get_tk_widget().pack_forget()
        self._placeholder.pack(expand=True)

    def _show_detail(self, recipe: Recipe):
        self._name_lbl.configure(text=recipe.name)
        self._notes_var.set(recipe.notes or "")
        self._placeholder.pack_forget()
        self._canvas.get_tk_widget().pack(fill=BOTH, expand=True)
        self._redraw(recipe)

    def _on_chart_resize(self, event):
        # Debounce: only resize after resizing has settled (100 ms)
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, lambda w=event.width, h=event.height: self._apply_resize(w, h))

    def _apply_resize(self, width: int, height: int):
        self._resize_job = None
        if width < 10 or height < 10:
            return
        dpi = self._fig.get_dpi()
        self._fig.set_size_inches(width / dpi, height / dpi, forward=False)
        sel = self.tree.selection()
        if sel:
            recipe = self._get_recipe(sel[0])
            if recipe:
                self._redraw(recipe)

    def _redraw(self, recipe: Recipe):
        self._fig.clear()
        ax = self._fig.add_subplot(1, 1, 1)
        ax.set_aspect("equal")
        self._draw_donut(ax, recipe)
        self._fig.tight_layout(pad=1.0)
        self._canvas.draw_idle()

    def _draw_donut(self, ax, recipe: Recipe):
        cat_labels, cat_pcts, cat_colors = [], [], []
        ing_labels, ing_pcts, ing_colors = [], [], []

        for rc in recipe.categories:
            if rc.percentage <= 0:
                continue
            cat_labels.append(rc.category.capitalize())
            cat_pcts.append(rc.percentage)
            cat_colors.append(_CAT_BASE.get(rc.category, "#999999"))

            palette = _CAT_PALETTES.get(rc.category, ["#999999"] * 5)
            active = [(ri, self._ingredient_name(ri.ingredient_id))
                      for ri in rc.ingredients
                      if rc.percentage * ri.percentage / 100.0 > 0]
            if active:
                for ii, (ri, name) in enumerate(active):
                    abs_pct = rc.percentage * ri.percentage / 100.0
                    ing_labels.append(f"{name}\n{abs_pct:.1f}%")
                    ing_pcts.append(abs_pct)
                    ing_colors.append(palette[ii % len(palette)])
            else:
                ing_labels.append("")
                ing_pcts.append(rc.percentage)
                ing_colors.append(_CAT_BASE.get(rc.category, "#cccccc"))

        if not cat_pcts:
            return

        wedge_kw = {"linewidth": 1.2, "edgecolor": "white"}

        # Outer ring — ingredients
        outer_wedges, *_ = ax.pie(
            ing_pcts, colors=ing_colors, radius=1.0,
            startangle=90, counterclock=False,
            wedgeprops={**wedge_kw, "width": 0.42},
            labels=None,
        )

        # Inner ring — categories
        _, inner_texts = ax.pie(
            cat_pcts, colors=cat_colors, radius=0.58,
            startangle=90, counterclock=False,
            wedgeprops={**wedge_kw, "width": 0.42},
            labels=cat_labels,
            labeldistance=0.35,
        )
        for t in inner_texts:
            t.set_fontsize(8)
            t.set_fontweight("bold")
            t.set_color("white")
            t.set_ha("center")

        # Legend for named outer wedges
        named = [(w, lb) for w, lb in zip(outer_wedges, ing_labels) if lb]
        if named:
            ws, lbs = zip(*named)
            ax.legend(ws, lbs, loc="lower center", bbox_to_anchor=(0.5, -0.22),
                      ncol=2, fontsize=7, frameon=False,
                      handlelength=1.2, handleheight=1.0)

        ax.set_title("Recipe Composition", fontsize=9, pad=6)

    def _ingredient_name(self, ingredient_id: str) -> str:
        ing = next((i for i in self.app.ingredients if i.id == ingredient_id), None)
        return ing.name if ing else "(unknown)"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _new(self):
        dlg = RecipeEditor(self, None, self.app)
        if dlg.result:
            self.app.recipes.append(dlg.result)
            self.app.save()
            self.refresh()

    def _edit(self):
        recipe = self._selected()
        if not recipe:
            return
        dlg = RecipeEditor(self, recipe, self.app)
        if dlg.result:
            idx = next(i for i, r in enumerate(self.app.recipes) if r.id == recipe.id)
            self.app.recipes[idx] = dlg.result
            self.app.save()
            self.refresh()

    def _delete(self):
        recipe = self._selected()
        if not recipe:
            return
        if tk.messagebox.askyesno("Delete", f"Delete recipe '{recipe.name}'?", parent=self):
            self.app.recipes = [r for r in self.app.recipes if r.id != recipe.id]
            self.app.save()
            self.refresh()

    def _print(self):
        if not self.app.recipes:
            tk.messagebox.showinfo("Print", "No recipes saved yet.", parent=self)
            return
        from gui.print_dialog import PrintDialog
        PrintDialog(self, self.app)
