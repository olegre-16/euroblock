"""
Мастер первоначальной настройки программы.
Запускается только при первом запуске.
Определяет роль режима работы (локальный/сетевой) и настраивает подключение.
[ИЗМЕНЕНО] 
- Для сетевого режима используется диалог выбора папки (filedialog.askdirectory)
- Путь к БД формируется автоматически: выбранная_папка + \\euroblock.db
- Проверка доступности папки и наличия БД
- Все компьютеры равноправны — нет разделения на основной/клиентский
- Используется один главный диалог на протяжении всей настройки
- Корректная работа с grab_set без transient()
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import socket
from config.settings import COLORS, FONTS, PADDING, SIZES


class SetupWizard:
    """Мастер первоначальной настройки"""
    
    # Имя файла базы данных (фиксированное)
    DB_FILENAME = 'euroblock.db'
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None  # 'configured' или None (отмена)
        
        # Определяем папку конфигурации
        import sys
        if getattr(sys, 'frozen', False):
            self.config_dir = os.path.dirname(sys.executable)
        else:
            self.config_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        self.config_file = os.path.join(self.config_dir, 'network_config.ini')
        self.marker_file = os.path.join(self.config_dir, '.first_run_done')
        
        # Выбранный путь к БД (для сетевого режима)
        self.selected_db_path = None
        
        self._create_main_dialog()
        self._show_mode_selection()
    
    def _create_main_dialog(self):
        """Создать главный диалог мастера"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Первоначальная настройка")
        self.dialog.configure(bg=COLORS['panel_bg'])
        self.dialog.resizable(False, False)
        
        self.dialog_width = 650
        self.dialog_height = 500
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        x = (screen_w - self.dialog_width) // 2
        y = (screen_h - self.dialog_height) // 2
        self.dialog.geometry(f"{self.dialog_width}x{self.dialog_height}+{x}+{y}")
        
        self.content_frame = tk.Frame(self.dialog, bg=COLORS['panel_bg'])
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Гарантированное отображение
        self.dialog.deiconify()
        self.dialog.lift()
        self.dialog.attributes('-topmost', True)
        self.dialog.update()
        self.dialog.attributes('-topmost', False)
        self.dialog.focus_force()
        self.dialog.grab_set()
    
    def _clear_content(self):
        """Очистить содержимое контейнера шагов"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    # ========================================================================
    # ШАГ 1: Выбор режима работы
    # ========================================================================
    def _show_mode_selection(self):
        """Шаг 1: Выбор режима работы"""
        self._clear_content()
        
        tk.Label(
            self.content_frame,
            text="Мастер первоначальной настройки",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(20, 10))
        
        tk.Frame(self.content_frame, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 15)
        )
        
        tk.Label(
            self.content_frame,
            text="Выберите режим работы программы:",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            justify='center'
        ).pack(pady=(10, 15))
        
        btn_frame = tk.Frame(self.content_frame, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=40, pady=(0, 10))
        
        # Кнопка "Многопользовательский режим"
        network_btn = tk.Button(
            btn_frame,
            text="Многопользовательский режим\n(работа с общей базой данных по сети)",
            font=FONTS['menu'],
            command=self._show_network_setup,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=12,
            cursor='hand2',
            justify='center'
        )
        network_btn.pack(fill=tk.X, pady=(0, 10))
        network_btn.bind('<Enter>', lambda e: network_btn.config(bg=COLORS['button_primary_hover']))
        network_btn.bind('<Leave>', lambda e: network_btn.config(bg=COLORS['button_primary']))
        
        # Кнопка "Локальный режим"
        local_btn = tk.Button(
            btn_frame,
            text="Локальный режим\n(один пользователь, база на этом компьютере)",
            font=FONTS['menu'],
            command=self._save_local_config,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=12,
            cursor='hand2',
            justify='center'
        )
        local_btn.pack(fill=tk.X)
        local_btn.bind('<Enter>', lambda e: local_btn.config(bg=COLORS['button_settings_hover']))
        local_btn.bind('<Leave>', lambda e: local_btn.config(bg=COLORS['button_settings']))
        
        # Подсказка
        tk.Label(
            self.content_frame,
            text="Режим можно изменить позже, удалив файл network_config.ini",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            justify='center'
        ).pack(pady=(15, 0))
    
    # ========================================================================
    # ШАГ 2: Выбор сетевой папки через диалог
    # ========================================================================
    def _show_network_setup(self):
        """Шаг 2: Выбор сетевой папки через диалог"""
        self._clear_content()
        
        tk.Label(
            self.content_frame,
            text="Настройка многопользовательского режима",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(20, 10))
        
        tk.Frame(self.content_frame, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 15)
        )
        
        tk.Label(
            self.content_frame,
            text="Выберите сетевую папку, в которой будет храниться общая база данных.\n"
                 "Все пользователи программы будут работать с этой БД.",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            justify='center'
        ).pack(pady=(0, 15))
        
        # ===== Поле пути =====
        path_frame = tk.Frame(self.content_frame, bg=COLORS['panel_bg'])
        path_frame.pack(fill=tk.X, padx=30, pady=(0, 5))
        
        tk.Label(
            path_frame,
            text="Путь к общей базе данных:",
            font=FONTS['field'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            anchor='w'
        ).pack(fill=tk.X, pady=(0, 5))
        
        # Поле ввода (read-only) + кнопка "Обзор"
        entry_frame = tk.Frame(path_frame, bg=COLORS['panel_bg'])
        entry_frame.pack(fill=tk.X)
        
        self.path_entry = tk.Entry(
            entry_frame,
            font=FONTS['field'],
            relief=tk.SOLID,
            bd=1,
            state='readonly',
            readonlybackground='#f5f5f5'
        )
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        browse_btn = tk.Button(
            entry_frame,
            text="Обзор...",
            font=FONTS['field'],
            command=self._browse_folder,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=10,
            cursor='hand2'
        )
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        browse_btn.bind('<Enter>', lambda e: browse_btn.config(bg=COLORS['button_primary_hover']))
        browse_btn.bind('<Leave>', lambda e: browse_btn.config(bg=COLORS['button_primary']))
        
        # ===== Статус папки =====
        self.status_frame = tk.Frame(self.content_frame, bg=COLORS['panel_bg'])
        self.status_frame.pack(fill=tk.X, padx=30, pady=(10, 10))
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Папка не выбрана",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            anchor='w',
            justify='left'
        )
        self.status_label.pack(fill=tk.X)
        
        # ===== Подсказки =====
        tk.Label(
            self.content_frame,
            text="Советы:\n"
                 "• В диалоге выбора можно открыть «Сеть» и выбрать нужный компьютер\n"
                 "• Папка должна быть открыта для чтения/записи всем пользователям\n"
                 "• Если БД в папке уже есть — программа подключится к ней\n"
                 "• Если БД нет — она будет создана при первом запуске",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            justify='left',
            anchor='w'
        ).pack(fill=tk.X, padx=30, pady=(5, 15))
        
        # ===== Кнопки =====
        btn_frame = tk.Frame(self.content_frame, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=30, pady=(0, 20))
        
        self.connect_btn = tk.Button(
            btn_frame,
            text="Подключиться",
            font=FONTS['menu'],
            command=self._on_connect,
            bg=COLORS['button_disabled'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2',
            state='disabled'
        )
        self.connect_btn.pack(fill=tk.X, pady=(0, 10))
        
        back_btn = tk.Button(
            btn_frame,
            text="← Назад",
            font=FONTS['menu'],
            command=self._show_mode_selection,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor='hand2'
        )
        back_btn.pack(fill=tk.X)
        back_btn.bind('<Enter>', lambda e: back_btn.config(bg=COLORS['button_settings_hover']))
        back_btn.bind('<Leave>', lambda e: back_btn.config(bg=COLORS['button_settings']))
    
    def _browse_folder(self):
        """Открыть диалог выбора папки"""
        # Открываем диалог выбора папки
        folder_path = filedialog.askdirectory(
            parent=self.dialog,
            title="Выберите сетевую папку для базы данных",
            initialdir='\\\\',  # Начинаем с сетевого окружения
            mustexist=False  # Папка может не существовать — создадим
        )
        
        if not folder_path:
            # Пользователь отменил выбор
            return
        
        # Нормализуем путь
        folder_path = os.path.normpath(folder_path)
        
        # Формируем полный путь к БД
        db_path = os.path.join(folder_path, self.DB_FILENAME)
        
        # Сохраняем выбранный путь
        self.selected_db_path = db_path
        
        # Отображаем путь в поле
        self.path_entry.config(state='normal')
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, db_path)
        self.path_entry.config(state='readonly')
        
        # Проверяем папку и обновляем статус
        self._check_folder_status(folder_path)
    
    def _check_folder_status(self, folder_path):
        """Проверить статус папки и обновить индикатор"""
        # Проверяем доступность папки
        if not os.path.exists(folder_path):
            self._set_status(
                f"⚠ Папка не существует: {folder_path}\n"
                f"База данных будет создана при первом запуске.",
                COLORS['msg_icon_warning']
            )
            self._enable_connect_button()
            return
        
        # Проверяем возможность записи
        test_file = os.path.join(folder_path, '.write_test_temp')
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('test')
            os.remove(test_file)
            can_write = True
        except Exception:
            can_write = False
        
        if not can_write:
            self._set_status(
                f"✗ Нет прав на запись в папку:\n{folder_path}\n"
                f"Обратитесь к администратору для предоставления прав.",
                COLORS['msg_icon_error']
            )
            self.connect_btn.config(state='disabled', bg=COLORS['button_disabled'])
            return
        
        # Проверяем наличие БД
        db_path = os.path.join(folder_path, self.DB_FILENAME)
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            self._set_status(
                f"✓ Папка доступна. База данных найдена ({size_mb:.2f} МБ).\n"
                f"Программа подключится к существующей БД.",
                COLORS['msg_icon_info']
            )
        else:
            self._set_status(
                f"✓ Папка доступна. База данных будет создана при первом запуске.",
                COLORS['msg_icon_info']
            )
        
        self._enable_connect_button()
    
    def _set_status(self, text, color):
        """Обновить статус-лейбл"""
        self.status_label.config(text=text, fg=color)
    
    def _enable_connect_button(self):
        """Активировать кнопку подключения"""
        self.connect_btn.config(state='normal', bg=COLORS['button_primary'])
        self.connect_btn.bind('<Enter>', lambda e: self.connect_btn.config(bg=COLORS['button_primary_hover']))
        self.connect_btn.bind('<Leave>', lambda e: self.connect_btn.config(bg=COLORS['button_primary']))
    
    def _on_connect(self):
        """Обработка нажатия кнопки «Подключиться»"""
        if not self.selected_db_path:
            messagebox.showwarning(
                "Внимание",
                "Сначала выберите папку",
                parent=self.dialog
            )
            return
        
        # Дополнительная проверка перед сохранением
        folder_path = os.path.dirname(self.selected_db_path)
        
        if os.path.exists(folder_path):
            # Проверяем возможность записи
            test_file = os.path.join(folder_path, '.write_test_temp')
            try:
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write('test')
                os.remove(test_file)
            except Exception:
                messagebox.showerror(
                    "Ошибка",
                    f"Нет прав на запись в папку:\n{folder_path}",
                    parent=self.dialog
                )
                return
        
        # Сохраняем конфигурацию
        self._save_network_config(self.selected_db_path)
    
    # ========================================================================
    # Сохранение конфигурации
    # ========================================================================
    def _save_local_config(self):
        """Сохранить конфигурацию для локального режима"""
        try:
            db_path = os.path.join(self.config_dir, self.DB_FILENAME)
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
            
            self.result = 'configured'
            
            try:
                self.dialog.grab_release()
            except tk.TclError:
                pass
            self.dialog.destroy()
            
            messagebox.showinfo(
                "Настройка завершена",
                "Локальный режим сохранён.\n\n"
                "Программа будет работать с локальной базой данных."
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{e}", parent=self.dialog)
    
    def _save_network_config(self, network_path):
        """Сохранить конфигурацию для сетевого режима"""
        try:
            # Нормализуем путь для корректного отображения
            normalized_path = os.path.normpath(network_path)
            
            config_content = f"""# Конфигурация многопользовательского режима
# Создано мастером настройки

[mode]
mode = network

[network]
db_path = {normalized_path}
busy_timeout = 30
check_interval = 2
is_main = false
"""
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            with open(self.marker_file, 'w', encoding='utf-8') as f:
                f.write('done')
            
            self.result = 'configured'
            
            try:
                self.dialog.grab_release()
            except tk.TclError:
                pass
            self.dialog.destroy()
            
            messagebox.showinfo(
                "Настройка завершена",
                f"Многопользовательский режим сохранён.\n\n"
                f"Путь к общей БД:\n{normalized_path}\n\n"
                f"Все пользователи программы будут работать с этой базой данных.\n"
                f"При следующем запуске подключение произойдёт автоматически."
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки:\n{e}", parent=self.dialog)
    
    def _on_cancel(self):
        """Отмена настройки"""
        self.result = None
        try:
            self.dialog.grab_release()
        except tk.TclError:
            pass
        self.dialog.destroy()
        try:
            self.parent.quit()
        except tk.TclError:
            pass
    
    def get_result(self):
        """Получить результат настройки"""
        return self.result


def is_first_run(config_dir):
    """
    Проверить, является ли это первым запуском программы.
    
    Args:
        config_dir: папка с конфигурацией
    
    Returns:
        True, если это первый запуск (нет маркера)
    """
    marker_file = os.path.join(config_dir, '.first_run_done')
    return not os.path.exists(marker_file)


def run_setup_wizard(parent, config_dir=None):
    """
    Запустить мастер настройки.
    
    Args:
        parent: родительское окно (root)
        config_dir: папка с конфигурацией (не используется, но оставлено для совместимости)
    
    Returns:
        'configured' — если настройка прошла успешно
        None — если настройка отменена
    """
    wizard = SetupWizard(parent)
    
    try:
        parent.mainloop()
    except tk.TclError:
        pass
    
    return wizard.get_result()