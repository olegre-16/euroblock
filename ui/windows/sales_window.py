"""
Окно "Реализация продукции"
[ИЗМЕНЕНО] Убраны вызовы _restore_window_state() после show_info()
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    products_repo, colors_repo, sales_repo, reserved_products_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class SalesWindow(BaseToplevelWindow):
    def __init__(self, parent, on_exit_callback,
                 prefill_reserve_id=None, prefill_product=None,
                 prefill_color=None, prefill_quantity=None):
        self.prefill_reserve_id = prefill_reserve_id
        self.prefill_product = prefill_product
        self.prefill_color = prefill_color
        self.prefill_quantity = prefill_quantity
        
        self.product_list = [row[0] for row in products_repo.get_all()]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.editing_sale_id = None
        super().__init__(parent, on_exit_callback, title="Реализация продукции")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Реализация продукции")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 6))
        
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
            columns=('date', 'product', 'color', 'quantity', 'price', 'total'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        self.tree.heading('quantity', text='Кол-во, шт/м2', anchor='w')
        self.tree.heading('price', text='Цена, руб.', anchor='w')
        self.tree.heading('total', text='Сумма, руб.', anchor='w')
        self.tree.column('date', width=100, anchor='w')
        self.tree.column('product', width=250, anchor='w')
        self.tree.column('color', width=100, anchor='w')
        self.tree.column('quantity', width=120, anchor='w')
        self.tree.column('price', width=120, anchor='w')
        self.tree.column('total', width=130, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_sales()
        self._apply_prefill()
    
    def _apply_prefill(self):
        today = datetime.now().strftime('%d.%m.%Y')
        self.date_entry.set_date(today)
        
        if self.prefill_product:
            self.product_combo.set(self.prefill_product)
        if self.prefill_color:
            self.color_combo.set(self.prefill_color)
        if self.prefill_quantity is not None:
            self.quantity_entry.delete(0, tk.END)
            self.quantity_entry.insert(0, self._format_number(self.prefill_quantity))
        self.price_entry.focus_set()
    
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
            total = (quantity or 0) * (price or 0)
            self.tree.insert(
                '', 'end', iid=str(sale_id),
                values=(date, product, color or '—',
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
            self.show_warning("Внимание", "Выберите запись для редактирования")
            return
        sale_id = int(selected[0])
        sale = sales_repo.get_by_id(sale_id)
        if not sale:
            self.show_error("Ошибка", "Запись не найдена")
            return
        if len(sale) == 7:
            _, date, product, color, quantity, price, equipment = sale
        else:
            _, date, product, color, quantity, price = sale
        self.date_entry.set_date(date)
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
        """
        Сохранить продажу.
        [ИЗМЕНЕНО] Гарантированная запись в историю реализаций из резерва.
        """
        date_str = self.date_entry.get_date()
        product = self.product_combo.get().strip()
        color = self.color_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        price_str = self.price_entry.get().strip()
        
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
        if not quantity_str or not price_str:
            self.show_warning("Внимание", "Укажите количество и цену")
            return
        try:
            quantity = float(quantity_str.replace(',', '.'))
            price = float(price_str.replace(',', '.'))
        except ValueError:
            self.show_warning("Внимание", "Неверный формат числа")
            return
        
        # Сохраняем продажу в основную таблицу
        if self.editing_sale_id:
            success, message = sales_repo.update(
                self.editing_sale_id, date_str, product, color, quantity, price, None
            )
        else:
            success, message = sales_repo.add(
                date_str, product, color, quantity, price, None
            )
        
        if not success:
            self.show_error("Ошибка", message)
            return
        
        # [ИЗМЕНЕНО] Если это реализация из резерва — записываем в историю
        # Используем getattr для безопасного доступа к атрибуту
        reserve_id = getattr(self, 'prefill_reserve_id', None)
        
        if reserve_id is not None:
            print(f"→ Запись реализации из резерва: reserve_id={reserve_id}, qty={quantity}")
            
            try:
                hist_success, hist_message = reserved_products_repo.add_reserve_sale(
                    reserve_id, date_str, quantity
                )
                
                if hist_success:
                    print(f"✓ История реализаций обновлена успешно")
                    
                    # Закрываем окно и вызываем callback для обновления таблицы резервов
                    self._on_close()
                    return
                else:
                    # Если не удалось добавить в историю — показываем ошибку, но продажу сохраняем
                    print(f"✗ Ошибка добавления в историю: {hist_message}")
                    self.show_warning(
                        "Внимание",
                        f"Продажа сохранена, но не добавлена в историю резерва:\n{hist_message}"
                    )
            except Exception as e:
                print(f"✗ Исключение при добавлении в историю: {e}")
                import traceback
                traceback.print_exc()
                self.show_warning(
                    "Внимание",
                    f"Продажа сохранена, но произошла ошибка при добавлении в историю:\n{e}"
                )
            
            # Закрываем окно даже при ошибке истории
            self._on_close()
            return
        
        # Обычное поведение — очищаем поля и обновляем таблицу
        self.product_combo.clear()
        self.color_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        if self.editing_sale_id:
            self.editing_sale_id = None
            self.save_btn.config(text="Сохранить")
        self.load_sales()
        self.product_combo.focus_set()
        self.show_info("Успех", message)
        
            
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для удаления")
            return
        sale_id = int(selected[0])
        sale = sales_repo.get_by_id(sale_id)
        if not sale:
            self.show_error("Ошибка", "Запись не найдена")
            return
        if len(sale) == 7:
            _, date, product, color, quantity, price, equipment = sale
        else:
            _, date, product, color, quantity, price = sale
        total = (quantity or 0) * (price or 0)
        if not self.ask_yes_no(
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
            # [ИЗМЕНЕНО] Убран _restore_window_state()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)
    
    def _on_auto_refresh(self):
        try:
            self.load_sales()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в SalesWindow: {e}")