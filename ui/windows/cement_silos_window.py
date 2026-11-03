"""
Окно "Силос цемента" - управление силосами цемента
С дополнительным полем: Вмещаемый объем, тн
[ИЗМЕНЕНО] Уменьшен hardcoded шрифт заголовка таблицы.
"""
import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cement_silos_repo
from utils.excel_reader import read_xlsx_first_column, is_xlsx_file


class CementSilosWindow:
    """Окно управления силосами цемента с расширенными полями"""
    def __init__(self, parent, on_exit_callback):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.repo = cement_silos_repo
        
        # Состояние редактирования
        self.editing_silo_name = None
        
        # Основной контейнер
        self.main_frame = tk.Frame(parent, bg=COLORS['background'])
        
        # Заголовок
        self.title_label = tk.Label(
            self.main_frame,
            text="Силос цемента",
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
        
        self._create_input_field(
            label_text="Добавить силос цемента:",
            attr_name="name_entry"
        )
        
        self._create_input_field(
            label_text="Вмещаемый объем, тн:",
            attr_name="capacity_entry"
        )
        
        self.save_btn = tk.Button(
            self.left_frame,
            text="Сохранить",
            font=FONTS['menu'],
            command=self.save_silo,
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
        
        # ===== ПРАВАЯ ЧАСТЬ: таблица с 2 колонками =====
        self.right_frame = tk.Frame(
            self.content_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.table_title = tk.Label(
            self.right_frame,
            text="Добавленные записи: Силос цемента",
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
        # [ИЗМЕНЕНО] Уменьшен шрифт с 11 до 9
        style.configure('Treeview.Heading', font=('Arial', 9, 'bold'))
        
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=('name', 'capacity'),
            show='headings',
            yscrollcommand=self.scrollbar.set,
            selectmode='browse'
        )
        
        self.tree.heading('name', text='Наименование', anchor='w')
        self.tree.heading('capacity', text='Вмещаемый объем, тн', anchor='w')
        
        self.tree.column('name', width=400, anchor='w')
        self.tree.column('capacity', width=200, anchor='w')
        
        self.scrollbar.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_data()
    
    def _create_input_field(self, label_text, attr_name):
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
        entry.pack(fill=tk.X, ipady=SIZES['field_ipady'])
        
        setattr(self, attr_name, entry)
    
    def _on_save_enter(self):
        if self.editing_silo_name:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary_hover'])
    
    def _on_save_leave(self):
        if self.editing_silo_name:
            self.save_btn.config(bg='#27ae60')
        else:
            self.save_btn.config(bg=COLORS['button_primary'])
    
    def get_frame(self):
        return self.main_frame
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        data = self.repo.get_all()
        for row in data:
            name = row[0]
            capacity = row[1] if row[1] is not None else ''
            capacity_str = self._format_number(capacity)
            self.tree.insert('', 'end', iid=name, values=(name, capacity_str))
    
    def _format_number(self, value):
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
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для редактирования")
            return
        name_value = selected[0]
        item_values = self.tree.item(name_value, 'values')
        
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, item_values[0])
        self.capacity_entry.delete(0, tk.END)
        self.capacity_entry.insert(0, item_values[1])
        
        self.editing_silo_name = name_value
        self.save_btn.config(text="Обновить")
        self.name_entry.focus()
    
    def save_silo(self):
        name = self.name_entry.get()
        capacity = self.capacity_entry.get()
        
        if self.editing_silo_name:
            success, message = self.repo.update(
                self.editing_silo_name, 
                name, 
                capacity
            )
            if success:
                messagebox.showinfo("Успех", message)
                self._clear_fields()
                self.load_data()
            else:
                messagebox.showwarning("Ошибка", message)
        else:
            success, message = self.repo.add(name, capacity)
            if success:
                messagebox.showinfo("Успех", message)
                self._clear_fields()
                self.load_data()
            else:
                messagebox.showwarning("Ошибка", message)
    
    def _clear_fields(self):
        self.name_entry.delete(0, tk.END)
        self.capacity_entry.delete(0, tk.END)
        self.editing_silo_name = None
        self.save_btn.config(text="Сохранить")
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return
        name_value = selected[0]
        if messagebox.askyesno("Подтверждение", f"Удалить силос цемента \"{name_value}\"?"):
            self.repo.delete(name_value)
            if self.editing_silo_name == name_value:
                self._clear_fields()
            self.load_data()
            messagebox.showinfo("Успех", "Запись удалена")
    
    def import_table(self):
        if self.editing_silo_name:
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
            "Файл должен содержать 2 колонки:\n"
            "1. Наименование силоса цемента\n"
            "2. Вмещаемый объем, тн\n\n"
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
            capacity = row[1] if len(row) > 1 else ''
            
            success, message = self.repo.add(name, capacity)
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
                                while len(row) < 2:
                                    row.append('')
                                rows.append(row[:2])
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Не удалось определить кодировку файла")
        
        elif is_xlsx_file(file_path):
            from utils.excel_reader import read_xlsx_rows
            rows = read_xlsx_rows(file_path, max_columns=2)
        
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(';')
                    if parts:
                        while len(parts) < 2:
                            parts.append('')
                        rows.append(parts[:2])
        
        if rows:
            first = rows[0][0].strip().lower()
            header_keywords = [
                'наименование', 'название', 'name', 'силос', 
                'силос цемента', 'емкость'
            ]
            if first in header_keywords or first.replace(' ', '') in header_keywords:
                rows = rows[1:]
        
        return rows