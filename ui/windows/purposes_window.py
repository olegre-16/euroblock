"""
Окно "Назначение"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import purposes_repo


class PurposesWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Назначение",
            item_label="Добавить назначение:",
            repo=purposes_repo
        )