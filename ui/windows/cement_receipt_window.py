"""
Окно "Поступление цемента" - учёт поступления цемента в силосы
Оформление идентично окну "Производство продукции".
[ИЗМЕНЕНО]
- Поставщик теперь список с автодополнением (AutocompleteCombobox)
- Под полем "Поставщик" добавлена подсказка: "Пустое поле — корректировка"
- Если поле "Поставщик" пустое → запись считается корректировкой
- Корректировки в таблице выделяются светло-жёлтым цветом
- Все messagebox заменены на методы базового класса (предотвращает сворачивание)
- После операций окно гарантированно остаётся открытым
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cement_silos_repo, cement_receipts_repo, suppliers_repo
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.widgets.silo_canvas import SiloCanvas
from ui.base_window import BaseToplevelWindow


class CementReceiptWindow(BaseToplevelWindow):
    """Окно поступления цемента"""
    def __init__(self, parent, on_exit_callback):
        self.silo_list = [row[0] for row in cement_silos_repo.get_all()]
        # Список поставщиков из справочника
        self.supplier_list = [row[0] for row in suppliers_repo.get_all()]
        self.editing_id = None
        super().__init__(parent, on_exit_callback, title="Поступление цемента")
    
    def _build_ui(self):
        """Построение интерфейса окна"""
        self.create_title_section(self.window, "Поступление цемента")
        content_frame = self.create_content_frame(self.window)
        
        # ===== ЛЕВАЯ ПАНЕЛЬ С ПРОКРУТКОЙ =====
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
        
        # Поставщик — список с автодополнением
        self.add_field_label(left_inner, "Поставщик:")
        self.supplier_combo = AutocompleteCombobox(left_inner, values=self.supplier_list)
        self.supplier_combo.pack(fill=tk.X, padx=10, pady=(0, 2))
        
        # [НОВОЕ] Подсказка под полем "Поставщик"
        self.supplier_hint = tk.Label(
            left_inner,
            text="Пустое поле — корректировка",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            anchor='w'
        )
        self.supplier_hint.pack(fill=tk.X, padx=10, pady=(0, 8))
        
        # ===== КНОПКИ =====
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
        
        tk.Label(
            right_frame, text="Журнал поступлений цемента",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('date', 'silo', 'quantity', 'supplier'),
            show='headings', yscrollcommand=scrollbar_y.set, selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('silo', text='Силос', anchor='w')
        self.tree.heading('quantity', text='Количество, кг', anchor='w')
        self.tree.heading('supplier', text='Поставщик', anchor='w')
        self.tree.column('date', width=100, anchor='w')
        self.tree.column('silo', width=150, anchor='w')
        self.tree.column('quantity', width=120, anchor='w')
        self.tree.column('supplier', width=200, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # [НОВОЕ] Настраиваем тег для корректировок — светло-жёлтый фон
        self.tree.tag_configure('correction', background='#fff9c4')
        
        self.load_receipts()
    
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
    
    def load_receipts(self):
        """
        Загрузить данные в таблицу.
        [ИЗМЕНЕНО] Корректировки выделяются светло-жёлтым цветом.
        """
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        receipts = cement_receipts_repo.get_all()
        for row in receipts:
            receipt_id = row[0]
            date = row[1]
            silo = row[2]
            quantity = row[3]
            supplier = row[4] if len(row) > 4 else ''
            is_correction = row[5] if len(row) > 5 else 0
            
            # [НОВОЕ] Определяем отображение поставщика и тег
            if is_correction == 1:
                supplier_display = 'Корректировка'
                tags = ('correction',)
            else:
                supplier_display = supplier or '—'
                tags = ()
            
            self.tree.insert(
                '', 'end', iid=str(receipt_id),
                values=(date, silo, self._format_number(quantity), supplier_display),
                tags=tags
            )
        
        try:
            self.tree.update()
            self.window.update_idletasks()
        except tk.TclError:
            pass
        
        self._update_silos_visualization()
    
    def _update_silos_visualization(self):
        """Обновить визуализацию силосов"""
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
        """
        Сохранить новую запись.
        [ИЗМЕНЕНО] Если поле "Поставщик" пустое — запись считается корректировкой.
        """
        date_str = self.date_entry.get_date()
        silo = self.silo_combo.get().strip()
        quantity_str = self.quantity_entry.get().strip()
        supplier = self.supplier_combo.get().strip()
        
        if not date_str:
            self.show_warning("Внимание", "Укажите дату")
            return
        if not silo:
            self.show_warning("Внимание", "Выберите силос")
            return
        if not quantity_str:
            self.show_warning("Внимание", "Укажите количество")
            return
        
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
            quantity = float(quantity_str.replace(',', '.'))
        except ValueError:
            self.show_warning("Внимание", "Неверный формат данных")
            return
        
        # [НОВОЕ] Определяем, является ли запись корректировкой
        is_correction = (supplier == '')
        
        if self.editing_id:
            success, message = cement_receipts_repo.update(
                self.editing_id, date_str, silo, quantity, supplier, is_correction
            )
        else:
            success, message = cement_receipts_repo.add(
                date_str, silo, quantity, supplier, is_correction
            )
        
        if success:
            self._clear_fields()
            self.load_receipts()
            self.show_info("Успех", message)
            self._restore_window_state()
        else:
            self.show_error("Ошибка", message)
            self._restore_window_state()
    
    def _clear_fields(self):
        """Очистить все поля"""
        self.date_entry.clear()
        self.silo_combo.clear()
        self.quantity_entry.delete(0, tk.END)
        self.supplier_combo.clear()
        self.editing_id = None
        self.save_btn.config(text="Сохранить")
    
    def edit_selected(self):
        """
        Загрузить данные для редактирования.
        [ИЗМЕНЕНО] Для корректировок поле поставщика остаётся пустым.
        """
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись")
            return
        receipt_id = int(selected[0])
        receipt = cement_receipts_repo.get_by_id(receipt_id)
        if not receipt:
            self.show_error("Ошибка", "Запись не найдена")
            return
        date = receipt[1]
        silo = receipt[2]
        quantity = receipt[3]
        supplier = receipt[4] if len(receipt) > 4 else ''
        is_correction = receipt[5] if len(receipt) > 5 else 0
        
        self.date_entry.set_date(date)
        self.silo_combo.set(silo)
        self.quantity_entry.delete(0, tk.END)
        self.quantity_entry.insert(0, self._format_number(quantity))
        
        # [НОВОЕ] Для корректировок поле поставщика оставляем пустым
        if is_correction == 1:
            self.supplier_combo.clear()
        else:
            self.supplier_combo.set(supplier or '')
        
        self.editing_id = receipt_id
        self.save_btn.config(text="Обновить")
        self._restore_window_state()
    
    def delete_selected(self):
        """Удалить выбранную запись"""
        selected = self.tree.selection()
        if not selected:
            self.show_warning("Внимание", "Выберите запись для удаления")
            return
        
        receipt_id = int(selected[0])
        
        receipt = cement_receipts_repo.get_by_id(receipt_id)
        if not receipt:
            self.show_error("Ошибка", "Запись не найдена")
            return
        
        date = receipt[1]
        silo = receipt[2]
        quantity = receipt[3]
        supplier = receipt[4] if len(receipt) > 4 else ''
        is_correction = receipt[5] if len(receipt) > 5 else 0
        
        # Формируем текст подтверждения
        record_type = "корректировку" if is_correction == 1 else "запись о поступлении"
        confirm_text = (
            f"Удалить {record_type}?\n\n"
            f"Дата: {date}\n"
            f"Силос: {silo}\n"
            f"Количество: {self._format_number(quantity)} кг\n"
            f"Поставщик: {supplier or '(корректировка)'}"
        )
        
        if not self.ask_yes_no("Подтверждение", confirm_text):
            return
        
        success, message = cement_receipts_repo.delete(receipt_id)
        
        if success:
            if self.editing_id == receipt_id:
                self._clear_fields()
            self.load_receipts()
            self.show_info("Успех", message)
            self._restore_window_state()
        else:
            self.show_error("Ошибка", message)
            self._restore_window_state()
            
    def _on_auto_refresh(self):
        """
        Автообновление данных при изменении БД другим компьютером.
        Вызывается таймером из BaseToplevelWindow каждые 3 секунды.
        """
        try:
            self.load_receipts()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в CementReceiptWindow: {e}")