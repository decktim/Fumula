from __future__ import annotations
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import export


class PrintDialog(tk.Toplevel):
    """Dialog for selecting recipes and target gram amounts, then generating HTML."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.title("Print Recipe Sheet")
        self.resizable(False, False)
        self.grab_set()
        self._app = app
        self._build()
        self.wait_window()

    def _build(self):
        pad = dict(padx=10, pady=4)

        ttk.Label(self, text="Select Recipes:", font="-weight bold").pack(anchor=W, **pad)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill=X, padx=10, pady=2)

        self._check_vars: dict[str, tk.BooleanVar] = {}
        for recipe in self._app.recipes:
            var = tk.BooleanVar(value=True)
            self._check_vars[recipe.id] = var
            ttk.Checkbutton(list_frame, text=recipe.name, variable=var).pack(anchor=W)

        ttk.Separator(self).pack(fill=X, padx=10, pady=6)

        gram_frame = ttk.Frame(self)
        gram_frame.pack(fill=X, **pad)
        ttk.Label(gram_frame, text="Target grams (comma-separated):").pack(side=LEFT)
        self._grams_var = tk.StringVar(value="1, 2, 5, 10")
        ttk.Entry(gram_frame, textvariable=self._grams_var, width=20).pack(side=LEFT, padx=8)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Generate & Open in Browser", bootstyle=SUCCESS,
                   command=self._generate).pack(side=RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", bootstyle=SECONDARY,
                   command=self.destroy).pack(side=RIGHT)

    def _generate(self):
        selected = [r for r in self._app.recipes if self._check_vars[r.id].get()]
        if not selected:
            tk.messagebox.showwarning("Print", "Please select at least one recipe.", parent=self)
            return

        raw = self._grams_var.get()
        try:
            target_grams = [float(x.strip()) for x in raw.split(",") if x.strip()]
            if not target_grams:
                raise ValueError
        except ValueError:
            tk.messagebox.showwarning("Print", "Enter valid comma-separated numbers for target grams.", parent=self)
            return

        export.generate_and_open(selected, self._app.ingredients, target_grams)
        self.destroy()
