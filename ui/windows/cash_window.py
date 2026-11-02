"""
Окно "Касса" - учёт кассовых операций
Оформление идентично окну "Производство продукции".
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cash_repo
from ui.widgets.date_entry import DateEntry
from ui.base_window import BaseToplevelWindow


class CashWindow(BaseToplevelWindow):
    """Окно учёта кассовых операций"""
    
    def __init__(self, parent, on_exit_callback):
        self.editing_id = None
        super().__init__(parent, on_exit_callback, title="Касса")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Касса")
        content_frame = self.create_content_frame(self.window)
        
        # Левая панель
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 6))
        
        self.add_field_label(left_inner, "Приход, руб.:")
        self.income_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.income_entry.pack(fill=tk.X, padx=10, pady=(0, 6), ipady=SIZES['field_ipady'])
        self.income_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Расход, руб.:")
        self.expense_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.expense_entry.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=SIZES['field_ipady'])
        self.expense_entry.bind('<KeyRelease>', self._validate_number)
        
        # Кнопки
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_operation,
                                        color=COLORS['button_primary'])
        self.delete_btn = self.add_button(buttons_frame, "Удалить", self.delete_selected_cell,
                                          color='#e74c3c')
        self.delete_btn.bind('<Enter>', lambda e: self.delete_btn.config(bg='#c0392b'))
        self.delete_btn.bind('<Leave>', lambda e: self.delete_btn.config(bg='#e74c3c'))
        
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # Правая часть
        right_frame = self.create_right_panel(content_frame)
        
        tk.Label(
            right_frame, text="Журнал кассовых операций",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('date', 'income', 'expense'),
            show='headings',
            yscrollcommand=scrollbar_y.set,
            selectmode='browse'
        )
        
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('income', text='Приход, руб.', anchor='w')
        self.tree.heading('expense', text='Расход, руб.', anchor='w')
        
        self.tree.column('date', width=150, anchor='w')
        self.tree.column('income', width=200, anchor='w')
        self.tree.column('expense', width=200, anchor='w')
        
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        
        # Блок итогов
        self.summary_frame = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        self.summary_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Frame(self.summary_frame, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, pady=(0, 10)
        )
        
        self.balance_label = tk.Label(
            self.summary_frame, text="Остаток, руб.: 0",
            font=('Arial', 12, 'bold'), bg=COLORS['panel_bg'],
            fg=COLORS['title_text'], anchor='w'
        )
        self.balance_label.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.load_operations()
    
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
    
    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self._update_summary_for_item(selected[0])
    
    def _update_summary_for_item(self, item_id):
        values = self.tree.item(item_id, 'values')
        if not values:
            self._clear_summary()
            return
        
        date_str = values[0]
        
        if item_id.startswith('total_'):
            date_str = item_id[6:]
        elif item_id.startswith('turnover_'):
            date_str = item_id[9:]
        
        if not date_str or date_str in ('Итог', 'Оборот за день'):
            children = self.tree.get_children()
            idx = list(children).index(item_id)
            for i in range(idx - 1, -1, -1):
                prev_values = self.tree.item(children[i], 'values')
                if prev_values and prev_values[0] and prev_values[0] not in ('Итог', 'Оборот за день'):
                    date_str = prev_values[0]
                    break
        
        if not date_str or date_str in ('Итог', 'Оборот за день'):
            self._clear_summary()
            return
        
        balance = cash_repo.get_balance_up_to_date(date_str)
        self.balance_label.config(text=f"Остаток, руб.: {self._format_money(balance)}")
    
    def _clear_summary(self):
        self.balance_label.config(text="Остаток, руб.: 0")
    
    def _format_money(self, value):
        if value is None or value == '':
            return '0'
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:.2f}".rstrip('0').rstrip('.')
        except (ValueError, TypeError):
            return str(value)
    
    def _parse_money(self, s):
        if not s:
            return None
        try:
            return float(s.replace(',', '.'))
        except:
            return None
    
    def save_operation(self):
        date_str = self.date_entry.get_date()
        income_str = self.income_entry.get().strip()
        expense_str = self.expense_entry.get().strip()
        
        if not date_str:
            messagebox.showwarning("Внимание", "Укажите дату")
            return
        
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        
        if not income_str and not expense_str:
            messagebox.showwarning("Внимание", "Укажите приход или расход")
            return
        
        try:
            income = float(income_str.replace(',', '.')) if income_str else 0
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат прихода")
            return
        
        try:
            expense = float(expense_str.replace(',', '.')) if expense_str else 0
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат расхода")
            return
        
        success, message = cash_repo.add(date_str, income, expense)
        
        if success:
            self.income_entry.delete(0, tk.END)
            self.expense_entry.delete(0, tk.END)
            self.load_operations()
            self.income_entry.focus_set()
        else:
            messagebox.showerror("Ошибка", message)
    
    def load_operations(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        operations = cash_repo.get_all()
        
        grouped_by_date = {}
        for op_id, date, income, expense in operations:
            if date not in grouped_by_date:
                grouped_by_date[date] = []
            grouped_by_date[date].append((op_id, income, expense))
        
        def date_to_comparable(d):
            try:
                parts = d.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return int(f"{year}{month.zfill(2)}{day.zfill(2)}")
            except:
                pass
            return 0
        
        sorted_dates = sorted(grouped_by_date.keys(), 
                             key=lambda d: date_to_comparable(d), reverse=True)
        
        for date in sorted_dates:
            ops = grouped_by_date[date]
            
            incomes = []
            expenses = []
            
            for op_id, inc, exp in ops:
                if inc and inc > 0:
                    incomes.append({'id': op_id, 'value': inc})
                if exp and exp > 0:
                    expenses.append({'id': op_id, 'value': exp})
            
            num_rows = max(len(incomes), len(expenses))
            if num_rows == 0:
                continue
            
            for i in range(num_rows):
                date_display = date if i == 0 else ''
                
                inc_val = ''
                if i < len(incomes):
                    inc_val = self._format_money(incomes[i]['value'])
                
                exp_val = ''
                if i < len(expenses):
                    exp_val = self._format_money(expenses[i]['value'])
                
                row_iid = f"row__{date}__{i}"
                
                self.tree.insert(
                    '', 'end', iid=row_iid,
                    values=(date_display, inc_val, exp_val)
                )
            
            total_income = sum(item['value'] for item in incomes)
            total_expense = sum(item['value'] for item in expenses)
            
            self.tree.insert(
                '', 'end', iid=f"total_{date}",
                values=("Итог", self._format_money(total_income), 
                        self._format_money(total_expense))
            )
            
            turnover = total_income - total_expense
            self.tree.insert(
                '', 'end', iid=f"turnover_{date}",
                values=(f"Оборот за день: {self._format_money(turnover)} руб.", "", "")
            )
    
    def delete_selected_cell(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите ячейку для удаления")
            return
        
        item_id = selected[0]
        
        if item_id.startswith('total_') or item_id.startswith('turnover_'):
            messagebox.showwarning(
                "Внимание",
                "Выберите конкретное значение прихода или расхода для удаления"
            )
            return
        
        values = self.tree.item(item_id, 'values')
        if not values:
            return
        
        actual_date = self._get_date_from_group(item_id)
        if not actual_date:
            messagebox.showerror("Ошибка", "Не удалось определить дату записи")
            return
        
        income_val_str = values[1]
        expense_val_str = values[2]
        
        inc_float = self._parse_money(income_val_str)
        exp_float = self._parse_money(expense_val_str)
        
        has_income = inc_float is not None and inc_float != 0
        has_expense = exp_float is not None and exp_float != 0
        
        if not has_income and not has_expense:
            messagebox.showwarning("Внимание", "В выбранной строке нет значений для удаления")
            return
        
        target_type = None
        
        if has_income and has_expense:
            target_type = self._ask_what_to_delete(income_val_str, expense_val_str)
            if target_type is None:
                return
        elif has_income:
            target_type = 'income'
        elif has_expense:
            target_type = 'expense'
        
        all_ops = cash_repo.get_all()
        day_ops = [op for op in all_ops if op[1] == actual_date]
        
        target_op_id = None
        target_desc = ""
        
        if target_type == 'income':
            for op in day_ops:
                if op[2] and abs(op[2] - inc_float) < 0.01:
                    target_op_id = op[0]
                    target_desc = f"Приход: {income_val_str} руб."
                    break
        elif target_type == 'expense':
            for op in day_ops:
                if op[3] and abs(op[3] - exp_float) < 0.01:
                    target_op_id = op[0]
                    target_desc = f"Расход: {expense_val_str} руб."
                    break
        
        if not target_op_id:
            messagebox.showerror("Ошибка", "Не найдена запись для удаления")
            return
        
        if not messagebox.askyesno(
            "Подтверждение",
            f"Удалить значение?\n\nДата: {actual_date}\n{target_desc}"
        ):
            return
        
        success, message = cash_repo.clear_field(target_op_id, target_type)
        
        if success:
            self.load_operations()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)
    
    def _get_date_from_group(self, item_id):
        children = self.tree.get_children()
        idx = list(children).index(item_id)
        for i in range(idx, -1, -1):
            vals = self.tree.item(children[i], 'values')
            if vals and vals[0] and vals[0] not in ('Итог', 'Оборот за день'):
                return vals[0]
        return None
    
    def _ask_what_to_delete(self, income_val_str, expense_val_str):
        dialog = tk.Toplevel(self.window)
        dialog.title("Что удалить?")
        dialog.configure(bg=COLORS['panel_bg'])
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.grab_set()
        
        dialog_width = 400
        dialog_height = 260
        
        root_window = self.window.winfo_toplevel()
        root_window.update_idletasks()
        root_x = root_window.winfo_rootx()
        root_y = root_window.winfo_rooty()
        root_w = root_window.winfo_width()
        root_h = root_window.winfo_height()
        
        x = root_x + (root_w - dialog_width) // 2
        y = root_y + (root_h - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        result = {'choice': None}
        
        tk.Label(
            dialog, text="Что удалить?",
            font=FONTS['section_title'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(15, 10))
        
        tk.Frame(dialog, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 10)
        )
        
        info_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        def _add_info_row(label_text, value_text):
            row = tk.Frame(info_frame, bg=COLORS['panel_bg'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(
                row, text=f"{label_text}:",
                font=FONTS['field'], bg=COLORS['panel_bg'],
                fg=COLORS['work_area_text'], width=12, anchor='w'
            ).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(
                row, text=value_text,
                font=FONTS['field'], bg=COLORS['panel_bg'],
                fg=COLORS['title_text'], anchor='w'
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        _add_info_row("Приход", f"{income_val_str} руб.")
        _add_info_row("Расход", f"{expense_val_str} руб.")
        
        tk.Frame(dialog, height=1, bg=COLORS['work_area_text']).pack(
            fill=tk.X, padx=20, pady=10
        )
        
        tk.Label(
            dialog, text="Выберите, что нужно удалить:",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(anchor='w', padx=20, pady=(0, 10))
        
        def on_income():
            result['choice'] = 'income'
            dialog.grab_release()
            dialog.destroy()
        
        def on_expense():
            result['choice'] = 'expense'
            dialog.grab_release()
            dialog.destroy()
        
        def on_cancel():
            result['choice'] = None
            dialog.grab_release()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        income_btn = tk.Button(
            btn_frame, text="Приход", font=FONTS['menu'], command=on_income,
            bg=COLORS['button_primary'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        income_btn.pack(side=tk.LEFT, padx=(0, 10))
        income_btn.bind('<Enter>', lambda e: income_btn.config(bg=COLORS['button_primary_hover']))
        income_btn.bind('<Leave>', lambda e: income_btn.config(bg=COLORS['button_primary']))
        
        expense_btn = tk.Button(
            btn_frame, text="Расход", font=FONTS['menu'], command=on_expense,
            bg='#f39c12', fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        expense_btn.pack(side=tk.LEFT, padx=(0, 10))
        expense_btn.bind('<Enter>', lambda e: expense_btn.config(bg='#d68910'))
        expense_btn.bind('<Leave>', lambda e: expense_btn.config(bg='#f39c12'))
        
        cancel_btn = tk.Button(
            btn_frame, text="Отмена", font=FONTS['menu'], command=on_cancel,
            bg=COLORS['button_settings'], fg=COLORS['button_text'],
            relief=tk.FLAT, padx=15, pady=5, cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg=COLORS['button_settings_hover']))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg=COLORS['button_settings']))
        
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        self.window.wait_window(dialog)
        
        return result['choice']