"""
Виджет Treeview с пагинацией.
Отображает данные постранично, не загружая всё в память.
Поддерживает навигацию: Первая, Предыдущая, Следующая, Последняя страница.
"""
import tkinter as tk
from tkinter import ttk
from config.settings import COLORS, FONTS, SIZES


class PaginatedTreeview(tk.Frame):
    """
    Treeview с пагинацией.
    
    Использование:
        tree = PaginatedTreeview(
            parent,
            columns=('date', 'name', 'value'),
            headings={'date': 'Дата', 'name': 'Имя', 'value': 'Значение'},
            column_widths={'date': 100, 'name': 200, 'value': 100},
            page_size=100,
            load_callback=my_load_function
        )
        tree.pack(fill=tk.BOTH, expand=True)
        tree.load_page()  # Загрузить первую страницу
    
    load_callback(page, page_size) -> (rows, total_count)
        Должна вернуть список строк и общее количество.
    """
    
    def __init__(self, parent, columns, headings, column_widths=None,
                 column_anchors=None, page_size=100, load_callback=None, **kwargs):
        super().__init__(parent, bg=COLORS['panel_bg'], **kwargs)
        
        self.columns = columns
        self.headings = headings
        self.column_widths = column_widths or {}
        self.column_anchors = column_anchors or {}
        self.page_size = page_size
        self.load_callback = load_callback
        
        self.current_page = 0
        self.total_count = 0
        self.total_pages = 0
        self.current_data = []
        
        self._build_ui()
    
    def _build_ui(self):
        """Построить интерфейс: Treeview + панель пагинации"""
        # ===== Контейнер для Treeview со скроллбаром =====
        tree_container = tk.Frame(self, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        
        self.scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=self.columns,
            show='headings',
            yscrollcommand=self.scrollbar_y.set,
            selectmode='browse'
        )
        
        for col in self.columns:
            heading_text = self.headings.get(col, col)
            anchor = self.column_anchors.get(col, 'w')
            width = self.column_widths.get(col, 100)
            self.tree.heading(col, text=heading_text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor)
        
        self.scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # ===== Панель пагинации =====
        self.pagination_frame = tk.Frame(self, bg=COLORS['panel_bg'])
        self.pagination_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Кнопка "Первая"
        self.first_btn = tk.Button(
            self.pagination_frame, text="⏮", font=FONTS['field'],
            command=self.go_to_first, bg=COLORS['button_primary'],
            fg=COLORS['button_text'], relief=tk.FLAT, padx=8, pady=2,
            cursor='hand2'
        )
        self.first_btn.pack(side=tk.LEFT, padx=(0, 3))
        self.first_btn.bind('<Enter>', lambda e: self.first_btn.config(bg=COLORS['button_primary_hover']))
        self.first_btn.bind('<Leave>', lambda e: self.first_btn.config(bg=COLORS['button_primary']))
        
        # Кнопка "Предыдущая"
        self.prev_btn = tk.Button(
            self.pagination_frame, text="◀", font=FONTS['field'],
            command=self.go_to_prev, bg=COLORS['button_primary'],
            fg=COLORS['button_text'], relief=tk.FLAT, padx=8, pady=2,
            cursor='hand2'
        )
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.prev_btn.bind('<Enter>', lambda e: self.prev_btn.config(bg=COLORS['button_primary_hover']))
        self.prev_btn.bind('<Leave>', lambda e: self.prev_btn.config(bg=COLORS['button_primary']))
        
        # Индикатор страницы
        self.page_label = tk.Label(
            self.pagination_frame, text="Страница 0 / 0",
            font=FONTS['field'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        )
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        # Кнопка "Следующая"
        self.next_btn = tk.Button(
            self.pagination_frame, text="▶", font=FONTS['field'],
            command=self.go_to_next, bg=COLORS['button_primary'],
            fg=COLORS['button_text'], relief=tk.FLAT, padx=8, pady=2,
            cursor='hand2'
        )
        self.next_btn.pack(side=tk.LEFT, padx=(10, 3))
        self.next_btn.bind('<Enter>', lambda e: self.next_btn.config(bg=COLORS['button_primary_hover']))
        self.next_btn.bind('<Leave>', lambda e: self.next_btn.config(bg=COLORS['button_primary']))
        
        # Кнопка "Последняя"
        self.last_btn = tk.Button(
            self.pagination_frame, text="⏭", font=FONTS['field'],
            command=self.go_to_last, bg=COLORS['button_primary'],
            fg=COLORS['button_text'], relief=tk.FLAT, padx=8, pady=2,
            cursor='hand2'
        )
        self.last_btn.pack(side=tk.LEFT, padx=(0, 15))
        self.last_btn.bind('<Enter>', lambda e: self.last_btn.config(bg=COLORS['button_primary_hover']))
        self.last_btn.bind('<Leave>', lambda e: self.last_btn.config(bg=COLORS['button_primary']))
        
        # Индикатор записей
        self.records_label = tk.Label(
            self.pagination_frame, text="Всего: 0",
            font=FONTS['field'], bg=COLORS['panel_bg'], fg=COLORS['work_area_text']
        )
        self.records_label.pack(side=tk.LEFT, padx=10)
        
        # Размер страницы
        tk.Label(
            self.pagination_frame, text="На странице:",
            font=FONTS['field'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(side=tk.RIGHT, padx=(5, 3))
        
        self.page_size_var = tk.StringVar(value=str(self.page_size))
        self.page_size_combo = ttk.Combobox(
            self.pagination_frame, textvariable=self.page_size_var,
            values=['50', '100', '200', '500', '1000'],
            width=6, state='readonly', font=FONTS['field']
        )
        self.page_size_combo.pack(side=tk.RIGHT)
        self.page_size_combo.bind('<<ComboboxSelected>>', self._on_page_size_change)
    
    def _on_page_size_change(self, event=None):
        """Изменение размера страницы"""
        try:
            new_size = int(self.page_size_var.get())
            if new_size != self.page_size:
                self.page_size = new_size
                self.current_page = 0
                self.load_page()
        except ValueError:
            pass
    
    def set_load_callback(self, callback):
        """Установить функцию загрузки данных"""
        self.load_callback = callback
    
    def load_page(self, page=None):
        """
        Загрузить указанную страницу.
        Если page=None — загрузить текущую.
        """
        if page is not None:
            self.current_page = page
        
        if self.load_callback is None:
            return
        
        try:
            rows, total = self.load_callback(self.current_page, self.page_size)
            self.current_data = rows
            self.total_count = total
            self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
            
            # Ограничиваем текущую страницу
            if self.current_page >= self.total_pages:
                self.current_page = self.total_pages - 1
            
            self._render_page()
            self._update_pagination_ui()
        except Exception as e:
            print(f"Ошибка загрузки страницы: {e}")
    
    def load_all_data(self, data):
        """
        Загрузить все данные в память и пагинировать локально.
        Используется, когда данные уже загружены.
        """
        self.current_data = data
        self.total_count = len(data)
        self.total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        
        if self.current_page >= self.total_pages:
            self.current_page = self.total_pages - 1
        
        self._render_page()
        self._update_pagination_ui()
    
    def _render_page(self):
        """Отрисовать текущую страницу в Treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start = self.current_page * self.page_size
        end = start + self.page_size
        page_data = self.current_data[start:end]
        
        for i, row in enumerate(page_data):
            # Используем глобальный индекс как iid
            global_idx = start + i
            self.tree.insert('', 'end', iid=str(global_idx), values=row)
    
    def _update_pagination_ui(self):
        """Обновить состояние кнопок и индикаторов"""
        # Индикатор страницы
        self.page_label.config(
            text=f"Страница {self.current_page + 1} / {self.total_pages}"
        )
        
        # Индикатор записей
        start = self.current_page * self.page_size + 1 if self.total_count > 0 else 0
        end = min((self.current_page + 1) * self.page_size, self.total_count)
        self.records_label.config(
            text=f"Показано {start}-{end} из {self.total_count}"
        )
        
        # Состояние кнопок
        is_first = self.current_page == 0
        is_last = self.current_page >= self.total_pages - 1
        
        for btn in (self.first_btn, self.prev_btn):
            if is_first:
                btn.config(state='disabled', bg=COLORS['button_disabled'])
            else:
                btn.config(state='normal', bg=COLORS['button_primary'])
        
        for btn in (self.last_btn, self.next_btn):
            if is_last:
                btn.config(state='disabled', bg=COLORS['button_disabled'])
            else:
                btn.config(state='normal', bg=COLORS['button_primary'])
    
    def go_to_first(self):
        """Перейти на первую страницу"""
        self.load_page(0)
    
    def go_to_prev(self):
        """Перейти на предыдущую страницу"""
        if self.current_page > 0:
            self.load_page(self.current_page - 1)
    
    def go_to_next(self):
        """Перейти на следующую страницу"""
        if self.current_page < self.total_pages - 1:
            self.load_page(self.current_page + 1)
    
    def go_to_last(self):
        """Перейти на последнюю страницу"""
        if self.total_pages > 0:
            self.load_page(self.total_pages - 1)
    
    def refresh(self):
        """Перезагрузить текущую страницу"""
        self.load_page(self.current_page)
    
    def get_selection(self):
        """Получить выбранную строку"""
        selected = self.tree.selection()
        if not selected:
            return None
        item = self.tree.item(selected[0])
        return item.get('values')
    
    def get_selected_iid(self):
        """Получить iid выбранной строки"""
        selected = self.tree.selection()
        if not selected:
            return None
        return selected[0]
    
    def bind_select(self, callback):
        """Привязать обработчик выбора строки"""
        self.tree.bind('<<TreeviewSelect>>', callback)
    
    def bind_double_click(self, callback):
        """Привязать обработчик двойного клика"""
        self.tree.bind('<Double-Button-1>', callback)