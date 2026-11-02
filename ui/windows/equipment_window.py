"""
Окно "Оборудование"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import equipment_repo


class EquipmentWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Оборудование",
            item_label="Добавить оборудование:",
            repo=equipment_repo
        )