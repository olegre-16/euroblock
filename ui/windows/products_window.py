"""
Окно "Продукция" - управление номенклатурой продукции
С дополнительными полями: Объем на поддоне, Норматив производства
"""
import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import products_repo
from utils.excel_reader import read_xlsx_first_column, is_xlsx_file


class ProductsWindow:
    """Окно управления продукцией с расширенными полями"""
    
    def __init__(self, parent, on_exit_callback):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.repo = products_repo
        
        # Состояние редактирования
        self.editing_product_name = None
        
        # Основной контейнер
        self.main_frame = tk.Frame(parent, bg=COLORS['background'])
        
        # Заголовок
        self.title_label = tk.Label(
            self.main_frame,
            text="Продукция",
            font=FONTS['section_title'],
            bg=COLORS['background'],
            fg=COLORS['title_text']
        )
        self.title_label.pack(pady=(20, 0), anchor='w', padx=20)
        
        separator = tk.Frame(self.main_frame, height=2, bg=COLORS['button_primary'])
        separator.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        self.content_frame = tk.Frame(self.main_frame, bg=COLORS['background'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # ===== ЛЕВАЯ ЧАСТЬ =====
        self.left_frame = tk.Frame(
            self.content_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        
        # Поле "Наименование продукции"
        self._create_input_field(
            label_text="Наименование продукции:",
            attr_name="name_entry"
        )
        
        # Поле "Объем на поддоне, шт/м2"
        self._create_input_field(
            label_text="Объем на поддоне, шт/м2:",
            attr_name="volume_entry"
        )
        
        # Поле "Норматив производства, поддоны" (ИЗМЕНЕНО)
        self._create_input_field(
            label_text="Норматив производства, поддоны:",
            attr_name="rate_entry"
        )
        
        # Кнопка "Сохранить"
        self.save_btn = tk.Button(
            self.left_frame,
            text="Сохранить",
            font=FONTS['menu'],
            command=self.save_product,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.save_btn.pack(fill=tk.X, padx=PADDING['button_x'], pady=(10, 5))
        self.save_btn.bind('<Enter>', lambda e: self._on_save_enter())
        self.save_btn.bind('<Leave>', lambda e: self._on_save_leave())
        
        # Кнопка "Изменить"
        self.edit_btn = tk.Button(
            self.left_frame,
            text="Изменить",
            font=FONTS['menu'],
            command=self.edit_selected,
            bg='#f39c12',
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.edit_btn.pack(fill=tk.X, padx=PADDING['button_x'], pady=5)
        self.edit_btn.bind('<Enter>', lambda e: self.edit_btn.config(bg='#d68910'))
        self.edit_btn.bind('<Leave>', lambda e: self.edit_btn.config(bg='#f39c12'))
        
        # Кнопка "Удалить выбранное"
        self.delete_btn = tk.Button(
            self.left_frame,
            text="Удалить выбранное",
            font=FONTS['menu'],
            command=self.delete_selected,
            bg='#e74c3c',
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.delete_btn.pack(fill=tk.X, padx=PADDING['button_x'], pady=5)
        self.delete_btn.bind('<Enter>', lambda e: self.delete_btn.config(bg='#c0392b'))
        self.delete_btn.bind('<Leave>', lambda e: self.delete_btn.config(bg='#e74c3c'))
        
        # Кнопка "Импорт таблицы"
        self.import_btn = tk.Button(
            self.left_frame,
            text="Импорт таблицы",
            font=FONTS['menu'],
            command=self.import_table,
            bg=COLORS['button_import'],
            fg=COLORS['title_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.import_btn.pack(fill=tk.X, padx=PADDING['button_x'], pady=5)
        self.import_btn.bind('<Enter>', lambda e: self.import_btn.config(bg=COLORS['button_import_hover']))
        self.import_btn.bind('<Leave>', lambda e: self.import_btn.config(bg=COLORS['button_import']))
        
        # Кнопка "Выход" внизу
        self.exit_btn = tk.Button(
            self.left_frame,
            text="Выход",
            font=FONTS['menu'],
            command=self.on_exit_callback,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.exit_btn.pack(fill=tk.X, side=tk.BOTTOM, padx=PADDING['button_x'], pady=PADDING['button_x'])
        self.exit_btn.bind('<Enter>', lambda e: self.exit_btn.config(bg=COLORS['button_settings_hover']))
        self.exit_btn.bind('<Leave>', lambda e: self.exit_btn.config(bg=COLORS['button_settings']))
        
        # ===== ПРАВАЯ ЧАСТЬ: таблица с 3 колонками =====
        self.right_frame = tk.Frame(
            self.content_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.table_title = tk.Label(
            self.right_frame,
            text="Добавленные записи: Продукция",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        self.table_title.pack(pady=(10, 5), anchor='w', padx=10)
        
        self.tree_frame = tk.Frame(self.right_frame, bg=COLORS['panel_bg'])
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.scrollbar = ttk.Scrollbar(self.tree_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        style = ttk.Style()
        style.configure('Treeview', font=FONTS['menu'], rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 11, 'bold'))
        
        # Таблица с 3 колонками
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=('name', 'volume', 'rate'),
            show='headings',
            yscrollcommand=self.scrollbar.set,
            selectmode='browse'
        )
        
        # Все заголовки выровнены влево
        self.tree.heading('name', text='Наименование', anchor='w')
        self.tree.heading('volume', text='Объем на поддоне, шт/м2', anchor='w')
        # ИЗМЕНЕНО: заголовок столбца теперь содержит единицу измерения
        self.tree.heading('rate', text='Норматив производства, поддоны', anchor='w')
        
        # Все данные выровнены влево
        self.tree.column('name', width=350, anchor='w')
        self.tree.column('volume', width=180, anchor='w')
        # Увеличена ширина колонки для длинного заголовка
        self.tree.column('rate', width=230, anchor='w')
        
        self.scrollbar.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_data()
    
    def _create_input_field(self, label_text, attr_name):
        """Создать поле ввода с меткой и сохранить в атрибут"""
        field_frame = tk.Frame(self.left_frame, bg=COLORS['panel_bg'])
        field_frame.pack(fill=tk.X, padx=PADDING['button_x'], pady=(5, 0))
        
        label = tk.Label(
            field_frame,
            text=label_text,
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        label.pack(anchor='w', pady=(0, 3))
        
        entry = tk.Entry(
            field_frame,
            font=FONTS['menu'],
            width=30,
            relief=tk.SOLID,
            bd=1
        )
        entry.pack(fill=tk.X, ipady=5)
        
        setattr(self, attr_name, entry)
    
    def _on_save_enter(self):
        """Обработка наведения на кнопку Сохранить/Обновить"""
        if self.editing_product_name:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary_hover'])
    
    def _on_save_leave(self):
        """Обработка ухода курсора с кнопки Сохранить/Обновить"""
        if self.editing_product_name:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary'])
    
    def get_frame(self):
        return self.main_frame
    
    def load_data(self):
        """Загрузить данные в таблицу"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        data = self.repo.get_all()
        for row in data:
            name = row[0]
            volume = row[1] if row[1] is not None else ''
            rate = row[2] if row[2] is not None else ''
            
            volume_str = self._format_number(volume)
            rate_str = self._format_number(rate)
            
            self.tree.insert('', 'end', iid=name, values=(name, volume_str, rate_str))
    
    def _format_number(self, value):
        """Форматировать число: убрать лишние нули после запятой"""
        if value == '' or value is None:
            return ''
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:g}"
        except (ValueError, TypeError):
            return str(value)
    
    def edit_selected(self):
        """Загрузить данные выбранной записи в поля ввода для редактирования"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return
        
        name_value = selected[0]
        item_values = self.tree.item(name_value, 'values')
        
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, item_values[0])
        
        self.volume_entry.delete(0, tk.END)
        self.volume_entry.insert(0, item_values[1])
        
        self.rate_entry.delete(0, tk.END)
        self.rate_entry.insert(0, item_values[2])
        
        self.editing_product_name = name_value
        self.save_btn.config(text="Обновить")
        
        self.name_entry.focus()
    
    def save_product(self):
        """Сохранить новую запись или обновить существующую"""
        name = self.name_entry.get()
        volume = self.volume_entry.get()
        rate = self.rate_entry.get()
        
        if self.editing_product_name:
            success, message = self.repo.update(
                self.editing_product_name, 
                name, 
                volume, 
                rate
            )
            
            if success:
                messagebox.showinfo("Успех", message)
                self._clear_fields()
                self.load_data()
            else:
                messagebox.showwarning("Ошибка", message)
        else:
            success, message = self.repo.add(name, volume, rate)
            
            if success:
                messagebox.showinfo("Успех", message)
                self._clear_fields()
                self.load_data()
            else:
                messagebox.showwarning("Ошибка", message)
    
    def _clear_fields(self):
        """Очистить поля ввода и сбросить режим редактирования"""
        self.name_entry.delete(0, tk.END)
        self.volume_entry.delete(0, tk.END)
        self.rate_entry.delete(0, tk.END)
        self.editing_product_name = None
        self.save_btn.config(text="Сохранить")
    
    def delete_selected(self):
        """Удалить выбранную запись"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return
        
        name_value = selected[0]
        
        if messagebox.askyesno("Подтверждение", f"Удалить продукцию \"{name_value}\"?"):
            self.repo.delete(name_value)
            if self.editing_product_name == name_value:
                self._clear_fields()
            self.load_data()
            messagebox.showinfo("Успех", "Запись удалена")
    
    def import_table(self):
        """Импорт продукции из внешнего файла (3 колонки)"""
        if self.editing_product_name:
            if not messagebox.askyesno(
                "Внимание",
                "Вы находитесь в режиме редактирования. Импорт не затронет текущую запись.\n"
                "Продолжить импорт?"
            ):
                return
        
        file_path = filedialog.askopenfilename(
            title="Выберите файл для импорта",
            filetypes=[
                ("Все поддерживаемые", "*.csv *.xlsx"),
                ("Файлы CSV", "*.csv"),
                ("Файлы Excel", "*.xlsx"),
                ("Все файлы", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        if not messagebox.askyesno(
            "Подтверждение импорта",
            f"Импортировать данные из файла:\n{os.path.basename(file_path)}?\n\n"
            "Файл должен содержать 3 колонки:\n"
            "1. Наименование продукции\n"
            "2. Объем на поддоне, шт/м2\n"
            "3. Норматив производства, поддоны\n\n"
            "Дубликаты будут пропущены."
        ):
            return
        
        try:
            rows = self._read_file(file_path)
        except Exception as e:
            messagebox.showerror("Ошибка чтения файла", f"Не удалось прочитать файл:\n{e}")
            return
        
        if not rows:
            messagebox.showwarning("Внимание", "Файл не содержит данных для импорта")
            return
        
        added = 0
        skipped = 0
        errors = []
        
        for row in rows:
            if len(row) < 1 or not row[0].strip():
                continue
            
            name = row[0].strip()
            volume = row[1] if len(row) > 1 else ''
            rate = row[2] if len(row) > 2 else ''
            
            success, message = self.repo.add(name, volume, rate)
            if success:
                added += 1
            else:
                if "уже существует" in message:
                    skipped += 1
                else:
                    errors.append(f"{name}: {message}")
        
        report = f"Импорт завершён:\n\n"
        report += f"✓ Добавлено: {added}\n"
        report += f"⊘ Пропущено (дубликаты): {skipped}\n"
        
        if errors:
            report += f"✗ Ошибок: {len(errors)}\n\n"
            report += "Примеры ошибок:\n" + "\n".join(errors[:5])
        
        messagebox.showinfo("Результат импорта", report)
        self.load_data()
    
    def _read_file(self, file_path):
        """
        Прочитать данные из файла.
        Возвращает список строк, где каждая строка — список из 3 значений:
        [наименование, объем_на_поддоне, норматив_производства]
        """
        ext = os.path.splitext(file_path)[1].lower()
        rows = []
        
        if ext == '.csv':
            for encoding in ['utf-8', 'utf-8-sig', 'cp1251', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding, newline='') as f:
                        sample = f.read(2048)
                        f.seek(0)
                        try:
                            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
                        except csv.Error:
                            dialect = csv.excel
                        
                        reader = csv.reader(f, dialect)
                        for row in reader:
                            if row:
                                while len(row) < 3:
                                    row.append('')
                                rows.append(row[:3])
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Не удалось определить кодировку файла")
        
        elif is_xlsx_file(file_path):
            from utils.excel_reader import read_xlsx_rows
            rows = read_xlsx_rows(file_path, max_columns=3)
        
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(';')
                    if parts:
                        while len(parts) < 3:
                            parts.append('')
                        rows.append(parts[:3])
        
        # Пропуск заголовка
        if rows:
            first = rows[0][0].strip().lower()
            header_keywords = [
                'наименование', 'название', 'name', 'продукция',
                'вид продукции', 'номенклатура'
            ]
            if first in header_keywords or first.replace(' ', '') in header_keywords:
                rows = rows[1:]
        
        return rows