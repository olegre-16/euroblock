"""
Окно "Поступление цемента" - учёт поступления цемента в силосы
[ИЗМЕНЕНО] Применена пагинация к журналу поступлений.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cement_silos_repo, cement_receipts_repo
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.widgets.silo_canvas import SiloCanvas
from ui.widgets.paginated_treeview import PaginatedTreeview
from ui.base_window import BaseToplevelWindow


class CementReceiptWindow(BaseToplevelWindow):
    """Окно поступления цемента"""
    def __init__(self, parent, on_exit_callback):
        self.silo_list = [row[0] for row in cement_silos_repo.get_all()]
        self.editing_id = None
        super().__init__(parent, on_exit_callback, title="Поступление цемента")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Поступление цемента")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame, width=350)
        
        self.add_field_label(left_inner, "Дата:")
        self.date_entry = DateEntry(left_inner)
        self.date_entry.pack(fill=tk.X, padx=10, pady=(10, 6))
        
        self.add_field_label(left_inner, "Силос цемента:")
        self.silo_combo = AutocompleteCombobox(left_inner, values=self.silo_list)
        self.silo_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.add_field_label(left_inner, "Количество, кг:")
        self.quantity_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.quantity_entry.pack(fill=tk.X, padx=10, pady=(0, 6), ipady=SIZES['field_ipady'])
        self.quantity_entry.bind('<KeyRelease>', self._validate_number)
        
        self.add_field_label(left_inner, "Поставщик:")
        self.supplier_entry = tk.Entry(
            left_inner, font=FONTS['field'], relief=tk.SOLID, bd=1, justify='left'
        )
        self.supplier_entry.pack(fill=tk.X, padx=10, pady=(0, 8), ipady=SIZES['field_ipady'])
        
        self.save_btn = self.add_button(left_inner, "Сохранить", self.save_receipt,
                                        color=COLORS['button_primary'])
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        self.edit_btn = self.add_button(left_inner, "Изменить", self.edit_selected,
                                        color='#f39c12')
        self.delete_btn = self.add_button(left_inner, "Удалить", self.delete_selected,
                                          color='#e74c3c')
        
        spacer = tk.Frame(left_inner, bg=COLORS['panel_bg'])
        spacer.pack(fill=tk.BOTH, expand=True)
        
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ===== ПРАВАЯ ЧАСТЬ =====
        right_frame = self.create_right_panel(content_frame)
        
        # Визуализация силосов
        silos_frame = tk.Frame(
            right_frame, bg=COLORS['panel_bg'],
            relief=tk.RAISED, bd=SIZES['panel_border']
        )
        silos_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(
            silos_frame, text="Текущий уровень наполнения силосов",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        self.silos_canvas_container = tk.Frame(silos_frame, bg=COLORS['panel_bg'])
        self.silos_canvas_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        silos_data = cement_silos_repo.get_all()
        balances = cement_receipts_repo.get_current_balance_by_silo()
        self.silos_canvas = SiloCanvas(self.silos_canvas_container, silos_data, balances)
        self.silos_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Таблица поступлений с пагинацией
        tk.Label(
            right_frame, text="Журнал поступлений цемента",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        self.paginated_tree = PaginatedTreeview(
            right_frame,
            columns=('date', 'silo', 'quantity', 'supplier'),
            headings={
                'date': 'Дата', 'silo': 'Силос',
                'quantity': 'Количество, кг', 'supplier': 'Поставщик'
            },
            column_widths={'date': 100, 'silo': 150, 'quantity': 120, 'supplier': 200},
            page_size=100,
            load_callback=self._load_receipts_page
        )
        self.paginated_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.paginated_tree.load_page(0)
    
    def _load_receipts_page(self, page, page_size):
        """Callback для загрузки страницы поступлений"""
        rows, total = cement_receipts_repo.get_all_paged(page, page_size)
        formatted_rows = []
        for row in rows:
            receipt_id = row[0]
            date = row[1]
            silo = row[2]
            quantity = row[3]
            supplier = row[4] if len(row) > 4 else ''
            formatted_rows.append((
                date, silo, self._format_number(quantity), supplier or '—'
            ))
        return formatted_rows, total
    
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
    
    def _update_silos_visualization(self):
        try:
            if hasattr(self, 'silos_canvas'):
                self.silos_canvas.destroy()
            silos_data = cement_silos_repo.get_all()
            balances = cement_receipts_repo.get_current_balance_by_silo()
            self.silos_canvas = SiloCanvas(self.silos_canvas_container, silos_data, balances)
            self.silos_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        except Exception as e:
            print(f"Ошибка обновления визуализации силосов: {e}")
    
    def save_receipt(self):
        date_str = self.date_entry.get_date()
        silo = self.silo_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        supplier = self.supplier_entry.get().strip()
        
        if not date_str:
            messagebox.showwarning("Внимание", "Укажите дату")
            return
        if not silo:
            messagebox.showwarning("Внимание", "Выберите силос")
            return
        if not quantity_str:
            messagebox.showwarning("Внимание", "Укажите количество")
            return
        
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
            quantity = float(quantity_str.replace(',', '.'))
        except ValueError:
            messagebox.showwarning("Внимание", "Неверный формат данных")
            return
        
        if self.editing_id:
            success, message = cement_receipts_repo.update(
                self.editing_id, date_str, silo, quantity, supplier
            )
        else:
            success, message = cement_receipts_repo.add(
                date_str, silo, quantity, supplier
            )
        
        if success:
            self._clear_fields()
            self.paginated_tree.refresh()
            self._update_silos_visualization()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)
    
    def _clear_fields(self):
        self.date_entry.clear()
        self.silo_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.supplier_entry.delete(0, tk.END)
        self.editing_id = None
        self.save_btn.config(text="Сохранить")
    
    def edit_selected(self):
        selected_iid = self.paginated_tree.get_selected_iid()
        if not selected_iid:
            messagebox.showwarning("Внимание", "Выберите запись")
            return
        
        receipt_id = int(selected_iid)
        receipt = cement_receipts_repo.get_by_id(receipt_id)
        if not receipt:
            messagebox.showerror("Ошибка", "Запись не найдена")
            return
        
        date = receipt[1]
        silo = receipt[2]
        quantity = receipt[3]
        supplier = receipt[4] if len(receipt) > 4 else ''
        
        self.date_entry.set_date(date)
        self.silo_combo.set(silo)
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        self.supplier_entry.delete(0, tk.END)
        self.supplier_entry.insert(0, supplier or '')
        self.editing_id = receipt_id
        self.save_btn.config(text="Обновить")
    
    def delete_selected(self):
        selected_iid = self.paginated_tree.get_selected_iid()
        if not selected_iid:
            messagebox.showwarning("Внимание", "Выберите запись")
            return
        
        receipt_id = int(selected_iid)
        if not messagebox.askyesno("Подтверждение", "Удалить запись?"):
            return
        
        success, message = cement_receipts_repo.delete(receipt_id)
        if success:
            if self.editing_id == receipt_id:
                self._clear_fields()
            self.paginated_tree.refresh()
            self._update_silos_visualization()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)