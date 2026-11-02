"""
Окно "Поставщик"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import suppliers_repo


class SuppliersWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Поставщик",
            item_label="Добавить поставщика:",
            repo=suppliers_repo
        )