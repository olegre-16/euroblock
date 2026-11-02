"""
Окно "Реализация продукции" - учёт продаж продукции
[ИЗМЕНЕНО] Кнопки "Сохранить", "Изменить", "Удалить" теперь той же ширины, что и "Выход".
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    products_repo, colors_repo, sales_repo, equipment_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class SalesWindow(BaseToplevelWindow):
    """Окно учёта реализации продукции"""
    def __init__(self, parent, on_exit_callback):
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.equipment_list = [row[0] for row in equipment_repo.get_all()]
        self.editing_sale_id = None
        super().__init__(parent, on_exit_callback, title="Реализация продукции")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Реализация продукции")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 6))
        
        self.add_field_label(left_inner, "Оборудование:")
        self.equipment_combo = AutocompleteCombobox(left_inner, values=self.equipment_list)
        self.equipment_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.add_field_label(left_inner, "Продукция:")
        self.product_combo = AutocompleteCombobox(left_inner, values=self.product_list)
        self.product_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        self.product_combo.bind_text_change(self._on_product_change)
        
        self.add_field_label(left_inner, "Цвет:")
        self.color_combo = AutocompleteCombobox(left_inner, values=self.color_list)
        self.color_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.add_field_label(left_inner, "Кол-во., шт/м2:")
        self.quantity_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 6), ipady=SIZES['field_ipady'])
        self.quantity_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Цена, руб.:")
        self.price_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.price_entry.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=SIZES['field_ipady'])
        self.price_entry.bind('<KeyRelease>', self._validate_number)
        
        # [ИЗМЕНЕНО] Убран padx=10 у buttons_frame
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))
        
        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_sale, 
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
            right_frame, text="Журнал реализации продукции",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('date', 'equipment', 'product', 'color', 'quantity', 'price', 'total'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('equipment', text='Оборудование', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        self.tree.heading('quantity', text='Кол-во, шт/м2', anchor='w')
        self.tree.heading('price', text='Цена, руб.', anchor='w')
        self.tree.heading('total', text='Сумма, руб.', anchor='w')
        self.tree.column('date', width=90, anchor='w')
        self.tree.column('equipment', width=120, anchor='w')
        self.tree.column('product', width=200, anchor='w')
        self.tree.column('color', width=90, anchor='w')
        self.tree.column('quantity', width=110, anchor='w')
        self.tree.column('price', width=110, anchor='w')
        self.tree.column('total', width=120, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_sales()
    
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
        if self.editing_sale_id:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary_hover'])
    
    def _on_save_leave(self):
        if self.editing_sale_id:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary'])
    
    def load_sales(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        sales = sales_repo.get_all()
        for row in sales:
            if len(row) == 7:
                sale_id, date, product, color, quantity, price, equipment = row
            else:
                sale_id, date, product, color, quantity, price = row
                equipment = ''
            total = (quantity or 0) * (price or 0)
            self.tree.insert(
                '', 'end', iid=str(sale_id),
                values=(date, equipment or '—', product, color or '—',
                        self._format_number(quantity), self._format_number(price),
                        self._format_number(total))
            )
    
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
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return
        sale_id = int(selected[0])
        sale = sales_repo.get_by_id(sale_id)
        if not sale:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return
        if len(sale) == 7:
            _, date, product, color, quantity, price, equipment = sale
        else:
            _, date, product, color, quantity, price = sale
            equipment = ''
        self.date_entry.set_date(date)
        self.equipment_combo.set(equipment or '')
        self.color_combo.set(color or '')
        self.product_combo.set(product)
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, self._format_number(price))
        self.editing_sale_id = sale_id
        self.save_btn.config(text="Обновить")
        self.date_entry.entry.focus()
    
    def save_sale(self):
        date_str = self.date_entry.get_date()
        equipment = self.equipment_combo.get().strip()
        product = self.product_combo.get().strip()
        color = self.color_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        price_str = self.price_entry.get().strip()
        
        if not date_str:
            messagebox.showwarning("Внимание", "Укажите дату")
            return
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        if not product:
            messagebox.showwarning("Внимание", "Выберите продукцию")
            return
        if not quantity_str or not price_str:
            messagebox.showwarning("Внимание", "Укажите количество и цену")
            return
        try:
            quantity = float(quantity_str.replace(',', '.'))
            price = float(price_str.replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат числа")
            return
        
        if self.editing_sale_id:
            success, message = sales_repo.update(
                self.editing_sale_id, date_str, product, color, quantity, price, equipment
            )
        else:
            success, message = sales_repo.add(
                date_str, product, color, quantity, price, equipment
            )
        
        if success:
            self.product_combo.clear()
            self.color_combo.clear()
            self.equipment_combo.clear()
            self.quantity_entry.delete(0, tk.END)
            self.price_entry.delete(0, tk.END)
            if self.editing_sale_id:
                self.editing_sale_id = None
                self.save_btn.config(text="Сохранить")
            self.load_sales()
            self.product_combo.focus_set()
        else:
            messagebox.showerror("Ошибка", message)
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return
        sale_id = int(selected[0])
        sale = sales_repo.get_by_id(sale_id)
        if not sale:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return
        if len(sale) == 7:
            _, date, product, color, quantity, price, equipment = sale
        else:
            _, date, product, color, quantity, price = sale
            equipment = ''
        total = (quantity or 0) * (price or 0)
        if not messagebox.askyesno(
            "Подтверждение",
            f"Удалить запись о продаже?\n\n"
            f"Дата: {date}\nПродукция: {product}\n"
            f"Сумма: {self._format_number(total)} руб."
        ):
            return
        success, message = sales_repo.delete(sale_id)
        if success:
            if self.editing_sale_id == sale_id:
                self.editing_sale_id = None
                self.save_btn.config(text="Сохранить")
            self.load_sales()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)