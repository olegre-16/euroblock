"""
Окно "Производство продукции" - учёт производства продукции
[ИЗМЕНЕНО] Все messagebox заменены на self.show_info/show_warning/show_error/ask_yes_no
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    equipment_repo, cement_silos_repo, products_repo, colors_repo, production_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class ProductionWindow(BaseToplevelWindow):
    """Окно учёта производства продукции"""
    def __init__(self, parent, on_exit_callback):
        self.equipment_list = [row[0] for row in equipment_repo.get_all()]
        self.silo_names = [row[0] for row in cement_silos_repo.get_all()]
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products if '(брак)' not in row[0]]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.editing_id = None
        self._editing_silo_name = None
        self._editing_cement_kg = None
        super().__init__(parent, on_exit_callback, title="Производство продукции")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Производство продукции")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame, width=350)
        
        self.add_field_label(left_inner, "Дата производства:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Оборудование:")
        self.equipment_combo = AutocompleteCombobox(left_inner, values=self.equipment_list)
        self.equipment_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Силос цемента:")
        self.silo_combo = AutocompleteCombobox(left_inner, values=self.silo_names)
        self.silo_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Цемент, кг:")
        self.cement_entry = self._create_number_entry(left_inner)
        self.cement_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Обогащенный песок, кг:")
        self.enriched_sand_entry = self._create_number_entry(left_inner)
        self.enriched_sand_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Речной песок, кг:")
        self.river_sand_entry = self._create_number_entry(left_inner)
        self.river_sand_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Керамзит, кг:")
        self.keramzit_entry = self._create_number_entry(left_inner)
        self.keramzit_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Пластификатор, кг:")
        self.plasticizer_entry = self._create_number_entry(left_inner)
        self.plasticizer_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Вода, кг:")
        self.water_entry = self._create_number_entry(left_inner)
        self.water_entry.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Продукция:")
        self.product_combo = AutocompleteCombobox(left_inner, values=self.product_list)
        self.product_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.product_combo.bind_text_change(self._on_product_change)
        
        self.add_field_label(left_inner, "Цвет:")
        self.color_combo = AutocompleteCombobox(left_inner, values=self.color_list)
        self.color_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Количество, поддонов:")
        self.quantity_entry = self._create_number_entry(left_inner)
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Примечание:")
        self.note_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.note_entry.pack(fill=tk.X, padx=10, pady=(0, 6), ipady=SIZES['field_ipady'])
        
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        self.save_btn = tk.Button(
            buttons_frame, text="Сохранить", font=FONTS['menu'],
            command=self.save_production, bg=COLORS['button_primary'],
            fg=COLORS['button_text'], relief=tk.FLAT,
            padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.save_btn.pack(fill=tk.X, pady=(0, 4))
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        self.edit_btn = tk.Button(
            buttons_frame, text="Изменить", font=FONTS['menu'],
            command=self.edit_selected, bg='#f39c12', fg=COLORS['button_text'],
            relief=tk.FLAT, padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.edit_btn.pack(fill=tk.X, pady=4)
        
        self.delete_btn = tk.Button(
            buttons_frame, text="Удалить", font=FONTS['menu'],
            command=self.delete_selected, bg='#e74c3c', fg=COLORS['button_text'],
            relief=tk.FLAT, padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.delete_btn.pack(fill=tk.X, pady=4)
        
        self.exit_btn = tk.Button(
            buttons_frame, text="Выход", font=FONTS['menu'],
            command=self._on_close, bg=COLORS['button_settings'],
            fg=COLORS['button_text'], relief=tk.FLAT,
            padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.exit_btn.pack(fill=tk.X, pady=(4, 0))
        
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
            columns=('date', 'equipment', 'product', 'color', 'quantity',
                     'cement', 'enriched_sand', 'plasticizer', 'river_sand',
                     'keramzit', 'water'),
            show='headings', yscrollcommand=scrollbar_y.set, selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('equipment', text='Оборудование', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        self.tree.heading('quantity', text='Кол-во, подд.', anchor='w')
        self.tree.heading('cement', text='Цемент, кг', anchor='w')
        self.tree.heading('enriched_sand', text='Обог. песок, кг', anchor='w')
        self.tree.heading('plasticizer', text='Пластиф., кг', anchor='w')
        self.tree.heading('river_sand', text='Речн. песок, кг', anchor='w')
        self.tree.heading('keramzit', text='Керамзит, кг', anchor='w')
        self.tree.heading('water', text='Вода, кг', anchor='w')
        self.tree.column('date', width=75, anchor='w')
        self.tree.column('equipment', width=100, anchor='w')
        self.tree.column('product', width=235, anchor='w')
        self.tree.column('color', width=80, anchor='w')
        self.tree.column('quantity', width=100, anchor='w')
        self.tree.column('cement', width=90, anchor='w')
        self.tree.column('enriched_sand', width=110, anchor='w')
        self.tree.column('plasticizer', width=110, anchor='w')
        self.tree.column('river_sand', width=110, anchor='w')
        self.tree.column('keramzit', width=90, anchor='w')
        self.tree.column('water', width=70, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.tree.bind('<Double-Button-1>', self._on_tree_double_click)
        
        self.load_production()
    
    def _create_number_entry(self, parent):
        entry = tk.Entry(parent, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left')
        entry.bind('<KeyRelease>', self._validate_number)
        return entry
    
    def _validate_number(self, event=None):
        widget = event.widget
        value = widget.get()
        filtered = ''.join(c for c in value if c.isdigit() or c in '-.,')
        if filtered != value:
            widget.delete(0, tk.END)
            widget.insert(0, filtered)
    
    def _on_product_change(self):
        product = self.product_combo.get().strip().lower()
        keywords = ['блок', 'бордюр', 'желоб']
        if any(keyword in product for keyword in keywords):
            self.color_combo.set('серый')
        else:
            self.color_combo.clear()
    
    def _on_tree_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        item_values = self.tree.item(item_id, 'values')
        if not item_values:
            return
        date_str = item_values[0]
        self._show_cement_info_dialog(date_str)
    
    def _show_cement_info_dialog(self, date_str):
        consumption = production_repo.get_cement_consumption_by_date(date_str)
        dialog = tk.Toplevel(self.window)
        dialog.title("Расход цемента")
        dialog.configure(bg=COLORS['panel_bg'])
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.update_idletasks()
        
        dialog_width = 400
        dialog_height = 300 if consumption else 200
        parent_x = self.window.winfo_rootx()
        parent_y = self.window.winfo_rooty()
        parent_w = self.window.winfo_width()
        parent_h = self.window.winfo_height()
        x = parent_x + (parent_w - dialog_width) // 2
        y = parent_y + (parent_h - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        tk.Label(
            dialog, text=f"Дата: {date_str}",
            font=FONTS['section_title'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(15, 10))
        
        tk.Frame(dialog, height=2, bg=COLORS['button_primary']).pack(fill=tk.X, padx=20, pady=(0, 10))
        
        if not consumption:
            tk.Label(
                dialog, text="Расход цемента за этот день не зафиксирован.",
                font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
            ).pack(pady=20)
        else:
            tk.Label(
                dialog, text="Расход цемента по силосам:",
                font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
            ).pack(pady=(0, 5))
            
            list_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
            list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
            
            total = 0
            for silo_name, cement_kg in consumption:
                cement_display = self._format_number(cement_kg)
                tk.Label(
                    list_frame, text=f"• {silo_name}: {cement_display} кг",
                    font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text'], anchor='w'
                ).pack(fill=tk.X, pady=2)
                total += cement_kg or 0
            
            tk.Frame(dialog, height=1, bg=COLORS['work_area_text']).pack(fill=tk.X, padx=20, pady=5)
            tk.Label(
                dialog, text=f"ИТОГО за день: {self._format_number(total)} кг",
                font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text'], anchor='w'
            ).pack(fill=tk.X, padx=20, pady=(0, 10))
        
        btn_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        def on_edit():
            dialog.destroy()
            self._show_cement_edit_dialog(date_str)
        
        def on_close():
            dialog.destroy()
        
        if consumption:
            edit_btn = tk.Button(
                btn_frame, text="Редактировать цемент", font=FONTS['menu'],
                command=on_edit, bg=COLORS['button_primary'], fg=COLORS['button_text'],
                relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
            )
            edit_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = tk.Button(
            btn_frame, text="Закрыть", font=FONTS['menu'], command=on_close,
            bg=COLORS['button_settings'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        close_btn.pack(side=tk.RIGHT)
        
        dialog.bind('<Escape>', lambda e: on_close())
    
    def _show_cement_edit_dialog(self, date_str):
        consumption = production_repo.get_cement_consumption_by_date(date_str)
        current_consumption = {silo_name: cement_kg for silo_name, cement_kg in consumption}
        
        dialog = tk.Toplevel(self.window)
        dialog.title("Редактирование расхода цемента")
        dialog.configure(bg=COLORS['panel_bg'])
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.update_idletasks()
        
        dialog_width = 450
        dialog_height = 400
        parent_x = self.window.winfo_rootx()
        parent_y = self.window.winfo_rooty()
        parent_w = self.window.winfo_width()
        parent_h = self.window.winfo_height()
        x = parent_x + (parent_w - dialog_width) // 2
        y = parent_y + (parent_h - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        tk.Label(
            dialog, text=f"Дата: {date_str}",
            font=FONTS['section_title'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(15, 10))
        
        tk.Frame(dialog, height=2, bg=COLORS['button_primary']).pack(fill=tk.X, padx=20, pady=(0, 10))
        
        tk.Label(
            dialog, text="Расход цемента по силосам (кг):",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(0, 10))
        
        fields_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        fields_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        entry_vars = {}
        for silo_name in self.silo_names:
            row_frame = tk.Frame(fields_frame, bg=COLORS['panel_bg'])
            row_frame.pack(fill=tk.X, pady=3)
            tk.Label(
                row_frame, text=f"{silo_name}:", font=FONTS['field'],
                bg=COLORS['panel_bg'], fg=COLORS['title_text'], width=20, anchor='w'
            ).pack(side=tk.LEFT, padx=(0, 10))
            
            var = tk.StringVar()
            current_value = current_consumption.get(silo_name, 0)
            var.set(self._format_number(current_value) if current_value else '0')
            
            entry = tk.Entry(
                row_frame, textvariable=var, font=FONTS['field'],
                width=15, relief=tk.SOLID, bd=1, justify='left'
            )
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            def validate_input(event, entry_widget=entry):
                value = entry_widget.get()
                filtered = ''.join(c for c in value if c.isdigit() or c in '.,')
                if filtered != value:
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, filtered)
            
            entry.bind('<KeyRelease>', validate_input)
            entry_vars[silo_name] = var
        
        btn_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        def on_save():
            new_consumption = {}
            for silo_name, var in entry_vars.items():
                value = var.get().strip()
                if value and value != '0':
                    new_consumption[silo_name] = value
            success, message = production_repo.update_cement_consumption_by_date(date_str, new_consumption)
            if success:
                self.show_info("Успех", message)
                dialog.destroy()
                self.load_production()
                self._show_cement_info_dialog(date_str)
            else:
                self.show_error("Ошибка", message)
        
        def on_cancel():
            dialog.destroy()
            self._show_cement_info_dialog(date_str)
        
        save_btn = tk.Button(
            btn_frame, text="Сохранить", font=FONTS['menu'], command=on_save,
            bg=COLORS['button_primary'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = tk.Button(
            btn_frame, text="Отменить", font=FONTS['menu'], command=on_cancel,
            bg=COLORS['button_settings'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        dialog.bind('<Escape>', lambda e: on_cancel())
    
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
        daily_cement = production_repo.get_daily_cement_totals()
        for row in records:
            (prod_id, date, equipment, silo, product, color, quantity,
             cement, enriched_sand, river_sand, keramzit, plasticizer, water, note) = row
            if not product:
                continue
            cement_total = daily_cement.get(date, 0)
            self.tree.insert(
                '', 'end', iid=str(prod_id),
                values=(
                    date, equipment or '—', product, color or '—',
                    self._format_number(quantity), self._format_number(cement_total),
                    self._format_number(enriched_sand), self._format_number(plasticizer),
                    self._format_number(river_sand), self._format_number(keramzit),
                    self._format_number(water)
                )
            )
    
    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для редактирования")
            return
        prod_id = int(selected[0])
        record = production_repo.get_by_id(prod_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        (prod_id, date, equipment, silo, product, color, quantity,
         cement, enriched_sand, river_sand, keramzit, plasticizer, water, note) = record
        
        self._editing_silo_name = silo or ''
        self._editing_cement_kg = cement
        
        self.date_entry.set_date(date)
        self.equipment_combo.set(equipment or '')
        self.color_combo.set(color or '')
        self.product_combo.set(product or '')
        self.color_combo.set(color or '')
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
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
        
        self.silo_combo.set_disabled(True, "Изменение через табличную часть")
        self.cement_entry.config(state='normal')
        self.cement_entry.delete(0, tk.END)
        self.cement_entry.insert(0, "Изменение через табличную часть")
        self.cement_entry.config(state='disabled', fg=COLORS['work_area_text'])
        
        self.editing_id = prod_id
        self.save_btn.config(text="Обновить")
        self.date_entry.entry.focus()
    
    def save_production(self):
        date_str = self.date_entry.get_date()
        equipment = self.equipment_combo.get().strip()
        product = self.product_combo.get().strip()
        color = self.color_combo.get().strip()
        quantity = self.quantity_entry.get().strip()
        enriched_sand = self.enriched_sand_entry.get().strip()
        river_sand = self.river_sand_entry.get().strip()
        keramzit = self.keramzit_entry.get().strip()
        plasticizer = self.plasticizer_entry.get().strip()
        water = self.water_entry.get().strip()
        note = self.note_entry.get().strip()
        
        if not date_str:
            self.show_warning("Внимание", "Укажите дату производства")
            return
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
        except ValueError:
            self.show_warning("Внимание", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        
        if self.editing_id:
            success, message = production_repo.update(
                self.editing_id, date_str, equipment,
                self._editing_silo_name, product, color, quantity,
                self._editing_cement_kg, enriched_sand, river_sand, keramzit,
                plasticizer, water, note
            )
        else:
            silo = self.silo_combo.get().strip()
            cement = self.cement_entry.get().strip()
            success, message = production_repo.add(
                date_str, equipment, silo, product, color,
                quantity, cement, enriched_sand, river_sand, keramzit,
                plasticizer, water, note
            )
        
        if success:
            self.show_info("Успех", message)
            self._clear_fields()
            self.load_production()
        else:
            self.show_error("Ошибка", message)
    
    def _clear_fields(self):
        self.date_entry.clear()
        self.equipment_combo.set_disabled(False)
        self.equipment_combo.clear()
        self.silo_combo.set_disabled(False)
        self.silo_combo.clear()
        self.cement_entry.config(state='normal', fg=COLORS['title_text'])
        self.cement_entry.delete(0, tk.END)
        self.enriched_sand_entry.delete(0, tk.END)
        self.river_sand_entry.delete(0, tk.END)
        self.keramzit_entry.delete(0, tk.END)
        self.plasticizer_entry.delete(0, tk.END)
        self.water_entry.delete(0, tk.END)
        self.product_combo.clear()
        self.color_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.note_entry.delete(0, tk.END)
        self.editing_id = None
        self._editing_silo_name = None
        self._editing_cement_kg = None
        self.save_btn.config(text="Сохранить")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для удаления")
            return
        item_values = self.tree.item(selected[0], 'values')
        if not item_values:
            return
        date_str = item_values[0]
        all_records = production_repo.get_all()
        records_for_date = [r for r in all_records if r[1] == date_str]
        count = len(records_for_date)
        if not self.ask_yes_no(
            "Подтверждение",
            f"Удалить ВСЕ записи за {date_str}?\n\n"
            f"Будет удалено записей: {count}\n"
            f"(включая расход цемента из других силосов за этот день)"
        ):
            return
        success, message = production_repo.delete_by_date(date_str)
        if success:
            if self.editing_id:
                editing_record = production_repo.get_by_id(self.editing_id)
                if not editing_record:
                    self._clear_fields()
            self.load_production()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)