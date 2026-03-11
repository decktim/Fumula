from __future__ import annotations
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import storage
from gui.ingredients_tab import IngredientsTab
from gui.recipes_tab import RecipesTab


class App(ttk.Window):
    def __init__(self):
        super().__init__(title="Incense Recipe Manager", themename="flatly", size=(800, 600))
        self.ingredients, self.recipes = storage.load_data()
        self._build()

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=BOTH, expand=True, padx=4, pady=4)

        self.ingredients_tab = IngredientsTab(nb, self)
        self.recipes_tab = RecipesTab(nb, self)

        nb.add(self.ingredients_tab, text="  Ingredients  ")
        nb.add(self.recipes_tab, text="  Recipes  ")

    def save(self):
        storage.save_data(self.ingredients, self.recipes)


if __name__ == "__main__":
    app = App()
    app.mainloop()
