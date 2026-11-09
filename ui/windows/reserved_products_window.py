"""
Окно "Продукция в резерве" - учёт резервирования продукции

[ВАЖНО] Tkinter Treeview не поддерживает многострочный текст в ячейках.
Поэтому для отображения нескольких реализаций одного резерва используется
несколько строк Treeview, визуально объединённых через одинаковые теги.

Логика отображения:
- Каждый резерв занимает N строк (где N = количество реализаций, минимум 1)
- В первой строке заполняются ВСЕ колонки
- В остальных строках заполняется ТОЛЬКО колонка "Реализовано"
- Все строки одного резерва имеют одинаковый цвет фона (через теги)
- При выборе любой строки резерва — выделяется весь резерв
"""
import tkinter as tk
from tkinter import ttk
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
        self.product_list = [row[0] for row in products_repo.get_all()]
        self.color_list = [row[0] for row in colors_repo.get_all()]
        self.customer_list = [row[0] for row in customers_repo.get_all()]
        self.editing_id = None
        # Храним соответствие iid -> res_id для корректной работы кнопок
        self._iid_to_res_id = {}
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
        
        # КНОПКИ
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))
        
        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_reservation,
                                        color=COLORS['button_primary'])
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        self.realize_btn = self.add_button(buttons_frame, "Реализация", self.on_realize,
                                           color='#27ae60')
        self.realize_btn.bind('<Enter>', lambda e: self.realize_btn.config(bg='#229954'))
        self.realize_btn.bind('<Leave>', lambda e: self.realize_btn.config(bg='#27ae60'))
        
        self.edit_btn = self.add_button(buttons_frame, "Изменить", self.edit_selected,
                                        color='#f39c12')
        self.delete_btn = self.add_button(buttons_frame, "Удалить", self.delete_selected,
                                          color='#e74c3c')
        
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ПРАВАЯ ЧАСТЬ
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
            columns=('start_date', 'end_date', 'product', 'color', 'quantity',
                     'customer', 'realized'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        self.tree.heading('start_date', text='Дата начала', anchor='w')
        self.tree.heading('end_date', text='Дата конца', anchor='w')
        self.tree.heading('product', text='Продукция', anchor='w')
        self.tree.heading('color', text='Цвет', anchor='w')
        self.tree.heading('quantity', text='Остаток / Реализовано', anchor='w')
        self.tree.heading('customer', text='Заказчик', anchor='w')
        self.tree.heading('realized', text='Реализовано', anchor='w')
        self.tree.column('start_date', width=80, anchor='w')
        self.tree.column('end_date', width=80, anchor='w')
        self.tree.column('product', width=180, anchor='w')
        self.tree.column('color', width=80, anchor='w')
        self.tree.column('quantity', width=130, anchor='w')
        self.tree.column('customer', width=130, anchor='w')
        self.tree.column('realized', width=220, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Настраиваем теги для подсветки строк
        # Частично реализована — светло-зелёный фон
        self.tree.tag_configure('partially_sold', background='#d4edda')
        # Полностью реализована — светло-фиолетовый фон
        self.tree.tag_configure('fully_sold', background='#e1bee7')
        # Выделение строки при выборе
        self.tree.tag_configure('selected_reserve', background='#b3d9ff')
        
        # Привязываем обработчик выбора строки для выделения всего резерва
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        
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
    
    def _date_to_sortable(self, date_str):
        """Преобразовать дату ДД.ММ.ГГГГ в числовой формат для сортировки"""
        try:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                return int(f"{year}{month.zfill(2)}{day.zfill(2)}")
        except (ValueError, AttributeError):
            pass
        return 0
    
    # ========================================================================
    # Обработчик выбора строки — выделяет все строки одного резерва
    # ========================================================================
    def _on_tree_select(self, event):
        """При выборе строки — подсвечиваем все строки этого резерва"""
        selected = self.tree.selection()
        if not selected:
            return
        
        # Получаем res_id из выбранной строки
        selected_iid = selected[0]
        res_id = self._iid_to_res_id.get(selected_iid)
        if res_id is None:
            return
        
        # Снимаем выделение со всех строк
        for iid in self.tree.get_children():
            current_tags = self.tree.item(iid, 'tags')
            # Убираем тег selected_reserve, оставляем остальные
            new_tags = tuple(t for t in current_tags if t != 'selected_reserve')
            self.tree.item(iid, tags=new_tags)
        
        # Выделяем все строки этого резерва
        for iid, rid in self._iid_to_res_id.items():
            if rid == res_id:
                current_tags = self.tree.item(iid, 'tags')
                if 'selected_reserve' not in current_tags:
                    self.tree.item(iid, tags=current_tags + ('selected_reserve',))
    
    # ========================================================================
    # Получение res_id из выбранной строки
    # ========================================================================
    def _get_selected_res_id(self):
        """Получить ID резерва из выбранной строки"""
        selected = self.tree.selection()
        if not selected:
            return None
        return self._iid_to_res_id.get(selected[0])
    
    # ========================================================================
    # Загрузка данных — несколько строк на резерв
    # ========================================================================
    def load_reservations(self):
        """
        Загрузить данные в таблицу.
        
        ЛОГИКА ОТОБРАЖЕНИЯ (из-за ограничения Tkinter):
        - Каждый резерв занимает N строк (N = количество реализаций, минимум 1)
        - В первой строке заполняются ВСЕ колонки
        - В остальных строках заполняется ТОЛЬКО колонка "Реализовано"
        - Все строки одного резерва имеют одинаковый цвет фона
        - В колонке "Количество" первой строки: "остаток/реализовано"
        - В колонке "Количество" остальных строк: пусто
        
        СОРТИРОВКА:
        1. Без реализаций (по дате начала, возрастание)
        2. Частично реализованные (по дате начала, возрастание)
        3. Полностью реализованные (по дате начала, возрастание)
        """
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._iid_to_res_id.clear()
        
        records = reserved_products_repo.get_all_reserved()
        if not records:
            return
        
        all_sales = reserved_products_repo.get_all_reserve_sales()
        
        # Собираем данные по резервам
        reserves_data = []
        
        for row in records:
            try:
                # Безопасная распаковка кортежа
                if len(row) >= 7:
                    res_id, start_date, end_date, product, color, quantity, customer = row[:7]
                elif len(row) >= 6:
                    res_id, start_date, end_date, product, color, quantity = row[:6]
                    customer = ''
                else:
                    continue
                
                # Получаем историю реализаций
                sales_history = all_sales.get(res_id, [])
                
                # Определяем статус
                if not sales_history:
                    status = 'no_sales'
                    sold_sum = 0
                    remaining = quantity
                else:
                    sold_sum = sum(qty for _, qty in sales_history)
                    remaining = quantity - sold_sum
                    status = 'fully_sold' if remaining <= 0 else 'partially_sold'
                
                # Определяем тег для подсветки
                if status == 'partially_sold':
                    status_tag = 'partially_sold'
                elif status == 'fully_sold':
                    status_tag = 'fully_sold'
                else:
                    status_tag = None
                
                # Ключ сортировки — дата начала резерва (возрастание)
                sort_key = self._date_to_sortable(start_date)
                
                # Формируем текст для колонки "Количество" (только для первой строки)
                if not sales_history:
                    quantity_text = self._format_number(quantity)
                else:
                    quantity_text = f"{self._format_number(remaining)}/{self._format_number(sold_sum)}"
                
                # Формируем данные для строк
                reserve_info = {
                    'res_id': res_id,
                    'status': status,
                    'status_tag': status_tag,
                    'sort_key': sort_key,
                    'start_date': start_date,
                    'end_date': end_date,
                    'product': product,
                    'color': color,
                    'quantity_text': quantity_text,
                    'customer': customer,
                    'sales_history': sales_history
                }
                
                reserves_data.append(reserve_info)
            
            except Exception as e:
                print(f"⚠ Ошибка обработки записи {row}: {e}")
                continue
        
        # ====================================================================
        # СОРТИРОВКА: сначала без реализаций, затем частично, затем полностью
        # ====================================================================
        status_order = {'no_sales': 0, 'partially_sold': 1, 'fully_sold': 2}
        reserves_data.sort(key=lambda x: (status_order[x['status']], x['sort_key']))
        
        # ====================================================================
        # ВЫВОД В TABLE
        # ====================================================================
        for reserve in reserves_data:
            res_id = reserve['res_id']
            status_tag = reserve['status_tag']
            sales_history = reserve['sales_history']
            
            if not sales_history:
                # Нет реализаций — одна строка со всеми данными
                row_data = (
                    reserve['start_date'],
                    reserve['end_date'],
                    reserve['product'],
                    reserve['color'] or '—',
                    reserve['quantity_text'],
                    reserve['customer'] or '—',
                    ''  # Пустая колонка "Реализовано"
                )
                iid = f"res_{res_id}_0"
                tags = (status_tag,) if status_tag else ()
                self.tree.insert('', 'end', iid=iid, values=row_data, tags=tags)
                self._iid_to_res_id[iid] = res_id
            else:
                # Есть реализации — несколько строк
                for idx, (sale_date, sale_qty) in enumerate(sales_history):
                    if idx == 0:
                        # Первая строка — все колонки заполнены
                        row_data = (
                            reserve['start_date'],
                            reserve['end_date'],
                            reserve['product'],
                            reserve['color'] or '—',
                            reserve['quantity_text'],
                            reserve['customer'] or '—',
                            f"{sale_date} - {self._format_number(sale_qty)}"
                        )
                    else:
                        # Последующие строки — только колонка "Реализовано"
                        row_data = (
                            '',  # Дата начала пустая
                            '',  # Дата конца пустая
                            '',  # Продукция пустая
                            '',  # Цвет пустой
                            '',  # Количество пустое
                            '',  # Заказчик пустой
                            f"{sale_date} - {self._format_number(sale_qty)}"
                        )
                    
                    iid = f"res_{res_id}_{idx}"
                    tags = (status_tag,) if status_tag else ()
                    self.tree.insert('', 'end', iid=iid, values=row_data, tags=tags)
                    self._iid_to_res_id[iid] = res_id
    
    def save_reservation(self):
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        product = self.product_combo.get().strip()
        color = self.color_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        customer = self.customer_combo.get().strip()
        
        if not start_date or not end_date:
            self.show_warning("Внимание", "Укажите даты начала и конца резерва")
            return
        try:
            datetime.strptime(start_date, '%d.%m.%Y')
            datetime.strptime(end_date, '%d.%m.%Y')
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
        except ValueError:
            self.show_warning("Внимание", "Неверный формат количества")
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
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)
    
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
        res_id = self._get_selected_res_id()
        if res_id is None:
            self.show_warning("Внимание", "Выберите запись для редактирования")
            return
        
        record = reserved_products_repo.get_by_id(res_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        
        if len(record) >= 7:
            _, start_date, end_date, product, color, quantity, customer = record[:7]
        elif len(record) >= 6:
            _, start_date, end_date, product, color, quantity = record[:6]
            customer = ''
        else:
            self.show_error("Ошибка", "Неверный формат записи")
            return
        
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
        """Удалить выбранную запись."""
        res_id = self._get_selected_res_id()
        if res_id is None:
            self.show_warning("Внимание", "Выберите запись для удаления")
            return
        
        record = reserved_products_repo.get_by_id(res_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        
        if len(record) >= 7:
            _, start_date, end_date, product, color, quantity, customer = record[:7]
        elif len(record) >= 6:
            _, start_date, end_date, product, color, quantity = record[:6]
        else:
            self.show_error("Ошибка", "Неверный формат записи")
            return
        
        # Проверяем, есть ли реализации по этому резерву
        sales_history = reserved_products_repo.get_reserve_sales(res_id)
        
        if sales_history:
            sold_sum = sum(qty for _, qty in sales_history)
            if not self.ask_yes_no(
                "Подтверждение",
                f"По этому резерву есть реализации (всего: {self._format_number(sold_sum)} шт/м2).\n\n"
                f"Удалить резерв и всю историю реализаций?"
            ):
                return
        else:
            if not self.ask_yes_no(
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
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)
    
    def on_realize(self):
        """Открыть окно реализации с предзаполнением из выбранного резерва"""
        res_id = self._get_selected_res_id()
        if res_id is None:
            self.show_warning("Внимание", "Выберите резерв для реализации")
            return
        
        record = reserved_products_repo.get_by_id(res_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        
        if len(record) >= 7:
            _, start_date, end_date, product, color, quantity, customer = record[:7]
        elif len(record) >= 6:
            _, start_date, end_date, product, color, quantity = record[:6]
        else:
            self.show_error("Ошибка", "Неверный формат записи")
            return
        
        # Проверяем, не реализован ли уже полностью
        sold_sum = reserved_products_repo.get_reserve_sold_sum(res_id)
        remaining = quantity - sold_sum
        
        if remaining <= 0:
            self.show_warning("Внимание", "Резерв уже реализован полностью")
            return
        
        from ui.windows.sales_window import SalesWindow
        
        SalesWindow(
            self.window,
            self._on_sales_closed,
            prefill_reserve_id=res_id,
            prefill_product=product,
            prefill_color=color,
            prefill_quantity=remaining
        )
    
    def _on_sales_closed(self):
        """Callback после закрытия окна реализации"""
        self.load_reservations()
    
    def _on_auto_refresh(self):
        """Автообновление данных при изменении БД другим компьютером"""
        try:
            self.load_reservations()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в ReservedProductsWindow: {e}")