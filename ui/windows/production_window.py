"""
Окно "Производство продукции"
Оформление идентично окну "Поступление цемента".

[ИЗМЕНЕНО]
- Поле "Количество, шт/м2" переименовано в "Количество, подд."
- Поле перенесено вниз, перед полем "Примечание"
- Заголовок колонки в Treeview также обновлён
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    products_repo, colors_repo, equipment_repo, cement_silos_repo, production_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class ProductionWindow(BaseToplevelWindow):
    """Окно учёта производства продукции"""
    def __init__(self, parent, on_exit_callback):
        self.product_list = [row[0] for row in products_repo.get_all()]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.equipment_list = [row[0] for row in equipment_repo.get_all()]
        self.silo_list = [row[0] for row in cement_silos_repo.get_all()]
        self.editing_id = None
        super().__init__(parent, on_exit_callback, title="Производство продукции")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Производство продукции")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 2))
        
        self.add_field_label(left_inner, "Оборудование:")
        self.equipment_combo = AutocompleteCombobox(left_inner, values=self.equipment_list)
        self.equipment_combo.pack(fill=tk.X, padx=10, pady=(0, 2))
        
        self.add_field_label(left_inner, "Силос цемента:")
        self.silo_combo = AutocompleteCombobox(left_inner, values=self.silo_list)
        self.silo_combo.pack(fill=tk.X, padx=10, pady=(0, 2))
        
        self.add_field_label(left_inner, "Продукция:")
        self.product_combo = AutocompleteCombobox(left_inner, values=self.product_list)
        self.product_combo.pack(fill=tk.X, padx=10, pady=(0, 2))
        self.product_combo.bind_text_change(self._on_product_change)
        
        self.add_field_label(left_inner, "Цвет:")
        self.color_combo = AutocompleteCombobox(left_inner, values=self.color_list)
        self.color_combo.pack(fill=tk.X, padx=10, pady=(0, 2))
        
        # [ИЗМЕНЕНО] Поля материалов (Цемент, Пески, Керамзит, Пластификатор, Вода)
        # теперь идут ПЕРЕД полем "Количество, подд."
        self.add_field_label(left_inner, "Цемент, кг:")
        self.cement_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.cement_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.cement_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Песок обогащённый, кг:")
        self.enriched_sand_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.enriched_sand_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.enriched_sand_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Песок речной, кг:")
        self.river_sand_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.river_sand_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.river_sand_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Керамзит, кг:")
        self.keramzit_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.keramzit_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.keramzit_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Пластификатор, кг:")
        self.plasticizer_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.plasticizer_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.plasticizer_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Вода, кг:")
        self.water_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.water_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.water_entry.bind('<KeyRelease>', self._validate_number)
        
        # [ИЗМЕНЕНО] Поле "Количество" перенесено сюда (перед "Примечание")
        # и переименовано в "Количество, подд."
        self.add_field_label(left_inner, "Количество, подд.:")
        self.quantity_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 2), ipady=SIZES['field_ipady'])
        self.quantity_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Примечание:")
        self.note_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.note_entry.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=SIZES['field_ipady'])
        
        # КНОПКИ
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))
        
        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_production,
                                        color=COLORS['button_primary'])
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        self.edit_btn = self.add_button(buttons_frame, "Изменить", self.edit_selected,
                                        color='#f39c12')
        self.delete_btn = self.add_button(buttons_frame, "Удалить", self.delete_selected,
                                          color='#e74c3c')
        
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ПРАВАЯ ЧАСТЬ
        right_frame = self.create_right_panel(content_frame)
        tk.Label(
            right_frame, text="Журнал производства продукции",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('date', 'equipment', 'silo', 'product', 'color', 'quantity'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('equipment', text='Оборудование', anchor='w')
        self.tree.heading('silo', text='Силос', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        # [ИЗМЕНЕНО] Заголовок колонки обновлён
        self.tree.heading('quantity', text='Кол-во, подд.', anchor='w')
        self.tree.column('date', width=80, anchor='w')
        self.tree.column('equipment', width=100, anchor='w')
        self.tree.column('silo', width=100, anchor='w')
        self.tree.column('product', width=180, anchor='w')
        self.tree.column('color', width=80, anchor='w')
        self.tree.column('quantity', width=100, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_production()
    
    def _on_product_change(self):
        product = self.product_combo.get().strip().lower()
        keywords = ['блок', 'бордюр', 'желоб']
        if any(keyword in product for keyword in keywords):
            self.color_combo.set('серый')
        else:
            self.color_combo.clear()
    
    def _validate_number(self, event=None):
        widget = event.widget
        value = widget.get()
        filtered = ''
        for char in value:
            if char.isdigit() or char in '-.,':
                filtered += char
        if filtered != value:
            widget.delete(0, tk.END)
            widget.insert(0, filtered)
    
    def _on_save_enter(self):
        if self.editing_id:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary_hover'])
    
    def _on_save_leave(self):
        if self.editing_id:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary'])
    
    def _format_number(self, value):
        if value is None or value == '':
            return '0'
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:g}"
        except (ValueError, TypeError):
            return str(value)
    
    def load_production(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        records = production_repo.get_all()
        for row in records:
            if len(row) >= 14:
                rec_id, date, equipment, silo, product, color, quantity = row[:7]
            elif len(row) >= 7:
                rec_id, date, equipment, silo, product, color, quantity = row[:7]
            else:
                continue
            self.tree.insert(
                '', 'end', iid=str(rec_id),
                values=(date, equipment or '—', silo or '—', product,
                        color or '—', self._format_number(quantity))
            )
    
    def save_production(self):
        date_str = self.date_entry.get_date()
        equipment = self.equipment_combo.get().strip()
        silo = self.silo_combo.get().strip()
        product = self.product_combo.get().strip()
        color = self.color_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        cement_str = self.cement_entry.get().strip()
        enriched_sand_str = self.enriched_sand_entry.get().strip()
        river_sand_str = self.river_sand_entry.get().strip()
        keramzit_str = self.keramzit_entry.get().strip()
        plasticizer_str = self.plasticizer_entry.get().strip()
        water_str = self.water_entry.get().strip()
        note = self.note_entry.get().strip()
        
        if not date_str:
            self.show_warning("Внимание", "Укажите дату")
            return
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
        except ValueError:
            self.show_warning("Внимание", "Неверный формат даты")
            return
        if not product:
            self.show_warning("Внимание", "Выберите продукцию")
            return
        if not quantity_str:
            self.show_warning("Внимание", "Укажите количество")
            return
        try:
            quantity = float(quantity_str.replace(',', '.'))
            cement = float(cement_str.replace(',', '.')) if cement_str else 0
            enriched_sand = float(enriched_sand_str.replace(',', '.')) if enriched_sand_str else 0
            river_sand = float(river_sand_str.replace(',', '.')) if river_sand_str else 0
            keramzit = float(keramzit_str.replace(',', '.')) if keramzit_str else 0
            plasticizer = float(plasticizer_str.replace(',', '.')) if plasticizer_str else 0
            water = float(water_str.replace(',', '.')) if water_str else 0
        except ValueError:
            self.show_warning("Внимание", "Неверный формат числа")
            return
        
        if self.editing_id:
            success, message = production_repo.update(
                self.editing_id, date_str, equipment, silo, product, color, quantity,
                cement, enriched_sand, river_sand, keramzit, plasticizer, water, note
            )
        else:
            success, message = production_repo.add(
                date_str, equipment, silo, product, color, quantity,
                cement, enriched_sand, river_sand, keramzit, plasticizer, water, note
            )
        
        if success:
            self._clear_fields()
            self.load_production()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)
    
    def _clear_fields(self):
        self.date_entry.clear()
        self.equipment_combo.clear()
        self.silo_combo.clear()
        self.product_combo.clear()
        self.color_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.cement_entry.delete(0, tk.END)
        self.enriched_sand_entry.delete(0, tk.END)
        self.river_sand_entry.delete(0, tk.END)
        self.keramzit_entry.delete(0, tk.END)
        self.plasticizer_entry.delete(0, tk.END)
        self.water_entry.delete(0, tk.END)
        self.note_entry.delete(0, tk.END)
        self.editing_id = None
        self.save_btn.config(text="Сохранить")
    
    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для редактирования")
            return
        rec_id = int(selected[0])
        record = production_repo.get_by_id(rec_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        _, date, equipment, silo, product, color, quantity, cement, enriched_sand, river_sand, keramzit, plasticizer, water, note = record[:14]
        self.date_entry.set_date(date)
        self.equipment_combo.set(equipment or '')
        self.silo_combo.set(silo or '')
        self.product_combo.set(product)
        self.color_combo.set(color or '')
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        self.cement_entry.delete(0, tk.END)
        self.cement_entry.insert(0, self._format_number(cement))
        self.enriched_sand_entry.delete(0, tk.END)
        self.enriched_sand_entry.insert(0, self._format_number(enriched_sand))
        self.river_sand_entry.delete(0, tk.END)
        self.river_sand_entry.insert(0, self._format_number(river_sand))
        self.keramzit_entry.delete(0, tk.END)
        self.keramzit_entry.insert(0, self._format_number(keramzit))
        self.plasticizer_entry.delete(0, tk.END)
        self.plasticizer_entry.insert(0, self._format_number(plasticizer))
        self.water_entry.delete(0, tk.END)
        self.water_entry.insert(0, self._format_number(water))
        self.note_entry.delete(0, tk.END)
        self.note_entry.insert(0, note or '')
        self.editing_id = rec_id
        self.save_btn.config(text="Обновить")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для удаления")
            return
        rec_id = int(selected[0])
        record = production_repo.get_by_id(rec_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        _, date, equipment, silo, product, color, quantity = record[:7]
        if not self.ask_yes_no(
            "Подтверждение",
            f"Удалить запись?\n\n"
            f"Дата: {date}\nПродукция: {product}\n"
            f"Количество: {self._format_number(quantity)} подд."
        ):
            return
        success, message = production_repo.delete(rec_id)
        if success:
            if self.editing_id == rec_id:
                self._clear_fields()
            self.load_production()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)
    
    def _on_auto_refresh(self):
        try:
            self.load_production()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в ProductionWindow: {e}")