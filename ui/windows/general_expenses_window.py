"""
Окно "Расходы общие" - учёт общих расходов
Оформление идентично окну "Производство продукции".
[ИЗМЕНЕНО] Все messagebox заменены на методы базового класса.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    suppliers_repo, materials_repo, payers_repo, payment_types_repo,
    purposes_repo, general_expenses_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class GeneralExpensesWindow(BaseToplevelWindow):
    """Окно учёта общих расходов"""
    def __init__(self, parent, on_exit_callback):
        self.supplier_list = [row[0] for row in suppliers_repo.get_all()]
        self.material_list = [row[0] for row in materials_repo.get_all()]
        self.payer_list = [row[0] for row in payers_repo.get_all()]
        self.payment_type_list = [row[0] for row in payment_types_repo.get_all()]
        self.purpose_list = [row[0] for row in purposes_repo.get_all()]
        self.editing_id = None
        super().__init__(parent, on_exit_callback, title="Расходы общие")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Расходы общие")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 4))
        
        self.add_field_label(left_inner, "Поставщик:")
        self.supplier_combo = AutocompleteCombobox(left_inner, values=self.supplier_list)
        self.supplier_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Материалы и услуги:")
        self.material_combo = AutocompleteCombobox(left_inner, values=self.material_list)
        self.material_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Количество:")
        self.quantity_entry = self._create_number_entry(left_inner)
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 3), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Цена:")
        self.price_entry = self._create_number_entry(left_inner)
        self.price_entry.pack(fill=tk.X, padx=10, pady=(0, 4), ipady=SIZES['field_ipady'])
        
        self.add_field_label(left_inner, "Плательщик:")
        self.payer_combo = AutocompleteCombobox(left_inner, values=self.payer_list)
        self.payer_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Вид оплаты:")
        self.payment_type_combo = AutocompleteCombobox(left_inner, values=self.payment_type_list)
        self.payment_type_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Назначение:")
        self.purpose_combo = AutocompleteCombobox(left_inner, values=self.purpose_list)
        self.purpose_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Комментарии:")
        self.comment_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.comment_entry.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=SIZES['field_ipady'])
        
        buttons_frame = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        buttons_frame.pack(fill=tk.X, padx=0, pady=(10, 5))
        
        self.save_btn = self.add_button(buttons_frame, "Сохранить", self.save_expense,
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
            right_frame, text="Журнал общих расходов",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('date', 'supplier', 'material', 'quantity', 'price', 'total',
                     'payer', 'payment_type', 'purpose', 'comment'),
            show='headings', yscrollcommand=scrollbar_y.set, selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('supplier', text='Поставщик', anchor='w')
        self.tree.heading('material', text='Материалы и услуги', anchor='w')
        self.tree.heading('quantity', text='Кол-во', anchor='w')
        self.tree.heading('price', text='Цена, руб', anchor='w')
        self.tree.heading('total', text='Сумма, руб', anchor='w')
        self.tree.heading('payer', text='Плательщик', anchor='w')
        self.tree.heading('payment_type', text='Вид оплаты', anchor='w')
        self.tree.heading('purpose', text='Назначение', anchor='w')
        self.tree.heading('comment', text='Комментарии', anchor='w')
        self.tree.column('date', width=80, anchor='w')
        self.tree.column('supplier', width=150, anchor='w')
        self.tree.column('material', width=180, anchor='w')
        self.tree.column('quantity', width=60, anchor='w')
        self.tree.column('price', width=80, anchor='w')
        self.tree.column('total', width=90, anchor='w')
        self.tree.column('payer', width=150, anchor='w')
        self.tree.column('payment_type', width=150, anchor='w')
        self.tree.column('purpose', width=150, anchor='w')
        self.tree.column('comment', width=230, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_expenses()
    
    def _create_number_entry(self, parent):
        entry = tk.Entry(parent, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left')
        entry.bind('<KeyRelease>', self._validate_number)
        return entry
    
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
    
    def load_expenses(self):
        selected_item = self.tree.selection()
        selected_id = None
        if selected_item:
            try:
                selected_id = int(selected_item[0])
            except (ValueError, IndexError):
                selected_id = None
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        records = general_expenses_repo.get_all()
        for row in records:
            (expense_id, date, supplier, material, quantity, price,
             payer, payment_type, purpose, comment) = row
            qty = quantity or 0
            prc = price or 0
            total = qty * prc
            self.tree.insert(
                '', 'end', iid=str(expense_id),
                values=(date, supplier or '—', material or '—',
                        self._format_number(quantity), self._format_number(price),
                        self._format_number(total), payer or '—',
                        payment_type or '—', purpose or '—', comment or '—')
            )
        
        if selected_id is not None:
            try:
                self.tree.selection_set(str(selected_id))
            except tk.TclError:
                pass
    
    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для редактирования")
            return
        expense_id = int(selected[0])
        record = general_expenses_repo.get_by_id(expense_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        (expense_id, date, supplier, material, quantity, price,
         payer, payment_type, purpose, comment) = record
        self.date_entry.set_date(date)
        self.supplier_combo.set(supplier or '')
        self.material_combo.set(material or '')
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, self._format_number(price))
        self.payer_combo.set(payer or '')
        self.payment_type_combo.set(payment_type or '')
        self.purpose_combo.set(purpose or '')
        self.comment_entry.delete(0, tk.END)
        self.comment_entry.insert(0, comment or '')
        self.editing_id = expense_id
        self.save_btn.config(text="Обновить")
        self.date_entry.entry.focus()
    
    def save_expense(self):
        date_str = self.date_entry.get_date()
        supplier = self.supplier_combo.get().strip()
        material = self.material_combo.get().strip()
        quantity = self.quantity_entry.get().strip()
        price = self.price_entry.get().strip()
        payer = self.payer_combo.get().strip()
        payment_type = self.payment_type_combo.get().strip()
        purpose = self.purpose_combo.get().strip()
        comment = self.comment_entry.get().strip()
        
        if not date_str:
            self.show_warning("Внимание", "Укажите дату")
            return
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
        except ValueError:
            self.show_warning("Внимание", "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        
        if self.editing_id:
            success, message = general_expenses_repo.update(
                self.editing_id, date_str, supplier, material,
                quantity, price, payer, payment_type, purpose, comment
            )
        else:
            success, message = general_expenses_repo.add(
                date_str, supplier, material, quantity, price,
                payer, payment_type, purpose, comment
            )
        
        if success:
            self._clear_fields()
            self.load_expenses()
        else:
            self.show_error("Ошибка", message)
    
    def _clear_fields(self):
        self.date_entry.clear()
        self.supplier_combo.clear()
        self.material_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.payer_combo.clear()
        self.payment_type_combo.clear()
        self.purpose_combo.clear()
        self.comment_entry.delete(0, tk.END)
        self.editing_id = None
        self.save_btn.config(text="Сохранить")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для удаления")
            return
        expense_id = int(selected[0])
        record = general_expenses_repo.get_by_id(expense_id)
        if not record:
            self.show_error("Ошибка", "Запись не найдена")
            return
        _, date, supplier, material, quantity, price, payer, payment_type, purpose, comment = record
        total = (quantity or 0) * (price or 0)
        if not self.ask_yes_no(
            "Подтверждение",
            f"Удалить запись о расходе?\n\n"
            f"Дата: {date}\n"
            f"Поставщик: {supplier or '—'}\n"
            f"Материал: {material or '—'}\n"
            f"Сумма: {self._format_number(total)} руб."
        ):
            return
        success, message = general_expenses_repo.delete(expense_id)
        if success:
            if self.editing_id == expense_id:
                self._clear_fields()
            self.load_expenses()
            self.show_info("Успех", message)
        else:
            self.show_error("Ошибка", message)