"""
Базовый класс для окон справочников.
"""
import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config.settings import COLORS, FONTS, PADDING, SIZES
from utils.excel_reader import read_xlsx_first_column, is_xlsx_file


class BaseDictionaryWindow:
    """Базовый класс окна справочника"""
    
    def __init__(self, parent, on_exit_callback, title, item_label, repo):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.title_text = title
        self.item_label = item_label
        self.repo = repo
        
        self.main_frame = tk.Frame(parent, bg=COLORS['background'])
        
        self.title_label = tk.Label(
            self.main_frame,
            text=self.title_text,
            font=FONTS['section_title'],
            bg=COLORS['background'],
            fg=COLORS['title_text']
        )
        self.title_label.pack(pady=(20, 0), anchor='w', padx=20)
        
        separator = tk.Frame(self.main_frame, height=2, bg=COLORS['button_primary'])
        separator.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        self.content_frame = tk.Frame(self.main_frame, bg=COLORS['background'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.left_frame = tk.Frame(
            self.content_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        
        self.input_frame = tk.Frame(self.left_frame, bg=COLORS['panel_bg'])
        self.input_frame.pack(fill=tk.X, padx=PADDING['button_x'], pady=PADDING['button_x'])
        
        self.input_label = tk.Label(
            self.input_frame,
            text=self.item_label,
            font=FONTS['field'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        self.input_label.pack(anchor='w', pady=(0, 5))
        
        self.input_entry = tk.Entry(
            self.input_frame,
            font=FONTS['field'],
            width=30,
            relief=tk.SOLID,
            bd=1
        )
        self.input_entry.pack(fill=tk.X, ipady=SIZES['field_ipady'])
        self.input_entry.bind('<Return>', lambda e: self.save_item())
        
        self.save_btn = tk.Button(
            self.left_frame,
            text="Сохранить",
            font=FONTS['menu'],
            command=self.save_item,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.save_btn.pack(fill=tk.X, padx=PADDING['button_x'], pady=(10, 5))
        self.save_btn.bind('<Enter>', lambda e: self.save_btn.config(bg=COLORS['button_primary_hover']))
        self.save_btn.bind('<Leave>', lambda e: self.save_btn.config(bg=COLORS['button_primary']))
        
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
        
        self.right_frame = tk.Frame(
            self.content_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.table_title = tk.Label(
            self.right_frame,
            text=f"Добавленные записи: {self.title_text}",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        self.table_title.pack(pady=(10, 5), anchor='w', padx=10)
        
        self.tree_frame = tk.Frame(self.right_frame, bg=COLORS['panel_bg'])
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.scrollbar = ttk.Scrollbar(self.tree_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview использует глобальные стили из main_window.py
        
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=('name',),
            show='headings',
            yscrollcommand=self.scrollbar.set,
            selectmode='browse'
        )
        
        self.tree.heading('name', text='Наименование', anchor='w')
        self.tree.column('name', width=500, anchor='w')
        
        self.scrollbar.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_data()
    
    def get_frame(self):
        return self.main_frame
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        data = self.repo.get_all()
        for row in data:
            name = row[0]
            self.tree.insert('', 'end', iid=name, values=(name,))
    
    def save_item(self):
        name = self.input_entry.get()
        success, message = self.repo.add(name)
        
        if success:
            messagebox.showinfo("Успех", message)
            self.input_entry.delete(0, tk.END)
            self.load_data()
        else:
            messagebox.showwarning("Ошибка", message)
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите запись для удаления")
            return
        
        name_value = selected[0]
        
        if messagebox.askyesno("Подтверждение", f"Удалить запись \"{name_value}\"?"):
            self.repo.delete(name_value)
            self.load_data()
            messagebox.showinfo("Успех", "Запись удалена")
    
    def import_table(self):
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
            "Дубликаты будут пропущены."
        ):
            return
        
        try:
            names = self._read_file(file_path)
        except Exception as e:
            messagebox.showerror("Ошибка чтения файла", f"Не удалось прочитать файл:\n{e}")
            return
        
        if not names:
            messagebox.showwarning("Внимание", "Файл не содержит данных для импорта")
            return
        
        added = 0
        skipped = 0
        errors = []
        
        for name in names:
            name = name.strip()
            if not name:
                continue
            
            success, message = self.repo.add(name)
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
        names = []
        
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
                                names.append(row[0])
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Не удалось определить кодировку файла")
        
        elif is_xlsx_file(file_path):
            names = read_xlsx_first_column(file_path)
        
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                names = [line.strip() for line in f if line.strip()]
        
        if names:
            first = names[0].strip().lower()
            header_keywords = [
                'наименование', 'название', 'name', 'вид оплаты', 'вид',
                'материал', 'услуга', 'назначение', 'оборудование',
                'плательщик', 'покупатель', 'поставщик', 'продукция',
                'силос', 'цвет'
            ]
            if first in header_keywords or first.replace(' ', '') in header_keywords:
                names = names[1:]
        
        return names

    def _on_auto_refresh(self):
        """
        Автообновление данных при изменении БД другим компьютером.
        Вызывается таймером из BaseToplevelWindow каждые 3 секунды.
        Применяется ко всем окнам справочников.
        """
        try:
            self.load_data()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в BaseDictionaryWindow: {e}")