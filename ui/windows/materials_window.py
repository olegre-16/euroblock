"""
Окно "Материалы и услуги"
"""
from ui.windows.base_dictionary_window import BaseDictionaryWindow
from database.repositories import materials_repo


class MaterialsWindow(BaseDictionaryWindow):
    def __init__(self, parent, on_exit_callback):
        super().__init__(
            parent=parent,
            on_exit_callback=on_exit_callback,
            title="Материалы и услуги",
            item_label="Добавить материал или услугу:",
            repo=materials_repo
        )