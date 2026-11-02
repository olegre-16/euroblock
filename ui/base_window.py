"""
Базовый класс для всех окон программы.
[ИЗМЕНЕНО] 
- Окно скрывается до построения UI (убирает мерцание)
- Используется geometry() вместо state('zoomed') — работает на любом разрешении
- Окно подстраивается под размер главного окна
"""
import tkinter as tk
from tkinter import ttk
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
        
        # [НОВОЕ] Скрываем окно ДО построения UI — убирает мерцание
        self.window.withdraw()
        
        # [НОВОЕ] Применяем геометрию родителя (главного окна)
        # Это работает на ЛЮБОМ разрешении и в ЛЮБОЙ ОС
        self._apply_parent_geometry()
        
        # Строим интерфейс
        self._build_ui()
        
        # [НОВОЕ] Обновляем геометрию и показываем окно
        self.window.update_idletasks()
        self.window.deiconify()
        
        # Фокус на окно
        self.window.lift()
        self.window.focus_force()
    
    def _apply_parent_geometry(self):
        """
        Применить геометрию родительского окна.
        Окно открывается точно в том же месте и размере, что и главное окно.
        Работает на любом разрешении экрана.
        """
        try:
            # Обновляем информацию о родителе
            self.parent.update_idletasks()
            
            # Получаем геометрию родителя
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()
            
            # Если родитель ещё не отображён — используем размер экрана
            if parent_w < 100 or parent_h < 100:
                screen_w = self.window.winfo_screenwidth()
                screen_h = self.window.winfo_screenheight()
                parent_x = 0
                parent_y = 0
                parent_w = screen_w
                parent_h = screen_h
            
            # Применяем геометрию
            self.window.geometry(f"{parent_w}x{parent_h}+{parent_x}+{parent_y}")
        except Exception as e:
            # Fallback: максимальный размер экрана
            try:
                screen_w = self.window.winfo_screenwidth()
                screen_h = self.window.winfo_screenheight()
                self.window.geometry(f"{screen_w}x{screen_h}+0+0")
            except Exception:
                pass
    
    def _build_ui(self):
        """Построить интерфейс окна. Переопределяется в наследниках."""
        pass
    
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
        """
        Создать левую панель с прокруткой.
        Возвращает inner_frame, в который нужно упаковывать виджеты.
        """
        if width is None:
            width = self.LEFT_PANEL_WIDTH
        
        # Основной фрейм левой панели с фиксированной шириной
        left_frame = tk.Frame(
            parent_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border'],
            width=width
        )
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        left_frame.pack_propagate(False)
        
        # Canvas для прокрутки
        canvas = tk.Canvas(
            left_frame,
            bg=COLORS['panel_bg'],
            highlightthickness=0
        )
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Вертикальный скроллбар
        scrollbar = ttk.Scrollbar(
            left_frame,
            orient=tk.VERTICAL,
            command=canvas.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Внутренний фрейм для размещения элементов
        inner_frame = tk.Frame(canvas, bg=COLORS['panel_bg'])
        
        # Создаём окно в canvas
        canvas_window_id = canvas.create_window(
            (0, 0), window=inner_frame, anchor='nw', width=width
        )
        
        # Обновление области прокрутки при изменении размера inner_frame
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        
        inner_frame.bind('<Configure>', _on_frame_configure)
        
        # Обновление ширины inner_frame при изменении размера canvas
        def _on_canvas_configure(event):
            if event.width > 0:
                canvas.itemconfig(canvas_window_id, width=event.width)
        
        canvas.bind('<Configure>', _on_canvas_configure)
        
        # Прокрутка колёсиком мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        
        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        
        # Сохраняем ссылки
        self._scroll_canvas = canvas
        self._scroll_inner_frame = inner_frame
        self._scroll_left_frame = left_frame
        self._scroll_canvas_window_id = canvas_window_id
        
        return inner_frame
    
    def create_right_panel(self, parent_frame):
        """Создать правую панель"""
        right_frame = tk.Frame(
            parent_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return right_frame
    
    def create_title_section(self, parent_frame, title_text):
        """Создать заголовок окна"""
        title_frame = tk.Frame(parent_frame, bg=COLORS['background'])
        title_frame.pack(fill=tk.X, padx=PADDING['main'], pady=PADDING['main'])
        
        title_label = tk.Label(
            title_frame,
            text=title_text,
            font=FONTS['section_title'],
            bg=COLORS['background'],
            fg=COLORS['title_text']
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
        """
        Добавить метку поля.
        Текст выровнен по левому краю (anchor='w', justify='left').
        """
        lbl = tk.Label(
            parent,
            text=text,
            font=FONTS['field'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            anchor='w',
            justify='left'
        )
        lbl.pack(fill=tk.X, anchor='w', padx=10, pady=(5, 2))
        return lbl
    
    def add_button(self, parent, text, command, color=None, side=None):
        """
        Добавить кнопку.
        Если side=tk.BOTTOM - кнопка прижимается к низу родителя.
        """
        if color is None:
            color = COLORS['button_primary']
        
        btn = tk.Button(
            parent,
            text=text,
            font=FONTS['menu'],
            command=command,
            bg=color,
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        
        if side == tk.BOTTOM:
            btn.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        else:
            btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Hover эффекты
        if color == COLORS['button_primary']:
            hover_color = COLORS['button_primary_hover']
        elif color == COLORS['button_settings']:
            hover_color = COLORS['button_settings_hover']
        else:
            hover_color = color
        
        btn.bind('<Enter>', lambda e: btn.config(bg=hover_color))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        
        return btn