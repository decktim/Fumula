from __future__ import annotations
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from models import Ingredient


class IngredientsTab(ttk.Frame):
    """Tab for viewing and managing the ingredient inventory."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, padx=8, pady=(8, 0))
        ttk.Button(toolbar, text="Add", bootstyle=SUCCESS, command=self._add).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Edit", bootstyle=INFO, command=self._edit).pack(side=LEFT, padx=(0, 4))
        ttk.Button(toolbar, text="Delete", bootstyle=DANGER, command=self._delete).pack(side=LEFT)

        # Treeview
        cols = ("name", "category", "source_url")
        frame = ttk.Frame(self)
        frame.pack(fill=BOTH, expand=True, padx=8, pady=8)

        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("source_url", text="Source URL")
        self.tree.column("name", width=160)
        self.tree.column("category", width=100)
        self.tree.column("source_url", width=300)
        self.tree.bind("<Double-1>", lambda e: self._edit())

        vsb = ttk.Scrollbar(frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for ing in self.app.ingredients:
            self.tree.insert("", END, iid=ing.id, values=(ing.name, ing.category, ing.source_url))

    def _selected(self) -> Ingredient | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        return next((i for i in self.app.ingredients if i.id == iid), None)

    def _add(self):
        dlg = _IngredientDialog(self, None, self.app)
        result = dlg.result
        if result:
            self.app.ingredients.append(result)
            self.app.save()
            self.refresh()

    def _edit(self):
        ing = self._selected()
        if not ing:
            return
        dlg = _IngredientDialog(self, ing, self.app)
        if dlg.result:
            ing.name = dlg.result.name
            ing.category = dlg.result.category
            ing.source_url = dlg.result.source_url
            self.app.save()
            self.refresh()

    def _delete(self):
        ing = self._selected()
        if not ing:
            return
        if tk.messagebox.askyesno("Delete", f"Delete '{ing.name}'?", parent=self):
            self.app.ingredients = [i for i in self.app.ingredients if i.id != ing.id]
            self.app.save()
            self.refresh()


class _IngredientDialog(tk.Toplevel):
    """Modal dialog for add/edit of an ingredient."""

    CATEGORIES = ["wood", "resin", "binder"]

    def __init__(self, parent, ingredient: Ingredient | None, app):
        super().__init__(parent)
        self.title("Edit Ingredient" if ingredient else "Add Ingredient")
        self.resizable(False, False)
        self.grab_set()
        self.result: Ingredient | None = None
        self._app = app
        self._ing = ingredient

        # Collect existing categories for combobox
        existing_cats = sorted({i.category for i in app.ingredients})
        cats = list(dict.fromkeys(self.CATEGORIES + existing_cats))  # preserve order, dedupe

        pad = dict(padx=10, pady=5)

        ttk.Label(self, text="Name").grid(row=0, column=0, sticky=W, **pad)
        self._name = ttk.Entry(self, width=30)
        self._name.grid(row=0, column=1, **pad)

        ttk.Label(self, text="Category").grid(row=1, column=0, sticky=W, **pad)
        self._cat = ttk.Combobox(self, values=cats, width=27)
        self._cat.grid(row=1, column=1, **pad)

        ttk.Label(self, text="Source URL").grid(row=2, column=0, sticky=W, **pad)
        self._url = ttk.Entry(self, width=30)
        self._url.grid(row=2, column=1, **pad)

        if ingredient:
            self._name.insert(0, ingredient.name)
            self._cat.set(ingredient.category)
            self._url.insert(0, ingredient.source_url)
        else:
            self._cat.set("wood")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="OK", bootstyle=PRIMARY, command=self._ok).pack(side=LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel", bootstyle=SECONDARY, command=self.destroy).pack(side=LEFT, padx=4)

        self._name.focus_set()
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_window()

    def _ok(self):
        name = self._name.get().strip()
        cat = self._cat.get().strip().lower()
        url = self._url.get().strip()
        if not name or not cat:
            tk.messagebox.showwarning("Validation", "Name and Category are required.", parent=self)
            return
        if self._ing:
            self.result = Ingredient(id=self._ing.id, name=name, category=cat, source_url=url)
        else:
            self.result = Ingredient(name=name, category=cat, source_url=url)
        self.destroy()
