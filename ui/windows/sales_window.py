"""
Окно "Реализация продукции" - учёт продаж продукции
[ИЗМЕНЕНО]
- Поддержка запуска из окна "Продукция в резерве" с предзаполнением полей
- Возврат данных о сохранённой продаже через on_saved_callback
- Ограничение количества остатком резерва (max_quantity)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import products_repo, colors_repo, sales_repo
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class SalesWindow(BaseToplevelWindow):
    """Окно учёта реализации продукции"""

    def __init__(self, parent, on_exit_callback, prefill=None, on_saved_callback=None):
        """
        Args:
            parent: родительское окно
            on_exit_callback: вызывается при закрытии окна
            prefill: словарь предзаполнения (режим "из резерва"):
                {'date', 'product', 'color', 'quantity', 'price', 'max_quantity'}
            on_saved_callback: функция, вызываемая после успешного сохранения
                новой продажи: callback({'sale_id', 'date', 'product',
                                         'color', 'quantity', 'price'})
        """
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.editing_sale_id = None

        # [НОВОЕ] Режим "из резерва"
        self.prefill = prefill
        self.on_saved_callback = on_saved_callback
        self.from_reserve = bool(prefill)
        self.max_quantity = None

        title = "Реализация продукции (из резерва)" if self.from_reserve else "Реализация продукции"
        super().__init__(parent, on_exit_callback, title=title)

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

        # [НОВОЕ] Подсказка в режиме "из резерва"
        if self.from_reserve:
            self.reserve_hint = tk.Label(
                left_inner,
                text="Продажа из резерва.\nПродукция и цвет зафиксированы.",
                font=FONTS['hint'],
                bg=COLORS['panel_bg'],
                fg='#27ae60',
                anchor='w',
                justify='left'
            )
            self.reserve_hint.pack(fill=tk.X, padx=10, pady=(0, 6))

        # Кнопки на всю ширину панели (padx=0 у контейнера)
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

        # [НОВОЕ] Применяем предзаполнение и блокировки в режиме "из резерва"
        if self.from_reserve:
            self._apply_prefill()

    # ========================================================================
    # [НОВОЕ] ПРЕДЗАПОЛНЕНИЕ ИЗ РЕЗЕРВА
    # ========================================================================
    def _apply_prefill(self):
        """Заполнить поля данными из резерва"""
        p = self.prefill or {}
        self.max_quantity = p.get('max_quantity')

        self.date_entry.set_date(p.get('date') or datetime.now().strftime('%d.%m.%Y'))

        # Сначала продукция (её изменение может перезаписать цвет),
        # затем цвет — чтобы цвет из резерва остался корректным
        self.product_combo.set(p.get('product') or '')
        self.color_combo.set(p.get('color') or '')

        self.quantity_entry.delete(0, tk.END)
        if p.get('quantity') is not None:
            self.quantity_entry.insert(0, self._format_number(p['quantity']))

        self.price_entry.delete(0, tk.END)
        if p.get('price'):
            self.price_entry.insert(0, self._format_number(p['price']))

        # Фиксируем продукцию и цвет — продажа должна соответствовать резерву
        self.product_combo.set_disabled(True)
        self.color_combo.set_disabled(True)

        # В режиме "из резерва" редактирование/удаление чужих записей недоступно
        self.edit_btn.config(state='disabled', bg=COLORS['button_disabled'])
        self.delete_btn.config(state='disabled', bg=COLORS['button_disabled'])

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
        filtered = ''.join(c for c in value if c.isdigit() or c in '-.,')
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
        self.date_entry.set_date(date)
        self.product_combo.set(product)
        self.color_combo.set(color or '')
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, self._format_number(price))
        self.editing_sale_id = sale_id
        self.save_btn.config(text="Обновить")
        self.date_entry.entry.focus()

    def save_sale(self):
        date_str = self.date_entry.get_date()
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

        if quantity <= 0:
            messagebox.showwarning("Внимание", "Количество должно быть больше нуля")
            return

        # [НОВОЕ] Ограничение по остатку резерва
        if self.max_quantity is not None and quantity > self.max_quantity + 1e-9:
            messagebox.showwarning(
                "Внимание",
                f"Количество не может превышать остаток резерва:\n"
                f"{self._format_number(self.max_quantity)} шт/м2"
            )
            return

        sale_id = None
        if self.editing_sale_id:
            success, message = sales_repo.update(
                self.editing_sale_id, date_str, product, color, quantity, price, None
            )
            sale_id = self.editing_sale_id
            is_new = False
        else:
            # [ИЗМЕНЕНО] add_with_id возвращает ID новой записи
            success, message, sale_id = sales_repo.add_with_id(
                date_str, product, color, quantity, price, None
            )
            is_new = True

        if not success:
            messagebox.showerror("Ошибка", message)
            return

        # [НОВОЕ] Уведомляем окно резерва о новой реализации
        if is_new and self.on_saved_callback:
            try:
                self.on_saved_callback({
                    'sale_id': sale_id,
                    'date': date_str,
                    'product': product,
                    'color': color,
                    'quantity': quantity,
                    'price': price
                })
            except Exception as e:
                print(f"Ошибка обработчика реализации резерва: {e}")

        # [НОВОЕ] В режиме "из резерва" закрываем окно после сохранения
        if self.from_reserve:
            self._on_close()
            return

        self.product_combo.clear()
        self.color_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        if self.editing_sale_id:
            self.editing_sale_id = None
            self.save_btn.config(text="Сохранить")
        self.load_sales()
        self.product_combo.focus_set()

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