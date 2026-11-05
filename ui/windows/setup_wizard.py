"""
Мастер первоначальной настройки программы.
Запускается только при первом запуске.
Определяет роль компьютера (основной/клиент) и настраивает подключение.
"""
import tkinter as tk
from tkinter import messagebox
import os
import socket
from config.settings import COLORS, FONTS, PADDING, SIZES


class SetupWizard:
    """Мастер первоначальной настройки"""
    
    def __init__(self, parent, config_dir):
        self.parent = parent
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, 'network_config.ini')
        self.marker_file = os.path.join(config_dir, '.first_run_done')
        
        self.result = None
        self.dialog = None
        
        self._show_main_question()
    
    def _show_main_question(self):
        """Шаг 1: Вопрос — это основной компьютер?"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Первоначальная настройка")
        self.dialog.configure(bg=COLORS['panel_bg'])
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        width, height = 550, 350
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        tk.Label(
            self.dialog,
            text="Мастер первоначальной настройки",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(20, 10))
        
        tk.Frame(self.dialog, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 15)
        )
        
        tk.Label(
            self.dialog,
            text="Это основной компьютер,\nна котором будет храниться база данных?",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            justify='center'
        ).pack(pady=(10, 5))
        
        tk.Label(
            self.dialog,
            text="(Основной компьютер должен быть включён,\nчтобы другие пользователи могли работать)",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            justify='center'
        ).pack(pady=(0, 20))
        
        btn_frame = tk.Frame(self.dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=40, pady=(0, 20))
        
        yes_btn = tk.Button(
            btn_frame,
            text="Да, это основной компьютер",
            font=FONTS['menu'],
            command=self._on_main_computer,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        yes_btn.pack(fill=tk.X, pady=(0, 10))
        yes_btn.bind('<Enter>', lambda e: yes_btn.config(bg=COLORS['button_primary_hover']))
        yes_btn.bind('<Leave>', lambda e: yes_btn.config(bg=COLORS['button_primary']))
        
        no_btn = tk.Button(
            btn_frame,
            text="Нет, это клиентский компьютер",
            font=FONTS['menu'],
            command=self._on_client_computer,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        no_btn.pack(fill=tk.X)
        no_btn.bind('<Enter>', lambda e: no_btn.config(bg=COLORS['button_settings_hover']))
        no_btn.bind('<Leave>', lambda e: no_btn.config(bg=COLORS['button_settings']))
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _on_main_computer(self):
        self.dialog.destroy()
        self._show_main_computer_info()
    
    def _on_client_computer(self):
        self.dialog.destroy()
        self._show_client_setup()
    
    def _on_cancel(self):
        self.result = None
        self.dialog.destroy()
    
    def _show_main_computer_info(self):
        """Шаг 2А: Показать информацию о основном компьютере"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Основной компьютер — информация")
        self.dialog.configure(bg=COLORS['panel_bg'])
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        width, height = 600, 450
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        tk.Label(
            self.dialog,
            text="Настройка основного компьютера",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(20, 10))
        
        tk.Frame(self.dialog, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 15)
        )
        
        local_ip = self._get_local_ip()
        computer_name = socket.gethostname()
        db_path = os.path.join(self.config_dir, 'euroblock.db')
        network_path = f"\\\\{computer_name}\\{os.path.basename(self.config_dir)}\\euroblock.db"
        
        info_frame = tk.Frame(self.dialog, bg=COLORS['panel_bg'])
        info_frame.pack(fill=tk.X, padx=30, pady=(10, 10))
        
        def add_info_row(label, value):
            row = tk.Frame(info_frame, bg=COLORS['panel_bg'])
            row.pack(fill=tk.X, pady=3)
            tk.Label(
                row, text=f"{label}:",
                font=FONTS['field'],
                bg=COLORS['panel_bg'],
                fg=COLORS['work_area_text'],
                width=20, anchor='w'
            ).pack(side=tk.LEFT)
            
            value_text = tk.Text(
                row, font=FONTS['field'],
                bg=COLORS['panel_bg'],
                fg=COLORS['title_text'],
                height=1, wrap='none',
                relief=tk.FLAT, bd=0
            )
            value_text.insert('1.0', value)
            value_text.config(state='disabled')
            value_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        add_info_row("Имя компьютера", computer_name)
        add_info_row("IP-адрес", local_ip)
        add_info_row("Путь к БД (локально)", db_path)
        add_info_row("Путь для клиентов", network_path)
        
        tk.Label(
            self.dialog,
            text="Инструкция:",
            font=FONTS['field'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            anchor='w'
        ).pack(fill=tk.X, padx=30, pady=(15, 5))
        
        instructions = (
            "1. Создайте общую папку с программой\n"
            "2. Дайте всем пользователям права чтения/записи\n"
            "3. На клиентских компьютерах выберите\n"
            "   «Нет, это клиентский компьютер»\n"
            "4. Введите путь: " + network_path
        )
        
        tk.Label(
            self.dialog,
            text=instructions,
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            justify='left',
            anchor='w'
        ).pack(fill=tk.X, padx=30)
        
        btn_frame = tk.Frame(self.dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=(20, 20))
        
        done_btn = tk.Button(
            btn_frame,
            text="Готово — сохранить настройки",
            font=FONTS['menu'],
            command=lambda: self._save_main_config(db_path),
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        done_btn.pack(fill=tk.X)
        done_btn.bind('<Enter>', lambda e: done_btn.config(bg=COLORS['button_primary_hover']))
        done_btn.bind('<Leave>', lambda e: done_btn.config(bg=COLORS['button_primary']))
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _show_client_setup(self):
        """Шаг 2Б: Ввод данных основного компьютера"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Подключение к основному компьютеру")
        self.dialog.configure(bg=COLORS['panel_bg'])
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        width, height = 550, 380
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        tk.Label(
            self.dialog,
            text="Подключение к основному компьютеру",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(20, 10))
        
        tk.Frame(self.dialog, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 15)
        )
        
        tk.Label(
            self.dialog,
            text="Введите путь к базе данных на основном компьютере.\n"
                 "Попросите эти данные у администратора основного компьютера.",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            justify='center'
        ).pack(pady=(0, 15))
        
        input_frame = tk.Frame(self.dialog, bg=COLORS['panel_bg'])
        input_frame.pack(fill=tk.X, padx=30, pady=(0, 10))
        
        tk.Label(
            input_frame,
            text="Путь к базе данных:",
            font=FONTS['field'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            anchor='w'
        ).pack(fill=tk.X, pady=(0, 5))
        
        self.path_entry = tk.Entry(
            input_frame,
            font=FONTS['field'],
            relief=tk.SOLID,
            bd=1
        )
        self.path_entry.pack(fill=tk.X, ipady=5)
        self.path_entry.insert(0, "\\\\ИМЯ_КОМПЬЮТЕРА\\Общая_папка\\euroblock.db")
        self.path_entry.bind('<FocusIn>', self._on_path_focus)
        
        tk.Label(
            self.dialog,
            text="Пример: \\\\OFFICE-PC\\Euroblock\\euroblock.db",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            anchor='w'
        ).pack(fill=tk.X, padx=30, pady=(5, 15))
        
        btn_frame = tk.Frame(self.dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        connect_btn = tk.Button(
            btn_frame,
            text="Подключиться",
            font=FONTS['menu'],
            command=self._on_connect,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        connect_btn.pack(fill=tk.X, pady=(0, 10))
        connect_btn.bind('<Enter>', lambda e: connect_btn.config(bg=COLORS['button_primary_hover']))
        connect_btn.bind('<Leave>', lambda e: connect_btn.config(bg=COLORS['button_primary']))
        
        cancel_btn = tk.Button(
            btn_frame,
            text="Отмена",
            font=FONTS['menu'],
            command=self._on_cancel,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        cancel_btn.pack(fill=tk.X)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg=COLORS['button_settings_hover']))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg=COLORS['button_settings']))
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _on_path_focus(self, event):
        if self.path_entry.get().startswith("\\\\ИМЯ_"):
            self.path_entry.delete(0, tk.END)
    
    def _on_connect(self):
        path = self.path_entry.get().strip()
        
        if not path:
            messagebox.showwarning("Внимание", "Введите путь к базе данных")
            return
        
        if not path.lower().endswith('.db'):
            messagebox.showwarning(
                "Внимание",
                "Путь должен заканчиваться на .db\n"
                "Пример: \\\\SERVER\\Share\\euroblock.db"
            )
            return
        
        db_dir = os.path.dirname(path)
        if not os.path.exists(db_dir):
            result = messagebox.askyesno(
                "Папка недоступна",
                f"Папка не найдена:\n{db_dir}\n\n"
                f"Основной компьютер выключен или папка недоступна.\n"
                f"Сохранить настройки и продолжить?"
            )
            if not result:
                return
        
        self._save_client_config(path)
    
    def _save_main_config(self, db_path):
        """Сохранить конфигурацию для основного компьютера"""
        try:
            config_content = f"""# Конфигурация многопользовательского режима
# Создано мастером настройки

[mode]
mode = local

[local]
db_path = {db_path}
is_main = true
"""
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            with open(self.marker_file, 'w', encoding='utf-8') as f:
                f.write('done')
            
            self.result = 'main'
            self.dialog.destroy()
            
            messagebox.showinfo(
                "Настройка завершена",
                "Конфигурация основного компьютера сохранена.\n\n"
                "Теперь другие компьютеры могут подключаться к этому."
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{e}")
    
    def _save_client_config(self, network_path):
        """Сохранить конфигурацию для клиентского компьютера"""
        try:
            config_content = f"""# Конфигурация многопользовательского режима
# Создано мастером настройки

[mode]
mode = network

[network]
db_path = {network_path}
busy_timeout = 30
check_interval = 2
is_main = false
"""
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            with open(self.marker_file, 'w', encoding='utf-8') as f:
                f.write('done')
            
            self.result = 'client'
            self.dialog.destroy()
            
            messagebox.showinfo(
                "Настройка завершена",
                f"Конфигурация клиента сохранена.\n\n"
                f"Путь к БД: {network_path}\n\n"
                "При следующем запуске подключение произойдёт автоматически."
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{e}")
    
    def _get_local_ip(self):
        """Получить локальный IP-адрес компьютера"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def get_result(self):
        return self.result


def is_first_run(config_dir):
    """Проверить, является ли это первым запуском программы"""
    marker_file = os.path.join(config_dir, '.first_run_done')
    return not os.path.exists(marker_file)


def run_setup_wizard(parent, config_dir):
    """Запустить мастер настройки"""
    wizard = SetupWizard(parent, config_dir)
    parent.wait_window(wizard.dialog)
    return wizard.get_result()