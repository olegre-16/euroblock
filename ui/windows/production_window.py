"""
Окно "Производство продукции" - учёт производства продукции
[ИЗМЕНЕНО] Применена пагинация к журналу производства.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    equipment_repo, cement_silos_repo, products_repo, colors_repo, production_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.widgets.paginated_treeview import PaginatedTreeview


class ProductionWindow:
    """Окно учёта производства продукции"""
    def __init__(self, parent, on_exit_callback):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.equipment_list = [row[0] for row in equipment_repo.get_all()]
        self.silo_names = [row[0] for row in cement_silos_repo.get_all()]
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products if '(брак)' not in row[0]]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.editing_id = None
        self._editing_silo_name = None
        self._editing_cement_kg = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Производство продукции")
        self.window.configure(bg=COLORS['background'])
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.transient(parent)
        self._build_ui()
        self.window.update_idletasks()
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        self.window.geometry(f"{parent_w}x{parent_h}+{parent_x}+{parent_y}")
        self.window.update_idletasks()
        self.window.grab_set()
    
    def _build_ui(self):
        self.title_frame = tk.Frame(self.window, bg=COLORS['background'])
        self.title_frame.pack(fill=tk.X, padx=PADDING['main'], pady=PADDING['main'])
        self.title_label = tk.Label(
            self.title_frame, text="Производство продукции",
            font=FONTS['section_title'], bg=COLORS['background'], fg=COLORS['title_text']
        )
        self.title_label.pack(anchor='w')
        self.separator = tk.Frame(self.title_frame, height=2, bg=COLORS['button_primary'])
        self.separator.pack(fill=tk.X, pady=(10, 0))
        
        self.content_frame = tk.Frame(self.window, bg=COLORS['background'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING['main'], pady=(0, PADDING['main']))
        
        # ===== ЛЕВАЯ ЧАСТЬ =====
        self.left_frame = tk.Frame(
            self.content_frame, bg=COLORS['panel_bg'],
            relief=tk.RAISED, bd=SIZES['panel_border'], width=315
        )
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        self.left_frame.pack_propagate(False)
        
        self._create_field_label("Дата производства:")
        self.date_entry = DateEntry(self.left_frame)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self._create_field_label("Оборудование:")
        self.equipment_combo = AutocompleteCombobox(self.left_frame, values=self.equipment_list)
        self.equipment_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self._create_field_label("Силос цемента:")
        self.silo_combo = AutocompleteCombobox(self.left_frame, values=self.silo_names)
        self.silo_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self._create_field_label("Цемент, кг:")
        self.cement_entry = self._create_number_entry()
        self.cement_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Обогащенный песок, кг:")
        self.enriched_sand_entry = self._create_number_entry()
        self.enriched_sand_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Речной песок, кг:")
        self.river_sand_entry = self._create_number_entry()
        self.river_sand_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Керамзит, кг:")
        self.keramzit_entry = self._create_number_entry()
        self.keramzit_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Пластификатор, кг:")
        self.plasticizer_entry = self._create_number_entry()
        self.plasticizer_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Вода, кг:")
        self.water_entry = self._create_number_entry()
        self.water_entry.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Продукция:")
        self.product_combo = AutocompleteCombobox(self.left_frame, values=self.product_list)
        self.product_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.product_combo.bind_text_change(self._on_product_change)
        
        self._create_field_label("Цвет:")
        self.color_combo = AutocompleteCombobox(self.left_frame, values=self.color_list)
        self.color_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self._create_field_label("Количество, поддонов:")
        self.quantity_entry = self._create_number_entry()
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=SIZES['field_ipady'])
        
        self._create_field_label("Примечание:")
        self.note_entry = tk.Entry(
            self.left_frame, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.note_entry.pack(fill=tk.X, padx=10, pady=(0, 6), ipady=SIZES['field_ipady'])
        
        self.buttons_frame = tk.Frame(self.left_frame, bg=COLORS['panel_bg'])
        self.buttons_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        self.save_btn = tk.Button(
            self.buttons_frame, text="Сохранить", font=FONTS['menu'],
            command=self.save_production, bg=COLORS['button_primary'],
            fg=COLORS['button_text'], relief=tk.FLAT,
            padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.save_btn.pack(fill=tk.X, pady=(0, 4))
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        self.edit_btn = tk.Button(
            self.buttons_frame, text="Изменить", font=FONTS['menu'],
            command=self.edit_selected, bg='#f39c12', fg=COLORS['button_text'],
            relief=tk.FLAT, padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.edit_btn.pack(fill=tk.X, pady=4)
        self.edit_btn.bind('<Enter>', lambda e: self.edit_btn.config(bg='#d68910'))
        self.edit_btn.bind('<Leave>', lambda e: self.edit_btn.config(bg='#f39c12'))
        
        self.delete_btn = tk.Button(
            self.buttons_frame, text="Удалить", font=FONTS['menu'],
            command=self.delete_selected, bg='#e74c3c', fg=COLORS['button_text'],
            relief=tk.FLAT, padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.delete_btn.pack(fill=tk.X, pady=4)
        self.delete_btn.bind('<Enter>', lambda e: self.delete_btn.config(bg='#c0392b'))
        self.delete_btn.bind('<Leave>', lambda e: self.delete_btn.config(bg='#e74c3c'))
        
        self.exit_btn = tk.Button(
            self.buttons_frame, text="Выход", font=FONTS['menu'],
            command=self._on_close, bg=COLORS['button_settings'],
            fg=COLORS['button_text'], relief=tk.FLAT,
            padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        self.exit_btn.pack(fill=tk.X, pady=(4, 0))
        self.exit_btn.bind('<Enter>', lambda e: self.exit_btn.config(bg=COLORS['button_settings_hover']))
        self.exit_btn.bind('<Leave>', lambda e: self.exit_btn.config(bg=COLORS['button_settings']))
        
        # ===== ПРАВАЯ ЧАСТЬ С ПАГИНАЦИЕЙ =====
        self.right_frame = tk.Frame(
            self.content_frame, bg=COLORS['panel_bg'],
            relief=tk.RAISED, bd=SIZES['panel_border']
        )
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(
            self.right_frame, text="Журнал производства продукции",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        # [НОВОЕ] Используем PaginatedTreeview
        self.paginated_tree = PaginatedTreeview(
            self.right_frame,
            columns=('date', 'equipment', 'product', 'color', 'quantity',
                     'cement', 'enriched_sand', 'plasticizer', 'river_sand',
                     'keramzit', 'water'),
            headings={
                'date': 'Дата', 'equipment': 'Оборудование',
                'product': 'Продукция', 'color': 'Цвет',
                'quantity': 'Кол-во, подд.', 'cement': 'Цемент, кг',
                'enriched_sand': 'Обог. песок, кг', 'plasticizer': 'Пластиф., кг',
                'river_sand': 'Речн. песок, кг', 'keramzit': 'Керамзит, кг',
                'water': 'Вода, кг'
            },
            column_widths={
                'date': 75, 'equipment': 100, 'product': 235,
                'color': 80, 'quantity': 100, 'cement': 90,
                'enriched_sand': 110, 'plasticizer': 110,
                'river_sand': 110, 'keramzit': 90, 'water': 70
            },
            page_size=100,
            load_callback=self._load_production_page
        )
        self.paginated_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Двойной клик для информации о расходе цемента
        self.paginated_tree.bind_double_click(self._on_tree_double_click)
        
        self.paginated_tree.load_page(0)
    
    def _load_production_page(self, page, page_size):
        """Callback для загрузки страницы производства"""
        rows, total = production_repo.get_all_paged(page, page_size)
        daily_cement = production_repo.get_daily_cement_totals()
        formatted_rows = []
        for row in rows:
            (prod_id, date, equipment, silo, product, color, quantity,
             cement, enriched_sand, river_sand, keramzit, plasticizer, water, note) = row
            if not product:
                continue
            cement_total = daily_cement.get(date, 0)
            formatted_rows.append((
                date, equipment or '—', product, color or '—',
                self._format_number(quantity), self._format_number(cement_total),
                self._format_number(enriched_sand), self._format_number(plasticizer),
                self._format_number(river_sand), self._format_number(keramzit),
                self._format_number(water)
            ))
        return formatted_rows, total
    
    def _on_product_change(self):
        product = self.product_combo.get().strip().lower()
        keywords = ['блок', 'бордюр', 'желоб']
        if any(keyword in product for keyword in keywords):
            self.color_combo.set('серый')
        else:
            self.color_combo.clear()
    
    def _on_tree_double_click(self, event):
        """Обработчик двойного клика — показывает информацию о расходе цемента за день"""
        values = self.paginated_tree.get_selection()
        if not values:
            return
        date_str = values[0]
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
            edit_btn.bind('<Enter>', lambda e: edit_btn.config(bg=COLORS['button_primary_hover']))
            edit_btn.bind('<Leave>', lambda e: edit_btn.config(bg=COLORS['button_primary']))
        
        close_btn = tk.Button(
            btn_frame, text="Закрыть", font=FONTS['menu'], command=on_close,
            bg=COLORS['button_settings'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind('<Enter>', lambda e: close_btn.config(bg=COLORS['button_settings_hover']))
        close_btn.bind('<Leave>', lambda e: close_btn.config(bg=COLORS['button_settings']))
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
                messagebox.showinfo("Успех", message)
                dialog.destroy()
                self.paginated_tree.refresh()
                self._show_cement_info_dialog(date_str)
            else:
                messagebox.showerror("Ошибка", message)
        
        def on_cancel():
            dialog.destroy()
            self._show_cement_info_dialog(date_str)
        
        save_btn = tk.Button(
            btn_frame, text="Сохранить", font=FONTS['menu'], command=on_save,
            bg=COLORS['button_primary'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg=COLORS['button_primary_hover']))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg=COLORS['button_primary']))
        
        cancel_btn = tk.Button(
            btn_frame, text="Отменить", font=FONTS['menu'], command=on_cancel,
            bg=COLORS['button_settings'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg=COLORS['button_settings_hover']))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg=COLORS['button_settings']))
        dialog.bind('<Escape>', lambda e: on_cancel())
    
    def _on_close(self):
        self.window.grab_release()
        self.window.destroy()
        if self.on_exit_callback:
            self.on_exit_callback()
    
    def get_frame(self):
        return self.window
    
    def _create_field_label(self, text):
        lbl = tk.Label(
            self.left_frame, text=text, font=FONTS['field'],
            bg=COLORS['panel_bg'], fg=COLORS['title_text']
        )
        lbl.pack(anchor='w', padx=10, pady=(2, 1))
    
    def _create_number_entry(self):
        entry = tk.Entry(
            self.left_frame, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        entry.bind('<KeyRelease>', self._validate_number)
        return entry
    
    def _validate_number(self, event=None):
        widget = event.widget
        value = widget.get()
        filtered = ''.join(c for c in value if c.isdigit() or c in '-.,')
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
    
    def edit_selected(self):
        values = self.paginated_tree.get_selection()
        if not values:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return
        
        # Получаем ID через iid (первая колонка — дата, нужно найти prod_id)
        selected_iid = self.paginated_tree.get_selected_iid()
        if not selected_iid:
            return
        
        # Получаем запись из БД по дате (первое поле)
        date_str = values[0]
        all_records = production_repo.get_all()
        record = None
        for r in all_records:
            if str(r[0]) == selected_iid:
                record = r
                break
        
        if not record:
            messagebox.showerror("Ошибка", "Запись не найдена")
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
            messagebox.showwarning("Внимание", "Укажите дату производства")
            return
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
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
            messagebox.showinfo("Успех", message)
            self._clear_fields()
            self.paginated_tree.refresh()
        else:
            messagebox.showerror("Ошибка", message)
    
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
        values = self.paginated_tree.get_selection()
        if not values:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return
        
        date_str = values[0]
        all_records = production_repo.get_all()
        records_for_date = [r for r in all_records if r[1] == date_str]
        count = len(records_for_date)
        
        if not messagebox.askyesno(
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
            self.paginated_tree.refresh()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)