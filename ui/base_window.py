"""
Базовый класс для всех окон программы.
[ИЗМЕНЕНО]
- Убраны отложенные вызовы after() из _restore_after_messagebox()
- Восстановление окна теперь синхронное — нет конфликтов с messagebox
- Убран _final_raise() — он вызывал лишние перерисовки
- Упрощена логика подготовки и восстановления окна
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config.settings import COLORS, FONTS, PADDING, SIZES


class BaseToplevelWindow:
    """Базовый класс для окон программы."""
    LEFT_PANEL_WIDTH = 350
    
    def __init__(self, parent, on_exit_callback, title="Окно"):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.window_title = title
        
        self._auto_refresh_stopped = False
        
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.configure(bg=COLORS['background'])
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.state('zoomed')
        
        self._build_ui()
        self._start_auto_refresh_timer()
    
    def _build_ui(self):
        pass
    
    # ========================================================================
    # [ИЗМЕНЕНО] УПРОЩЁННЫЕ МЕТОДЫ РАБОТЫ С MESSAGEBOX
    # ========================================================================
    def _prepare_for_messagebox(self):
        """
        Подготовить окно перед показом messagebox.
        [ИЗМЕНЕНО] Убраны отложенные вызовы — всё синхронно.
        """
        try:
            self.window.attributes('-topmost', True)
            self.window.lift()
            self.window.update_idletasks()
        except tk.TclError:
            pass
    
    def _restore_after_messagebox(self):
        """
        Восстановить состояние окна после показа messagebox.
        [ИЗМЕНЕНО] Синхронное восстановление без after().
        Это устраняет "промаргивание" диалогов.
        """
        try:
            if not self.window.winfo_exists():
                return
            
            # Если окно свёрнуто — разворачиваем
            if self.window.state() == 'iconic':
                self.window.deiconify()
            
            # Разворачиваем на весь экран
            self.window.state('zoomed')
            
            # Снимаем topmost
            self.window.attributes('-topmost', False)
            
            # Поднимаем окно и даём фокус
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
    # [ИЗМЕНЕНО] УПРОЩЁННЫЙ МЕТОД ВОССТАНОВЛЕНИЯ ОКНА
    # ========================================================================
    def _restore_window_state(self):
        """
        Восстановить окно в полноэкранном режиме.
        [ИЗМЕНЕНО] Синхронное восстановление без after().
        Вызывать только при необходимости — обычно не нужно,
        т.к. обёртки messagebox сами восстанавливают окно.
        """
        try:
            if not self.window.winfo_exists():
                return
            if self.window.state() == 'iconic':
                self.window.deiconify()
            self.window.state('zoomed')
            self.window.lift()
            self.window.focus_force()
            self.window.update_idletasks()
        except tk.TclError:
            pass
    
    # ========================================================================
    # ТАЙМЕР АВТООБНОВЛЕНИЯ
    # ========================================================================
    def _start_auto_refresh_timer(self):
        try:
            from client_config import MODE
            if MODE == 'network':
                self._auto_refresh_interval = 3000
                self._auto_refresh_stopped = False
                self._schedule_auto_refresh()
        except ImportError:
            pass
    
    def _schedule_auto_refresh(self):
        try:
            if (hasattr(self, 'window') and 
                self.window.winfo_exists() and 
                not getattr(self, '_auto_refresh_stopped', False)):
                self.window.after(
                    self._auto_refresh_interval,
                    self._do_auto_refresh
                )
        except tk.TclError:
            pass
    
    def _do_auto_refresh(self):
        try:
            if getattr(self, '_auto_refresh_stopped', False):
                return
            if not hasattr(self, 'window') or not self.window.winfo_exists():
                return
            
            from database.connection import get_db_sync_monitor
            monitor = get_db_sync_monitor()
            
            if monitor.check_for_changes(force=True):
                try:
                    self._on_auto_refresh()
                except Exception as e:
                    print(f"⚠ Ошибка автообновления: {e}")
            
            self._schedule_auto_refresh()
        except Exception as e:
            print(f"⚠ Ошибка в _do_auto_refresh: {e}")
            try:
                self._schedule_auto_refresh()
            except:
                pass
    
    def _on_auto_refresh(self):
        pass
    
    # ========================================================================
    # ЗАКРЫТИЕ ОКНА
    # ========================================================================
    def _on_close(self):
        try:
            self._auto_refresh_stopped = True
        except Exception:
            pass
        
        try:
            try:
                self.window.grab_release()
            except tk.TclError:
                pass
            
            try:
                for widget in list(self.window.winfo_children()):
                    if isinstance(widget, tk.Toplevel):
                        try:
                            widget.grab_release()
                        except tk.TclError:
                            pass
                        try:
                            widget.destroy()
                        except tk.TclError:
                            pass
            except Exception:
                pass
            
            if self.on_exit_callback:
                try:
                    self.on_exit_callback()
                except Exception:
                    pass
            
            try:
                self.window.destroy()
            except tk.TclError:
                pass
        except Exception as e:
            print(f"⚠ Ошибка закрытия окна: {e}")
    
    def get_frame(self):
        return self.window
    
    # ========================================================================
    # СОЗДАНИЕ ПАНЕЛЕЙ
    # ========================================================================
    def create_left_panel_with_scroll(self, parent_frame, width=None):
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
        
        self._scroll_canvas = canvas
        self._scroll_inner_frame = inner_frame
        self._scroll_left_frame = left_frame
        self._scroll_canvas_window_id = canvas_window_id
        
        return inner_frame
    
    def create_right_panel(self, parent_frame):
        right_frame = tk.Frame(
            parent_frame, bg=COLORS['panel_bg'],
            relief=tk.RAISED, bd=SIZES['panel_border']
        )
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return right_frame
    
    def create_title_section(self, parent_frame, title_text):
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
        content_frame = tk.Frame(parent_frame, bg=COLORS['background'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING['main'], pady=(0, PADDING['main']))
        return content_frame
    
    def add_field_label(self, parent, text):
        lbl = tk.Label(
            parent, text=text, font=FONTS['field'],
            bg=COLORS['panel_bg'], fg=COLORS['title_text'],
            anchor='w', justify='left'
        )
        lbl.pack(fill=tk.X, anchor='w', padx=10, pady=(5, 2))
        return lbl
    
    def add_button(self, parent, text, command, color=None, side=None):
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