"""
Окно "Продукция в резерве" - учёт резервирования продукции
[ИЗМЕНЕНО] Кнопки "Сохранить", "Изменить", "Удалить" теперь той же ширины, что и "Выход".
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    products_repo, colors_repo, customers_repo, reserved_products_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class ReservedProductsWindow(BaseToplevelWindow):
    """Окно учёта резервирования продукции"""
    def __init__(self, parent, on_exit_callback):
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.customer_list = [row[0] for row in customers_repo.get_all()]
        self.editing_id = None
        super().__init__(parent, on_exit_callback, title="Продукция в резерве")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Продукция в резерве")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата начала:")
        self.start_date_entry = DateEntry(left_inner)
        self.start_date_entry.pack(fill=tk.X, padx=10, pady=(10, 6))
        
        self.add_field_label(left_inner, "Дата конца:")
        self.end_date_entry = DateEntry(left_inner)
        self.end_date_entry.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.add_field_label(left_inner, "Продукция:")
        self.product_combo = AutocompleteCombobox(left_inner, values=self.product_list)
        self.product_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.product_combo.bind_text_change(self._on_product_change)
        
        self.add_field_label(left_inner, "Цвет:")
        self.color_combo = AutocompleteCombobox(left_inner, values=self.color_list)
        self.color_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.add_field_label(left_inner, "Количество, шт/м2:")
        self.quantity_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 6), ipady=SIZES['field_ipady'])
        self.quantity_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Заказчик:")
        self.customer_combo = AutocompleteCombobox(left_inner, values=self.customer_list)
        self.customer_combo.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        # [ИЗМЕНЕНО] Убран padx=10 у buttons_frame, чтобы кнопки внутри имели
        # только один padx=10 от add_button (как у кнопки "Выход")
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))
        
        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_reservation,
                                        color=COLORS['button_primary'])
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        self.edit_btn = self.add_button(buttons_frame, "Изменить", self.edit_selected,
                                        color='#f39c12')
        self.delete_btn = self.add_button(buttons_frame, "Удалить", self.delete_selected,
                                          color='#e74c3c')
        
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ===== ПРАВАЯ ЧАСТЬ =====
        right_frame = self.create_right_panel(content_frame)
        tk.Label(
            right_frame, text="Журнал резервирования продукции",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('start_date', 'end_date', 'product', 'color', 'quantity', 'customer'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        self.tree.heading('start_date', text='Дата начала', anchor='w')
        self.tree.heading('end_date', text='Дата конца', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        self.tree.heading('quantity', text='Кол-во, шт/м2', anchor='w')
        self.tree.heading('customer', text='Заказчик', anchor='w')
        self.tree.column('start_date', width=90, anchor='w')
        self.tree.column('end_date', width=90, anchor='w')
        self.tree.column('product', width=200, anchor='w')
        self.tree.column('color', width=90, anchor='w')
        self.tree.column('quantity', width=100, anchor='w')
        self.tree.column('customer', width=150, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_reservations()
    
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
    
    def load_reservations(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        records = reserved_products_repo.get_all_reserved()
        for row in records:
            res_id, start_date, end_date, product, color, quantity, customer = row
            self.tree.insert(
                '', 'end', iid=str(res_id),
                values=(start_date, end_date, product, color or '—',
                        self._format_number(quantity), customer or '—')
            )
    
    def save_reservation(self):
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        product = self.product_combo.get().strip()
        color = self.color_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        customer = self.customer_combo.get().strip()
        
        if not start_date or not end_date:
            messagebox.showwarning("Внимание", "Укажите даты начала и конца резерва")
            return
        try:
            datetime.strptime(start_date, '%d.%m.%Y')
            datetime.strptime(end_date, '%d.%m.%Y')
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        if not product:
            messagebox.showwarning("Внимание", "Выберите продукцию")
            return
        if not quantity_str:
            messagebox.showwarning("Внимание", "Укажите количество")
            return
        try:
            quantity = float(quantity_str.replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат количества")
            return
        
        if self.editing_id:
            success, message = reserved_products_repo.update(
                self.editing_id, start_date, end_date, product, color, quantity, customer
            )
        else:
            success, message = reserved_products_repo.add(
                start_date, end_date, product, color, quantity, customer
            )
        
        if success:
            self._clear_fields()
            self.load_reservations()
        else:
            messagebox.showerror("Ошибка", message)
    
    def _clear_fields(self):
        self.start_date_entry.clear()
        self.end_date_entry.clear()
        self.product_combo.clear()
        self.color_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.customer_combo.clear()
        self.editing_id = None
        self.save_btn.config(text="Сохранить")
    
    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return
        res_id = int(selected[0])
        record = reserved_products_repo.get_by_id(res_id)
        if not record:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return
        _, start_date, end_date, product, color, quantity, customer = record
        self.start_date_entry.set_date(start_date)
        self.end_date_entry.set_date(end_date)
        self.product_combo.set(product)
        self.color_combo.set(color or '')
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        self.customer_combo.set(customer or '')
        self.editing_id = res_id
        self.save_btn.config(text="Обновить")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return
        res_id = int(selected[0])
        record = reserved_products_repo.get_by_id(res_id)
        if not record:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return
        _, start_date, end_date, product, color, quantity, customer = record
        if not messagebox.askyesno(
            "Подтверждение",
            f"Удалить резерв?\n\n"
            f"Период: {start_date} - {end_date}\n"
            f"Продукция: {product}\n"
            f"Количество: {self._format_number(quantity)}"
        ):
            return
        success, message = reserved_products_repo.delete(res_id)
        if success:
            if self.editing_id == res_id:
                self._clear_fields()
            self.load_reservations()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)