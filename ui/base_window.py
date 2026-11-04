"""
Базовый класс для всех окон программы.
Все окна открываются сразу на полный экран.
Единое оформление как в окне "Производство продукции".
[ИЗМЕНЕНО] Добавлены методы-обёртки для messagebox и _restore_window_state.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config.settings import COLORS, FONTS, PADDING, SIZES


class BaseToplevelWindow:
    """
    Базовый класс для окон программы.
    Оформление идентично окну "Производство продукции".
    """
    LEFT_PANEL_WIDTH = 350
    
    def __init__(self, parent, on_exit_callback, title="Окно"):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.window_title = title
        
        # Создаём Toplevel окно
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.configure(bg=COLORS['background'])
        
        # Обработчик закрытия
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # СРАЗУ РАЗВОРАЧИВАЕМ НА ВЕСЬ ЭКРАН
        self.window.state('zoomed')
        
        # Строим интерфейс
        self._build_ui()
    
    def _build_ui(self):
        """Построить интерфейс окна. Переопределяется в наследниках."""
        pass
    
    # ========================================================================
    # [НОВОЕ] Методы-обёртки для messagebox
    # Предотвращают сворачивание окна при показе диалогов
    # ========================================================================
    def _prepare_for_messagebox(self):
        """Подготовить окно перед показом messagebox"""
        try:
            self.window.attributes('-topmost', True)
            self.window.update_idletasks()
        except tk.TclError:
            pass
    
    def _restore_after_messagebox(self):
        """Восстановить состояние окна после показа messagebox"""
        try:
            if self.window.state() == 'iconic':
                self.window.deiconify()
            self.window.state('zoomed')
            self.window.attributes('-topmost', False)
            self.window.lift()
            self.window.focus_force()
            self.window.update_idletasks()
        except tk.TclError:
            pass
    
    def show_info(self, title, message):
        """Показать информационное сообщение (без сворачивания окна)"""
        self._prepare_for_messagebox()
        result = messagebox.showinfo(title, message, parent=self.window)
        self._restore_after_messagebox()
        return result
    
    def show_warning(self, title, message):
        """Показать предупреждение (без сворачивания окна)"""
        self._prepare_for_messagebox()
        result = messagebox.showwarning(title, message, parent=self.window)
        self._restore_after_messagebox()
        return result
    
    def show_error(self, title, message):
        """Показать ошибку (без сворачивания окна)"""
        self._prepare_for_messagebox()
        result = messagebox.showerror(title, message, parent=self.window)
        self._restore_after_messagebox()
        return result
    
    def ask_yes_no(self, title, message):
        """Задать вопрос Да/Нет (без сворачивания окна)"""
        self._prepare_for_messagebox()
        result = messagebox.askyesno(title, message, parent=self.window)
        self._restore_after_messagebox()
        return result
    
    # ========================================================================
    # [НОВОЕ] Метод восстановления состояния окна
    # ========================================================================
    def _restore_window_state(self):
        """Восстановить окно в полноэкранном режиме"""
        try:
            if self.window.state() == 'iconic':
                self.window.deiconify()
            self.window.state('zoomed')
            self.window.lift()
            self.window.focus_force()
            self.window.attributes('-topmost', True)
            self.window.after(100, lambda: self.window.attributes('-topmost', False))
        except tk.TclError:
            pass
        except Exception as e:
            print(f"⚠ Ошибка восстановления окна: {e}")
    
    # ========================================================================
    # Остальные методы базового класса
    # ========================================================================
    def _on_close(self):
        """Закрытие окна"""
        try:
            try:
                self.window.grab_release()
            except tk.TclError:
                pass
        except:
            pass
        self.window.destroy()
        if self.on_exit_callback:
            self.on_exit_callback()
    
    def get_frame(self):
        return self.window
    
    def create_left_panel_with_scroll(self, parent_frame, width=None):
        """Создать левую панель с прокруткой."""
        if width is None:
            width = self.LEFT_PANEL_WIDTH
        
        left_frame = tk.Frame(
            parent_frame, bg=COLORS['panel_bg'],
            relief=tk.RAISED, bd=SIZES['panel_border'], width=width
        )
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        left_frame.pack_propagate(False)
        
        canvas = tk.Canvas(left_frame, bg=COLORS['panel_bg'], highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        inner_frame = tk.Frame(canvas, bg=COLORS['panel_bg'])
        canvas_window_id = canvas.create_window(
            (0, 0), window=inner_frame, anchor='nw', width=width
        )
        
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        inner_frame.bind('<Configure>', _on_frame_configure)
        
        def _on_canvas_configure(event):
            if event.width > 0:
                canvas.itemconfig(canvas_window_id, width=event.width)
        
        canvas.bind('<Configure>', _on_canvas_configure)
        
        # [ИЗМЕНЕНО] Прокрутка колесом мыши ПОЛНОСТЬЮ ОТКЛЮЧЕНА
        # Скроллбар работает только через клик и перетаскивание
        
        self._scroll_canvas = canvas
        self._scroll_inner_frame = inner_frame
        self._scroll_left_frame = left_frame
        self._scroll_canvas_window_id = canvas_window_id
        
        return inner_frame
    
    def create_right_panel(self, parent_frame):
        """Создать правую панель"""
        right_frame = tk.Frame(
            parent_frame, bg=COLORS['panel_bg'],
            relief=tk.RAISED, bd=SIZES['panel_border']
        )
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return right_frame
    
    def create_title_section(self, parent_frame, title_text):
        """Создать заголовок окна"""
        title_frame = tk.Frame(parent_frame, bg=COLORS['background'])
        title_frame.pack(fill=tk.X, padx=PADDING['main'], pady=PADDING['main'])
        
        title_label = tk.Label(
            title_frame, text=title_text,
            font=FONTS['section_title'], bg=COLORS['background'], fg=COLORS['title_text']
        )
        title_label.pack(anchor='w')
        
        separator = tk.Frame(title_frame, height=2, bg=COLORS['button_primary'])
        separator.pack(fill=tk.X, pady=(10, 0))
        
        return title_frame
    
    def create_content_frame(self, parent_frame):
        """Создать основной контейнер"""
        content_frame = tk.Frame(parent_frame, bg=COLORS['background'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING['main'], pady=(0, PADDING['main']))
        return content_frame
    
    def add_field_label(self, parent, text):
        """Добавить метку поля."""
        lbl = tk.Label(
            parent, text=text, font=FONTS['field'],
            bg=COLORS['panel_bg'], fg=COLORS['title_text'],
            anchor='w', justify='left'
        )
        lbl.pack(fill=tk.X, anchor='w', padx=10, pady=(5, 2))
        return lbl
    
    def add_button(self, parent, text, command, color=None, side=None):
        """Добавить кнопку."""
        if color is None:
            color = COLORS['button_primary']
        
        btn = tk.Button(
            parent, text=text, font=FONTS['menu'], command=command,
            bg=color, fg=COLORS['button_text'], relief=tk.FLAT,
            padx=PADDING['button_x'], pady=PADDING['button_y'], cursor='hand2'
        )
        
        if side == tk.BOTTOM:
            btn.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        else:
            btn.pack(fill=tk.X, padx=10, pady=5)
        
        if color == COLORS['button_primary']:
            hover_color = COLORS['button_primary_hover']
        elif color == COLORS['button_settings']:
            hover_color = COLORS['button_settings_hover']
        else:
            hover_color = color
        
        btn.bind('<Enter>', lambda e: btn.config(bg=hover_color))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        
        return btn