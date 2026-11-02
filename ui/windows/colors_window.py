"""
Окно "Цвет"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import colors_repo


class ColorsWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Цвет",
            item_label="Добавить цвет:",
            repo=colors_repo
        )
        