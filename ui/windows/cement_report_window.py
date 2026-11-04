"""
Окно "Отчет по цементу" - отчет о движении цемента по силосам
Оформление идентично окну "Производство продукции".
[ИЗМЕНЕНО] 
- Используется grid() вместо pack() для равномерного распределения
- Каждая строка grid имеет weight=1 — гарантирует одинаковую высоту
- Treeview внутри каждого блока растягивается на всё доступное пространство
- Количество таблиц = количество силосов (даже без данных)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cement_silos_repo, cement_receipts_repo
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.widgets.silo_canvas import SiloCanvas
from ui.base_window import BaseToplevelWindow


class CementReportWindow(BaseToplevelWindow):
    """Окно отчета по цементу"""
    def __init__(self, parent, on_exit_callback):
        self.silo_list = [row[0] for row in cement_silos_repo.get_all()]
        super().__init__(parent, on_exit_callback, title="Отчет по цементу")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Отчет по цементу")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата (начало периода):")
        self.start_date_entry = DateEntry(left_inner)
        self.start_date_entry.pack(fill=tk.X, padx=10, pady=(10, 4))
        
        self.add_field_label(left_inner, "Дата (конец периода):")
        self.end_date_entry = DateEntry(left_inner)
        self.end_date_entry.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Силос цемента:")
        self.silo_combo = AutocompleteCombobox(
            left_inner, values=self.silo_list
        )
        self.silo_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.hint_label = tk.Label(
            left_inner,
            text="Пустое поле - отчет по всем силосам",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            anchor='w'
        )
        self.hint_label.pack(fill=tk.X, padx=10, pady=(0, 15))
        
        self.report_btn = self.add_button(left_inner, "Открыть отчет",
                                          self._open_report_placeholder,
                                          color=COLORS['button_primary'])
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ===== ПРАВАЯ ЧАСТЬ =====
        right_frame = self.create_right_panel(content_frame)
        
        # Визуализация силосов (фиксированная высота)
        silos_frame = tk.Frame(
            right_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        silos_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(
            silos_frame,
            text="Текущий уровень наполнения силосов",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        self.silos_canvas_container = tk.Frame(silos_frame, bg=COLORS['panel_bg'])
        self.silos_canvas_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        silos_data = cement_silos_repo.get_all()
        balances = cement_receipts_repo.get_current_balance_by_silo()
        self.silos_canvas = SiloCanvas(
            self.silos_canvas_container,
            silos_data,
            balances
        )
        self.silos_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Заголовок блока таблиц
        tk.Label(
            right_frame,
            text="Отчет по движению цемента",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        # [ИЗМЕНЕНО] Используем grid-контейнер для равномерного распределения
        self.tables_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        self.tables_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.load_report_data()
    
    def _open_report_placeholder(self):
        messagebox.showinfo(
            "Информация",
            "Функция формирования PDF-отчета по периоду находится в разработке."
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
    
    def load_report_data(self):
        """
        Загрузить данные отчета.
        [ИЗМЕНЕНО] Используется grid() для равномерного распределения высоты.
        Создаются таблицы для ВСЕХ силосов (даже без данных).
        """
        # Очищаем контейнер
        for widget in self.tables_container.winfo_children():
            widget.destroy()
        
        # Получаем все данные отчета
        report_data = cement_receipts_repo.get_cement_report()
        
        # Получаем список ВСЕХ силосов из справочника
        all_silos = cement_silos_repo.get_all()  # [(name, capacity), ...]
        
        if not all_silos:
            # Если силосов нет вообще
            no_data_label = tk.Label(
                self.tables_container,
                text="Силоса не настроены. Добавьте их в Настройках.",
                font=FONTS['menu'],
                bg=COLORS['panel_bg'],
                fg=COLORS['work_area_text']
            )
            no_data_label.pack(expand=True)
            return
        
        # Группируем данные по силосам
        data_by_silo = {}
        for row in report_data:
            date, silo, receipt, consumption, balance = row
            if silo not in data_by_silo:
                data_by_silo[silo] = []
            data_by_silo[silo].append(row)
        
        # [НОВОЕ] Настраиваем grid-контейнер для равномерного распределения
        # Одна колонка на всю ширину
        self.tables_container.grid_columnconfigure(0, weight=1)
        
        # Количество таблиц = количество силосов
        num_silos = len(all_silos)
        
        # Создаем таблицу для КАЖДОГО силоса
        for row_idx, (silo_name, capacity) in enumerate(all_silos):
            # [НОВОЕ] Настраиваем строку grid — weight=1 означает равномерное распределение
            self.tables_container.grid_rowconfigure(row_idx, weight=1)
            
            silo_data = data_by_silo.get(silo_name, [])
            self._create_silo_table(row_idx, silo_name, silo_data)
    
    def _create_silo_table(self, row_idx, silo_name, silo_data):
        """
        Создать таблицу отчета для одного силоса.
        [ИЗМЕНЕНО] Используется grid() с sticky='nsew' для растягивания на всё пространство.
        
        Args:
            row_idx: индекс строки в grid
            silo_name: название силоса
            silo_data: список данных для этого силоса
        """
        # [ИЗМЕНЕНО] Блок силоса размещается через grid с растягиванием
        silo_block = tk.Frame(
            self.tables_container,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=1
        )
        # [НОВОЕ] grid вместо pack — sticky='nsew' растягивает блок на всю ячейку
        silo_block.grid(
            row=row_idx, column=0,
            sticky='nsew',  # North, South, East, West — растягивание во все стороны
            padx=0, pady=1
        )
        
        # [НОВОЕ] Настраиваем внутренний grid блока силоса
        # Строка 0 — заголовок (фиксированная высота)
        # Строка 1 — таблица (растягивается)
        silo_block.grid_rowconfigure(0, weight=0)   # Заголовок — не растягивается
        silo_block.grid_rowconfigure(1, weight=1)   # Таблица — растягивается
        silo_block.grid_columnconfigure(0, weight=1)
        
        # Заголовок блока силоса
        header_frame = tk.Frame(silo_block, bg=COLORS['button_primary'])
        header_frame.grid(row=0, column=0, sticky='ew')
        
        tk.Label(
            header_frame,
            text=f"  {silo_name}",
            font=FONTS['menu'],
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            anchor='w'
        ).pack(fill=tk.X, padx=5, pady=3)
        
        # [НОВОЕ] Контейнер для Treeview — использует grid внутри блока
        tree_container = tk.Frame(silo_block, bg=COLORS['panel_bg'])
        tree_container.grid(row=1, column=0, sticky='nsew')
        
        # Настраиваем внутренний grid контейнера
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        
        tree = ttk.Treeview(
            tree_container,
            columns=('date', 'receipt', 'consumption', 'balance'),
            show='headings',
            selectmode='browse'
        )
        
        # [НОВОЕ] Treeview размещается через grid с привязкой к скроллбару
        tree.grid(row=0, column=0, sticky='nsew')
        tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.configure(command=tree.yview)
        
        tree.heading('date', text='Дата', anchor='w')
        tree.heading('receipt', text='Поступление', anchor='w')
        tree.heading('consumption', text='Расход', anchor='w')
        tree.heading('balance', text='Остаток', anchor='w')
        
        tree.column('date', width=100, anchor='w')
        tree.column('receipt', width=120, anchor='w')
        tree.column('consumption', width=120, anchor='w')
        tree.column('balance', width=120, anchor='w')
        
        # Заполняем данными
        if silo_data:
            for row in silo_data:
                date, silo, receipt, consumption, balance = row
                receipt_str = self._format_number(receipt) if receipt and receipt > 0 else ''
                consumption_str = self._format_number(consumption) if consumption and consumption > 0 else ''
                balance_str = self._format_number(balance)
                tree.insert(
                    '', 'end',
                    values=(date, receipt_str, consumption_str, balance_str)
                )
        else:
            # Если данных нет — показываем сообщение в таблице
            tree.insert(
                '', 'end',
                values=('—', 'Нет данных', 'Нет данных', '—')
            )