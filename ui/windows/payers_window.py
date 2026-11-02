"""
Окно "Плательщик"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import payers_repo


class PayersWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Плательщик",
            item_label="Добавить плательщика:",
            repo=payers_repo
        )