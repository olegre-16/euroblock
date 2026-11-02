"""
Окно "Покупатель"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import customers_repo


class CustomersWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Покупатель",
            item_label="Добавить покупателя:",
            repo=customers_repo
        )