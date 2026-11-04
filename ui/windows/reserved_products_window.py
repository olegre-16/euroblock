"""
Окно "Продукция в резерве" - учёт резервирования продукции
[ИЗМЕНЕНО]
- Сортировка в три группы: не реализована → частично → полностью
- Внутри каждой группы — по дате убывания
- Цвета строк:
    • Не реализована — обычный белый фон
    • Частично реализована — светло-фиолетовый
    • Полностью реализована — светло-зелёный
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    products_repo, colors_repo, customers_repo, reserved_products_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.windows.sales_window import SalesWindow
from ui.base_window import BaseToplevelWindow


# ============================================================================
# [НОВОЕ] Цвета строк по состоянию реализации
# ============================================================================
REALIZE_BTN_BG = '#27ae60'           # Зелёный для кнопки "Реализация"
REALIZE_BTN_BG_HOVER = '#1e8449'
PARTIALLY_REALIZED_BG = '#E8DAEF'    # Светло-фиолетовый — частично реализована
FULLY_REALIZED_BG = '#D5F5E3'        # Светло-зелёный — полностью реализована


class ReservedProductsWindow(BaseToplevelWindow):
    """Окно учёта резервирования продукции"""

    def __init__(self, parent, on_exit_callback):
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.customer_list = [row[0] for row in customers_repo.get_all()]
        self.editing_id = None
        self.sales_window = None
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

        # Кнопки на всю ширину панели
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))

        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_reservation,
                                        color=COLORS['button_primary'])
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())

        # Кнопка "Реализация" — сразу после "Сохранить"
        self.realize_btn = self.add_button(buttons_frame, "Реализация", self.realize_selected,
                                           color=REALIZE_BTN_BG)
        self.realize_btn.bind('<Enter>', lambda e: self.realize_btn.config(bg=REALIZE_BTN_BG_HOVER))
        self.realize_btn.bind('<Leave>', lambda e: self.realize_btn.config(bg=REALIZE_BTN_BG))

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

        # Отдельный стиль, чтобы высота строк не влияла на другие окна
        style = ttk.Style()
        style.configure('Reserve.Treeview', font=FONTS['table_cell'], rowheight=25)
        style.configure('Reserve.Treeview.Heading', font=FONTS['table_heading'])

        self.tree = ttk.Treeview(
            tree_container,
            columns=('start_date', 'end_date', 'product', 'color',
                     'quantity', 'customer', 'realized'),
            show='headings',
            style='Reserve.Treeview',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        self.tree.heading('start_date', text='Дата начала', anchor='w')
        self.tree.heading('end_date', text='Дата конца', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        self.tree.heading('quantity', text='Кол-во, шт/м2', anchor='w')
        self.tree.heading('customer', text='Заказчик', anchor='w')
        self.tree.heading('realized', text='Реализовано', anchor='w')

        self.tree.column('start_date', width=85, anchor='w')
        self.tree.column('end_date', width=85, anchor='w')
        self.tree.column('product', width=190, anchor='w')
        self.tree.column('color', width=80, anchor='w')
        self.tree.column('quantity', width=110, anchor='w')
        self.tree.column('customer', width=140, anchor='w')
        self.tree.column('realized', width=220, anchor='w')

        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # [ИЗМЕНЕНО] Настраиваем теги для раскраски строк по состоянию
        # (вместо старого тега 'realized' с тёмно-зелёным фоном)
        self.tree.tag_configure('partially_realized', background=PARTIALLY_REALIZED_BG)
        self.tree.tag_configure('fully_realized', background=FULLY_REALIZED_BG)

        self.load_reservations()

    # ========================================================================
    # [НОВОЕ] СОРТИРОВКА ПО ТРЁМ ГРУППАМ
    # ========================================================================
    @staticmethod
    def _date_to_comparable(d):
        """Преобразовать дату ДД.ММ.ГГГГ в число для сортировки"""
        try:
            parts = d.split('.')
            if len(parts) == 3:
                day, month, year = parts
                return int(f"{year}{month.zfill(2)}{day.zfill(2)}")
        except (ValueError, AttributeError):
            pass
        return 0

    @staticmethod
    def _classify_reservation(reserved_qty, realized_total):
        """
        Определить класс резерва.
        Returns:
            0 — не реализована (приоритет выше, выводится первой)
            1 — частично реализована
            2 — полностью реализована (приоритет ниже, выводится последней)
        """
        if reserved_qty <= 0:
            return 2
        if realized_total <= 0:
            return 0
        remaining = reserved_qty - realized_total
        if remaining <= 0:
            return 2
        return 1

    # ========================================================================
    # РЕАЛИЗАЦИЯ РЕЗЕРВА
    # ========================================================================
    def realize_selected(self):
        """Открыть окно 'Реализация продукции' с данными выбранного резерва"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите резерв для реализации")
            return

        res_id = int(selected[0])
        record = reserved_products_repo.get_by_id(res_id)
        if not record:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return

        _, start_date, end_date, product, color, quantity, customer = record

        realizations = reserved_products_repo.get_realizations_map().get(res_id, [])
        total_realized = sum(q for _, q in realizations)
        remaining = (quantity or 0) - total_realized

        if remaining <= 0:
            messagebox.showinfo(
                "Информация",
                "Этот резерв уже реализован полностью."
            )
            return

        prefill = {
            'date': datetime.now().strftime('%d.%m.%Y'),
            'product': product,
            'color': color or '',
            'quantity': remaining,
            'price': None,
            'max_quantity': remaining
        }

        self.sales_window = SalesWindow(
            self.window,
            self._on_sales_window_closed,
            prefill=prefill,
            on_saved_callback=lambda data, rid=res_id: self._register_realization(rid, data)
        )

    def _register_realization(self, reserve_id, data):
        """Записать факт реализации после сохранения продажи"""
        success, message = reserved_products_repo.add_realization(
            reserve_id,
            data.get('date'),
            data.get('quantity'),
            data.get('sale_id')
        )
        if not success:
            messagebox.showerror(
                "Ошибка",
                f"Продажа сохранена, но не удалось записать реализацию резерва:\n{message}"
            )
        self.load_reservations()

    def _on_sales_window_closed(self):
        """Вызывается при закрытии окна реализации"""
        self.sales_window = None
        self.load_reservations()
        self._restore_window_state()

    # ========================================================================
    # [ИЗМЕНЕНО] ЗАГРУЗКА ТАБЛИЦЫ С СОРТИРОВКОЙ ПО ТРЁМ ГРУППАМ
    # ========================================================================
    def load_reservations(self):
        """
        Загрузить резервы с сортировкой:
        1. Не реализованные (по дате убывания)
        2. Частично реализованные (по дате убывания) — светло-фиолетовые
        3. Полностью реализованные (по дате убывания) — светло-зелёные
        """
        for item in self.tree.get_children():
            self.tree.delete(item)

        records = reserved_products_repo.get_all_reserved()
        realizations_map = reserved_products_repo.get_realizations_map()

        # [НОВОЕ] Собираем все записи с дополнительной информацией
        items_data = []
        for row in records:
            res_id, start_date, end_date, product, color, quantity, customer = row
            reserved_qty = quantity or 0

            realizations = realizations_map.get(res_id, [])
            total_realized = sum(q for _, q in realizations)
            remaining = reserved_qty - total_realized
            if remaining < 0:
                remaining = 0

            # Определяем класс (0/1/2)
            cls = self._classify_reservation(reserved_qty, total_realized)

            # Формируем текст столбца "Реализовано"
            lines = []
            for idx, (sale_date, qty) in enumerate(realizations):
                is_last = (idx == len(realizations) - 1)
                if is_last and total_realized > 0 and remaining <= 0:
                    lines.append(f"{sale_date} - реализовано полностью")
                else:
                    lines.append(f"{sale_date} - {self._format_number(qty)}")

            realized_text = "\n".join(lines) if lines else '—'

            # Формируем текст столбца "Количество"
            if total_realized <= 0:
                qty_text = self._format_number(reserved_qty)
            elif remaining <= 0:
                qty_text = self._format_number(reserved_qty)
            else:
                qty_text = (f"{self._format_number(remaining)} / "
                            f"{self._format_number(total_realized)}")

            # Определяем тег строки
            if cls == 1:
                tag = 'partially_realized'
            elif cls == 2:
                tag = 'fully_realized'
            else:
                tag = ''

            items_data.append({
                'res_id': res_id,
                'start_date': start_date,
                'end_date': end_date,
                'product': product,
                'color': color,
                'qty_text': qty_text,
                'customer': customer,
                'realized_text': realized_text,
                'tag': tag,
                'cls': cls,
                'date_key': self._date_to_comparable(start_date),
                'max_lines': len(lines) if lines else 1
            })

        # [НОВОЕ] Сортировка:
        # 1-й ключ — класс (0 → 1 → 2)
        # 2-й ключ — дата убывания (отрицание для убывания)
        # 3-й ключ — id убывания (для стабильности при одинаковых датах)
        items_data.sort(key=lambda x: (x['cls'], -x['date_key'], -x['res_id']))

        # Вставляем в таблицу
        max_lines = 1
        for item in items_data:
            tags = (item['tag'],) if item['tag'] else ()
            self.tree.insert(
                '', 'end', iid=str(item['res_id']),
                values=(item['start_date'], item['end_date'], item['product'],
                        item['color'] or '—', item['qty_text'],
                        item['customer'] or '—', item['realized_text']),
                tags=tags
            )
            max_lines = max(max_lines, item['max_lines'])

        self._adjust_row_height(max_lines)

    def _adjust_row_height(self, max_lines):
        """Подстроить высоту строк под максимальное число строк в столбце 'Реализовано'"""
        try:
            font_obj = tkfont.Font(font=FONTS['table_cell'])
            line_height = font_obj.metrics('linespace')
            new_height = max(25, line_height * max_lines + 8)
            style = ttk.Style()
            style.configure('Reserve.Treeview', rowheight=new_height)
        except Exception as e:
            print(f"Ошибка настройки высоты строк: {e}")

    # ========================================================================
    # ОБЫЧНЫЕ ОПЕРАЦИИ
    # ========================================================================
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
        if self.editing_id:
            self.save_btn.config(bg=REALIZE_BTN_BG)
        else:
            self.save_btn.config(bg=COLORS['button_primary_hover'])

    def _on_save_leave(self):
        if self.editing_id:
            self.save_btn.config(bg=REALIZE_BTN_BG)
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
            f"Количество: {self._format_number(quantity)}\n\n"
            f"Связанные отметки о реализации также будут удалены.\n"
            f"Записи в журнале реализации останутся."
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