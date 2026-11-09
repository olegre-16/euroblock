"""
Окно "Касса" - учёт кассовых операций.

ЛОГИКА ОТОБРАЖЕНИЯ:
- Операции группируются по датам.
- Внутри каждого дня отдельно формируется список приходов и список расходов.
- Затем они выводятся построчно параллельно:
    1-й приход + 1-й расход
    2-й приход + 2-й расход
    ...
- После операций выводится:
    "ОБОРОТ ЗА ДЕНЬ: +X" (или -X, или 0)
    "ОСТАТОК: Y" (накопительный остаток на конец дня)
- Дни чередуются: белый / светло-жёлтый
- "ОСТАТОК ПО КАССЕ" закреплён внизу

[ИЗМЕНЕНО]
- После сохранения операции дата НЕ сбрасывается — остаётся в поле
- При открытии окна дата пустая
- Пользователь может изменить дату вручную
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cash_repo
from ui.widgets.date_entry import DateEntry
from ui.base_window import BaseToplevelWindow


class CashWindow(BaseToplevelWindow):
    """Окно учёта кассовых операций"""

    def __init__(self, parent, on_exit_callback):
        self.editing_id = None
        self._iid_to_cells = {}
        super().__init__(parent, on_exit_callback, title="Касса")

    # ======================================================================
    # ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ======================================================================

    def _build_ui(self):
        self.create_title_section(self.window, "Касса")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)

        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 6))
        
        # [НОВОЕ] Дата НЕ устанавливается автоматически при открытии окна
        # Пользователь вводит дату вручную, и она сохраняется после операций

        self.add_field_label(left_inner, "Приход, руб.:")
        self.income_entry = tk.Entry(
            left_inner,
            font=FONTS["field"],
            relief=tk.SOLID,
            bd=1,
            justify="left"
        )
        self.income_entry.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 6),
            ipady=SIZES["field_ipady"]
        )
        self.income_entry.bind("<KeyRelease>", self._validate_number)

        self.add_field_label(left_inner, "Расход, руб.:")
        self.expense_entry = tk.Entry(
            left_inner,
            font=FONTS["field"],
            relief=tk.SOLID,
            bd=1,
            justify="left"
        )
        self.expense_entry.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 8),
            ipady=SIZES["field_ipady"]
        )
        self.expense_entry.bind("<KeyRelease>", self._validate_number)

        buttons_frame = tk.Frame(left_inner, bg=COLORS["panel_bg"])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))

        self.save_btn = self.add_button(
            buttons_frame,
            "Сохранить",
            self.save_operation,
            color=COLORS["button_primary"]
        )
        self.save_btn.bind("<Enter>", lambda e: self._on_save_enter())
        self.save_btn.bind("<Leave>", lambda e: self._on_save_leave())

        self.edit_btn = self.add_button(
            buttons_frame,
            "Изменить",
            self.edit_selected,
            color="#f39c12"
        )

        self.delete_btn = self.add_button(
            buttons_frame,
            "Удалить",
            self.delete_selected_cell,
            color="#e74c3c"
        )

        self.exit_btn = self.add_button(
            left_inner,
            "Выход",
            self._on_close,
            color=COLORS["button_settings"],
            side=tk.BOTTOM
        )

        # Правая часть
        right_frame = self.create_right_panel(content_frame)

        tk.Label(
            right_frame,
            text="Журнал кассовых операций",
            font=FONTS["menu"],
            bg=COLORS["panel_bg"],
            fg=COLORS["title_text"]
        ).pack(pady=(10, 5), anchor="w", padx=10)

        tree_wrapper = tk.Frame(right_frame, bg=COLORS["panel_bg"])
        tree_wrapper.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        tree_container = tk.Frame(tree_wrapper, bg=COLORS["panel_bg"])
        tree_container.pack(fill=tk.BOTH, expand=True)

        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            tree_container,
            columns=("date", "income", "expense"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            selectmode="browse"
        )

        self.tree.heading("date", text="Дата", anchor="w")
        self.tree.heading("income", text="Приход, руб.", anchor="w")
        self.tree.heading("expense", text="Расход, руб.", anchor="w")

        self.tree.column("date", width=180, anchor="w")
        self.tree.column("income", width=150, anchor="w")
        self.tree.column("expense", width=150, anchor="w")

        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Теги чередования дней: белый / светло-жёлтый
        self.tree.tag_configure(
            "op_white",
            background="white",
            foreground=COLORS["title_text"]
        )
        self.tree.tag_configure(
            "turn_white",
            background="white",
            foreground="#2c3e50",
            font=FONTS["field"]
        )

        self.tree.tag_configure(
            "op_yellow",
            background="#fff9c4",
            foreground=COLORS["title_text"]
        )
        self.tree.tag_configure(
            "turn_yellow",
            background="#fff9c4",
            foreground="#2c3e50",
            font=FONTS["field"]
        )

        self.tree.bind("<Double-Button-1>", self._on_tree_double_click)

        # Закреплённый остаток по кассе
        self.total_frame = tk.Frame(
            tree_wrapper,
            bg="#d4edda",
            relief=tk.RAISED,
            bd=2
        )
        self.total_frame.pack(fill=tk.X, side=tk.BOTTOM)

        total_inner = tk.Frame(self.total_frame, bg="#d4edda")
        total_inner.pack(fill=tk.X, padx=5, pady=8)

        self.total_date_label = tk.Label(
            total_inner,
            text="ОСТАТОК ПО КАССЕ:",
            font=FONTS["menu"],
            bg="#d4edda",
            fg="#155724",
            anchor="w",
            width=20
        )
        self.total_date_label.pack(side=tk.LEFT, padx=(5, 10))

        self.total_income_label = tk.Label(
            total_inner,
            text="",
            font=FONTS["menu"],
            bg="#d4edda",
            fg="#155724",
            anchor="w",
            width=18
        )
        self.total_income_label.pack(side=tk.LEFT, padx=(10, 10))

        self.total_expense_label = tk.Label(
            total_inner,
            text="",
            font=FONTS["menu"],
            bg="#d4edda",
            fg="#155724",
            anchor="w",
            width=18
        )
        self.total_expense_label.pack(side=tk.LEFT, padx=(10, 0))

        self.load_operations()

    # ======================================================================
    # СЛУЖЕБНЫЕ МЕТОДЫ
    # ======================================================================

    def _validate_number(self, event=None):
        widget = event.widget
        value = widget.get()
        filtered = ""

        for char in value:
            if char.isdigit() or char in "-., ":
                filtered += char

        if filtered != value:
            widget.delete(0, tk.END)
            widget.insert(0, filtered)

    def _on_save_enter(self):
        if self.editing_id:
            self.save_btn.config(bg="#27ae60")
        else:
            self.save_btn.config(bg=COLORS["button_primary_hover"])

    def _on_save_leave(self):
        if self.editing_id:
            self.save_btn.config(bg="#27ae60")
        else:
            self.save_btn.config(bg=COLORS["button_primary"])

    def _format_money(self, value):
        """Форматирование денежной суммы"""
        if value is None or value == "":
            return ""

        try:
            num = float(value)

            if num == 0:
                return "0"

            if num.is_integer():
                return f"{int(num):,}".replace(",", " ")

            return f"{num:,.2f}".replace(",", " ")
        except (ValueError, TypeError):
            return str(value)

    def _format_turnover(self, value):
        """Форматирование оборота с плюсом/минусом"""
        if value > 0:
            return f"+{self._format_money(value)}"
        elif value < 0:
            return f"-{self._format_money(-value)}"
        else:
            return "0"

    def _parse_money(self, value_str):
        """Преобразование денежной строки в число"""
        if not value_str or str(value_str).strip() == "":
            return None

        try:
            cleaned = str(value_str).replace(" ", "").replace(",", ".")
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    def _date_to_sort_key(self, date_str):
        """ДД.ММ.ГГГГ -> YYYY-MM-DD для сортировки"""
        try:
            parts = date_str.split(".")
            if len(parts) == 3:
                day, month, year = parts
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except (ValueError, AttributeError):
            pass

        return "9999-99-99"

    # ======================================================================
    # ЛОГИКА ПОСТРОЕНИЯ СТРОК
    # ======================================================================

    def _build_display_rows(self, ops, date):
        """
        Построить строки отображения для одного дня.
        Приходы и расходы уплотняются независимо.
        """
        incomes = []
        expenses = []

        sorted_ops = sorted(ops, key=lambda x: x["id"])

        for op in sorted_ops:
            income = op.get("income") or 0
            expense = op.get("expense") or 0

            if income > 0:
                incomes.append({
                    "op_id": op["id"],
                    "amount": income,
                    "date": date
                })

            if expense > 0:
                expenses.append({
                    "op_id": op["id"],
                    "amount": expense,
                    "date": date
                })

        rows_count = max(len(incomes), len(expenses))
        display_rows = []

        for index in range(rows_count):
            income_item = incomes[index] if index < len(incomes) else None
            expense_item = expenses[index] if index < len(expenses) else None

            income_op_id = income_item["op_id"] if income_item else None
            expense_op_id = expense_item["op_id"] if expense_item else None

            income_amount = income_item["amount"] if income_item else 0
            expense_amount = expense_item["amount"] if expense_item else 0

            iid = f"cash_row_{date}_{index}_{income_op_id or 0}_{expense_op_id or 0}"

            display_rows.append({
                "iid": iid,
                "income": income_amount,
                "expense": expense_amount,
                "income_op_id": income_op_id,
                "expense_op_id": expense_op_id,
                "date": date
            })

        return display_rows

    # ======================================================================
    # ЗАГРУЗКА ОПЕРАЦИЙ
    # ======================================================================

    def load_operations(self):
        """Загрузить операции в таблицу."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._iid_to_cells = {}

        operations = cash_repo.get_all()

        total_income = 0
        total_expense = 0

        if not operations:
            self._update_total_footer(0, 0)
            return

        # Группировка по дате
        groups = {}

        for op in operations:
            if len(op) < 4:
                continue

            op_id, date, income, expense = op[:4]

            if date not in groups:
                groups[date] = []

            groups[date].append({
                "id": op_id,
                "date": date,
                "income": income or 0,
                "expense": expense or 0
            })

        # Сортируем даты от старых к новым (для расчёта накопительного остатка)
        sorted_dates_asc = sorted(
            groups.keys(),
            key=self._date_to_sort_key,
            reverse=False
        )

        # Считаем оборот и накопительный остаток для каждого дня
        days_data = []
        cumulative_balance = 0

        for date in sorted_dates_asc:
            ops = groups[date]

            day_income = sum((op["income"] or 0) for op in ops)
            day_expense = sum((op["expense"] or 0) for op in ops)
            turnover = day_income - day_expense
            cumulative_balance += turnover

            days_data.append({
                "date": date,
                "ops": ops,
                "day_income": day_income,
                "day_expense": day_expense,
                "turnover": turnover,
                "balance": cumulative_balance
            })

            total_income += day_income
            total_expense += day_expense

        # Разворачиваем список — выводим от новых к старым
        days_data_reversed = list(reversed(days_data))

        for day_index, day in enumerate(days_data_reversed):
            date = day["date"]
            ops = day["ops"]
            turnover = day["turnover"]
            balance = day["balance"]

            # Чередование цветов: белый / светло-жёлтый
            if day_index % 2 == 0:
                op_tag = "op_white"
                turn_tag = "turn_white"
            else:
                op_tag = "op_yellow"
                turn_tag = "turn_yellow"

            # Выводим строки операций
            display_rows = self._build_display_rows(ops, date)

            for row_index, row in enumerate(display_rows):
                iid = row["iid"]

                self.tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(
                        date if row_index == 0 else "",
                        self._format_money(row["income"]) if row["income"] else "",
                        self._format_money(row["expense"]) if row["expense"] else ""
                    ),
                    tags=(op_tag,)
                )

                self._iid_to_cells[iid] = {
                    "income_op_id": row["income_op_id"],
                    "expense_op_id": row["expense_op_id"],
                    "income_amount": row["income"],
                    "expense_amount": row["expense"],
                    "date": date,
                    "is_operation": True
                }

            # Строка "ОБОРОТ ЗА ДЕНЬ: +X"
            turnover_text = f"ОБОРОТ ЗА ДЕНЬ: {self._format_turnover(turnover)}"
            turnover_iid = f"turnover_{date}"

            self.tree.insert(
                "",
                "end",
                iid=turnover_iid,
                values=(turnover_text, "", ""),
                tags=(turn_tag,)
            )

            # Строка "ОСТАТОК: Y" (большие буквы, тот же цвет, что и день)
            balance_text = f"ОСТАТОК: {self._format_money(balance)}"
            balance_iid = f"balance_{date}"

            self.tree.insert(
                "",
                "end",
                iid=balance_iid,
                values=(balance_text, "", ""),
                tags=(turn_tag,)
            )

        # Обновляем закреплённый общий итог
        self._update_total_footer(total_income, total_expense)

    def _update_total_footer(self, total_income, total_expense):
        """Обновить закреплённый остаток по кассе"""
        balance = total_income - total_expense

        if balance > 0:
            self.total_income_label.config(text=self._format_money(balance))
            self.total_expense_label.config(text="")
        elif balance < 0:
            self.total_income_label.config(text="")
            self.total_expense_label.config(text=self._format_money(-balance))
        else:
            self.total_income_label.config(text="0")
            self.total_expense_label.config(text="")

    # ======================================================================
    # СОХРАНЕНИЕ / РЕДАКТИРОВАНИЕ
    # ======================================================================

    def save_operation(self):
        date_str = self.date_entry.get_date()
        income_str = self.income_entry.get().strip()
        expense_str = self.expense_entry.get().strip()

        if not date_str:
            self.show_warning("Внимание", "Укажите дату")
            return

        try:
            datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            self.show_warning("Внимание", "Неверный формат даты")
            return

        if not income_str and not expense_str:
            self.show_warning("Внимание", "Укажите приход или расход")
            return

        income = self._parse_money(income_str) if income_str else 0
        expense = self._parse_money(expense_str) if expense_str else 0

        if income is None or expense is None:
            self.show_warning("Внимание", "Неверный формат числа")
            return

        if self.editing_id:
            success, message = cash_repo.update(
                self.editing_id,
                date_str,
                income,
                expense
            )
        else:
            success, message = cash_repo.add(
                date_str,
                income,
                expense
            )

        if success:
            # [ИЗМЕНЕНО] После сохранения очищаем только поля прихода/расхода,
            # но СОХРАНЯЕМ дату для удобства ввода нескольких операций за один день
            self._clear_fields(keep_date=True)
            self.load_operations()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)

    # [ИЗМЕНЕНО] Метод очистки полей с параметром keep_date
    def _clear_fields(self, keep_date=False):
        """
        Очистить поля формы.
        
        Args:
            keep_date: если True — дата остаётся в поле (для удобства
                       ввода нескольких операций за один день).
                       Если False — очищаются все поля, включая дату.
        """
        # Очищаем дату только если keep_date=False
        if not keep_date:
            self.date_entry.clear()
        
        # Всегда очищаем поля прихода и расхода
        self.income_entry.delete(0, tk.END)
        self.expense_entry.delete(0, tk.END)
        
        # Сбрасываем режим редактирования
        self.editing_id = None
        self.save_btn.config(text="Сохранить")
        
        # [НОВОЕ] Возвращаем фокус на поле прихода для быстрого ввода
        self.income_entry.focus_set()

    def _on_tree_double_click(self, event):
        """Двойной клик по строке — редактирование"""
        selected = self.tree.selection()

        if not selected:
            return

        item_id = selected[0]

        # Игнорируем служебные строки
        if item_id.startswith("turnover_") or item_id.startswith("balance_"):
            return

        cell = self._iid_to_cells.get(item_id)

        if not cell:
            return

        column = self.tree.identify_column(event.x)

        if column == "#3" and cell.get("expense_op_id"):
            self._load_operation_to_form(cell["expense_op_id"])
        elif cell.get("income_op_id"):
            self._load_operation_to_form(cell["income_op_id"])
        elif cell.get("expense_op_id"):
            self._load_operation_to_form(cell["expense_op_id"])

    def _load_operation_to_form(self, op_id):
        """Загрузить операцию в форму для редактирования"""
        record = cash_repo.get_by_id(op_id)

        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return

        _, date, income, expense = record[:4]

        # [ИЗМЕНЕНО] При редактировании дата тоже устанавливается
        self.date_entry.set_date(date)

        self.income_entry.delete(0, tk.END)
        if income:
            self.income_entry.insert(0, self._format_money(income))

        self.expense_entry.delete(0, tk.END)
        if expense:
            self.expense_entry.insert(0, self._format_money(expense))

        self.editing_id = op_id
        self.save_btn.config(text="Обновить")

    def edit_selected(self):
        selected = self.tree.selection()

        if not selected:
            self.show_warning("Внимание", "Выберите запись для редактирования")
            return

        item_id = selected[0]

        if item_id.startswith("turnover_") or item_id.startswith("balance_"):
            self.show_warning(
                "Внимание",
                "Выберите конкретную операцию для редактирования"
            )
            return

        cell = self._iid_to_cells.get(item_id)

        if not cell:
            return

        if cell.get("income_op_id"):
            self._load_operation_to_form(cell["income_op_id"])
        elif cell.get("expense_op_id"):
            self._load_operation_to_form(cell["expense_op_id"])

    # ======================================================================
    # УДАЛЕНИЕ
    # ======================================================================

    def delete_selected_cell(self):
        """
        Удаление прихода или расхода из выбранной строки.
        После удаления таблица перестраивается,
        значения автоматически подтягиваются вверх.
        
        [ИЗМЕНЕНО] После удаления дата сохраняется в поле формы.
        """
        selected = self.tree.selection()

        if not selected:
            self.show_warning("Внимание", "Выберите ячейку для удаления")
            return

        item_id = selected[0]

        if item_id.startswith("turnover_") or item_id.startswith("balance_"):
            self.show_warning(
                "Внимание",
                "Выберите конкретное значение прихода или расхода для удаления"
            )
            return

        cell = self._iid_to_cells.get(item_id)

        if not cell:
            return

        income_op_id = cell.get("income_op_id")
        expense_op_id = cell.get("expense_op_id")

        income_amount = cell.get("income_amount") or 0
        expense_amount = cell.get("expense_amount") or 0
        date = cell.get("date")

        has_income = income_op_id is not None and income_amount > 0
        has_expense = expense_op_id is not None and expense_amount > 0

        if not has_income and not has_expense:
            self.show_warning("Внимание", "В выбранной строке нет значений для удаления")
            return

        if has_income and has_expense:
            target_type = self._ask_what_to_delete(
                self._format_money(income_amount),
                self._format_money(expense_amount)
            )

            if target_type is None:
                return
        elif has_income:
            target_type = "income"
        else:
            target_type = "expense"

        if target_type == "income":
            target_op_id = income_op_id
            target_amount = income_amount
            target_desc = f"Приход: {self._format_money(target_amount)} руб."
        else:
            target_op_id = expense_op_id
            target_amount = expense_amount
            target_desc = f"Расход: {self._format_money(target_amount)} руб."

        if not self.ask_yes_no(
            "Подтверждение",
            f"Удалить значение?\n\nДата: {date}\n{target_desc}"
        ):
            return

        success, message = cash_repo.clear_field(target_op_id, target_type)

        if success:
            # [ИЗМЕНЕНО] После удаления очищаем только поля прихода/расхода,
            # дата остаётся для удобства
            self._clear_fields(keep_date=True)
            self.load_operations()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)

    def _ask_what_to_delete(self, income_str, expense_str):
        """Диалог выбора: приход или расход"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Что удалить?")
        dialog.configure(bg=COLORS["panel_bg"])
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()

        dialog_width = 400
        dialog_height = 250

        root_x = self.window.winfo_rootx()
        root_y = self.window.winfo_rooty()
        root_w = self.window.winfo_width()
        root_h = self.window.winfo_height()

        x = root_x + (root_w - dialog_width) // 2
        y = root_y + (root_h - dialog_height) // 2

        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        tk.Label(
            dialog,
            text="В строке есть и приход, и расход.\nЧто удалить?",
            font=FONTS["menu"],
            bg=COLORS["panel_bg"],
            fg=COLORS["title_text"],
            justify="center"
        ).pack(pady=(20, 15))

        tk.Frame(
            dialog,
            height=2,
            bg=COLORS["button_primary"]
        ).pack(fill=tk.X, padx=20, pady=(0, 15))

        result = {"choice": None}

        def on_income():
            result["choice"] = "income"
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def on_expense():
            result["choice"] = "expense"
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def on_cancel():
            result["choice"] = None
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS["panel_bg"])
        btn_frame.pack(fill=tk.X, padx=30, pady=(0, 10))

        income_btn = tk.Button(
            btn_frame,
            text=f"Приход: {income_str.strip()} руб.",
            font=FONTS["menu"],
            command=on_income,
            bg="#27ae60",
            fg=COLORS["button_text"],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        income_btn.pack(fill=tk.X, pady=(0, 10))
        income_btn.bind("<Enter>", lambda e: income_btn.config(bg="#229954"))
        income_btn.bind("<Leave>", lambda e: income_btn.config(bg="#27ae60"))

        expense_btn = tk.Button(
            btn_frame,
            text=f"Расход: {expense_str.strip()} руб.",
            font=FONTS["menu"],
            command=on_expense,
            bg="#e74c3c",
            fg=COLORS["button_text"],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        expense_btn.pack(fill=tk.X, pady=(0, 10))
        expense_btn.bind("<Enter>", lambda e: expense_btn.config(bg="#c0392b"))
        expense_btn.bind("<Leave>", lambda e: expense_btn.config(bg="#e74c3c"))

        cancel_btn = tk.Button(
            btn_frame,
            text="Отмена",
            font=FONTS["menu"],
            command=on_cancel,
            bg=COLORS["button_settings"],
            fg=COLORS["button_text"],
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        )
        cancel_btn.pack(fill=tk.X)
        cancel_btn.bind(
            "<Enter>",
            lambda e: cancel_btn.config(bg=COLORS["button_settings_hover"])
        )
        cancel_btn.bind(
            "<Leave>",
            lambda e: cancel_btn.config(bg=COLORS["button_settings"])
        )

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.bind("<Escape>", lambda e: on_cancel())

        self.window.wait_window(dialog)

        return result["choice"]

    # ======================================================================
    # АВТООБНОВЛЕНИЕ
    # ======================================================================

    def _on_auto_refresh(self):
        """Автообновление данных при изменении БД другим компьютером"""
        try:
            self.load_operations()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в CashWindow: {e}")