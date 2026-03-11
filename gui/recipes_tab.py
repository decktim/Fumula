from __future__ import annotations
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models import Recipe
from gui.recipe_editor import RecipeEditor


class RecipesTab(ttk.Frame):
    """Tab for listing, creating, editing, and deleting recipes."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, padx=8, pady=(8, 0))
        ttk.Button(toolbar, text="New Recipe", bootstyle=SUCCESS, command=self._new).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Edit", bootstyle=INFO, command=self._edit).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Delete", bootstyle=DANGER, command=self._delete).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Print…", bootstyle=PRIMARY, command=self._print).pack(side=LEFT, padx=(0, 4))

        cols = ("name", "categories", "notes")
        frame = ttk.Frame(self)
        frame.pack(fill=BOTH, expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Recipe Name")
        self.tree.heading("categories", text="Composition")
        self.tree.heading("notes", text="Notes")
        self.tree.column("name", width=180)
        self.tree.column("categories", width=320)
        self.tree.column("notes", width=200)
        self.tree.bind("<Double-1>", lambda e: self._edit())

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for recipe in self.app.recipes:
            composition = ", ".join(
                f"{rc.category.capitalize()} {rc.percentage:.0f}%"
                for rc in recipe.categories
            )
            self.tree.insert("", END, iid=recipe.id, values=(recipe.name, composition, recipe.notes))

    def _selected(self) -> Recipe | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        return next((r for r in self.app.recipes if r.id == iid), None)

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
