"""
Диалоговое окно с индикатором прогресса.
Используется для отображения прогресса длительных операций.
"""
import tkinter as tk
from tkinter import ttk
from config.settings import COLORS, FONTS, PADDING, SIZES


class ProgressDialog:
    """
    Модальное диалоговое окно с прогресс-баром.
    
    Поддерживает два режима:
    - indeterminate: анимированный прогресс-бар (когда нельзя определить прогресс)
    - determinate: прогресс-бар с конкретным значением (0-100%)
    
    Пример использования:
        progress = ProgressDialog(parent, "Загрузка", "Пожалуйста, подождите...")
        
        # Обновление сообщения
        progress.update_message("Обработка данных...")
        
        # Обновление прогресса (для determinate режима)
        progress.update_progress(50)  # 50%
        
        # Закрытие
        progress.close()
    """
    
    def __init__(self, parent, title: str, message: str, 
                 mode: str = 'indeterminate', cancellable: bool = False):
        """
        Args:
            parent: родительское окно
            title: заголовок диалога
            message: начальное сообщение
            mode: 'indeterminate' или 'determinate'
            cancellable: если True, показывается кнопка "Отмена"
        """
        self.parent = parent
        self.mode = mode
        self.cancellable = cancellable
        self.cancelled = False
        self.closed = False
        
        # Создаём диалог
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.configure(bg=COLORS['panel_bg'])
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Размеры
        dialog_width = 450
        dialog_height = 180 if cancellable else 150
        
        # Центрирование относительно родителя
        parent.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - dialog_width) // 2
        y = parent_y + (parent_h - dialog_height) // 2
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Запрет закрытия через крестик (если нельзя отменить)
        if not cancellable:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_close_disabled)
        else:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        self._build_ui(message)
        
        # Запускаем анимацию для indeterminate режима
        if mode == 'indeterminate':
            self.progress_bar.start(15)
    
    def _build_ui(self, message: str):
        """Построить интерфейс диалога"""
        # Заголовок
        self.title_label = tk.Label(
            self.dialog,
            text="Пожалуйста, подождите",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        self.title_label.pack(pady=(15, 5))
        
        # Синий разделитель
        tk.Frame(self.dialog, height=2, bg=COLORS['button_primary']).pack(
            fill=tk.X, padx=20, pady=(0, 10)
        )
        
        # Сообщение
        self.message_label = tk.Label(
            self.dialog,
            text=message,
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            wraplength=400
        )
        self.message_label.pack(pady=(0, 10), padx=20)
        
        # Прогресс-бар
        progress_mode = 'indeterminate' if self.mode == 'indeterminate' else 'determinate'
        self.progress_bar = ttk.Progressbar(
            self.dialog,
            orient='horizontal',
            length=400,
            mode=progress_mode
        )
        self.progress_bar.pack(pady=(0, 10), padx=20)
        
        if self.mode == 'determinate':
            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 100
        
        # Процент (для determinate режима)
        if self.mode == 'determinate':
            self.percent_label = tk.Label(
                self.dialog,
                text="0%",
                font=FONTS['field'],
                bg=COLORS['panel_bg'],
                fg=COLORS['work_area_text']
            )
            self.percent_label.pack()
        
        # Кнопка отмены (если разрешена)
        if self.cancellable:
            self.cancel_btn = tk.Button(
                self.dialog,
                text="Отмена",
                font=FONTS['menu'],
                command=self._on_cancel,
                bg=COLORS['button_settings'],
                fg=COLORS['button_text'],
                relief=tk.FLAT,
                padx=15,
                pady=5,
                cursor='hand2'
            )
            self.cancel_btn.pack(pady=10)
            self.cancel_btn.bind('<Enter>', 
                               lambda e: self.cancel_btn.config(bg=COLORS['button_settings_hover']))
            self.cancel_btn.bind('<Leave>', 
                               lambda e: self.cancel_btn.config(bg=COLORS['button_settings']))
    
    def _on_close_disabled(self):
        """Обработчик закрытия, когда отмена запрещена"""
        pass  # Ничего не делаем
    
    def _on_cancel(self):
        """Обработчик отмены"""
        self.cancelled = True
        self.close()
    
    def update_message(self, message: str):
        """Обновить сообщение"""
        if not self.closed:
            self.message_label.config(text=message)
            self.dialog.update_idletasks()
    
    def update_progress(self, value: int):
        """
        Обновить прогресс (только для determinate режима).
        
        Args:
            value: значение от 0 до 100
        """
        if self.mode != 'determinate' or self.closed:
            return
        
        value = max(0, min(100, value))
        self.progress_bar['value'] = value
        
        if hasattr(self, 'percent_label'):
            self.percent_label.config(text=f"{value}%")
        
        self.dialog.update_idletasks()
    
    def close(self):
        """Закрыть диалог"""
        if self.closed:
            return
        
        self.closed = True
        
        try:
            if self.mode == 'indeterminate':
                self.progress_bar.stop()
            
            self.dialog.grab_release()
            self.dialog.destroy()
        except tk.TclError:
            pass  # Диалог уже закрыт
    
    def is_cancelled(self) -> bool:
        """Проверить, была ли операция отменена"""
        return self.cancelled


class StatusMessage:
    """
    Временное сообщение в статусной строке.
    Автоматически исчезает через указанное время.
    """
    
    def __init__(self, parent, message: str, duration_ms: int = 3000):
        """
        Args:
            parent: родительский виджет
            message: текст сообщения
            duration_ms: время показа в миллисекундах
        """
        self.label = tk.Label(
            parent,
            text=message,
            font=FONTS['field'],
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            padx=10,
            pady=5
        )
        self.label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Автоматическое скрытие через duration_ms
        parent.after(duration_ms, self._hide)
    
    def _hide(self):
        """Скрыть сообщение"""
        try:
            self.label.destroy()
        except tk.TclError:
            pass