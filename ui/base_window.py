"""
Базовый класс для всех окон программы.
Все окна открываются сразу на полный экран.
Единое оформление как в окне "Производство продукции".

[ИЗМЕНЕНО]
- Добавлены методы-обёртки для messagebox (предотвращают сворачивание окна)
- Добавлен метод _restore_window_state() для восстановления окна
- Убрана прокрутка левой панели колесом мыши
- Гарантированное освобождение grab и уничтожение дочерних окон при закрытии
- Callback вызывается ПЕРЕД уничтожением окна
- [НОВОЕ] Таймер автообновления данных для сетевого режима (каждые 3 секунды)
- [НОВОЕ] Метод _on_auto_refresh() для переопределения в наследниках
- [НОВОE] Отложенное восстановление окна через after() для корректной работы на Windows
- [НОВОЕ] Метод _final_raise() для финального поднятия окна
- [НОВОЕ] Сохранение состояния окна перед messagebox (_saved_window_state)
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
        
        # Флаг остановки таймера автообновления
        self._auto_refresh_stopped = False
        
        # [НОВОЕ] Сохранённое состояние окна (для восстановления после messagebox)
        self._saved_window_state = 'zoomed'
        
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
        
        # [НОВОЕ] Запускаем таймер автообновления для сетевого режима
        self._start_auto_refresh_timer()
    
    def _build_ui(self):
        """Построить интерфейс окна. Переопределяется в наследниках."""
        pass
    
    # ========================================================================
    # [ИЗМЕНЕНО] Методы-обёртки для messagebox
    # Предотвращают сворачивание окна при показе диалогов
    # ========================================================================
    def _prepare_for_messagebox(self):
        """
        Подготовить окно перед показом messagebox.
        [ИЗМЕНЕНО] Сохраняет текущее состояние окна для последующего восстановления.
        """
        try:
            # Сохраняем текущее состояние окна
            self._saved_window_state = self.window.state()
            
            # Поднимаем окно на передний план
            self.window.attributes('-topmost', True)
            self.window.lift()
            self.window.focus_force()
            self.window.update_idletasks()
        except tk.TclError:
            pass
    
    def _restore_after_messagebox(self):
        """
        Восстановить состояние окна после показа messagebox.
        [ИЗМЕНЕНО] Используется отложенное восстановление через after(),
        чтобы окно успело корректно развернуться на Windows.
        """
        def _do_restore():
            try:
                if not self.window.winfo_exists():
                    return
                
                # Если окно свёрнуто — разворачиваем
                if self.window.state() == 'iconic':
                    self.window.deiconify()
                    self.window.update_idletasks()
                
                # Восстанавливаем предыдущее состояние (обычно zoomed)
                saved_state = getattr(self, '_saved_window_state', 'zoomed')
                if saved_state == 'zoomed':
                    self.window.state('zoomed')
                
                # Снимаем topmost
                self.window.attributes('-topmost', False)
                
                # Поднимаем окно и даём фокус
                self.window.lift()
                self.window.focus_force()
                self.window.update_idletasks()
                
                # Финальное поднятие через 100мс для надёжности
                self.window.after(100, self._final_raise)
            except tk.TclError:
                pass
        
        # Запускаем восстановление в главном цикле событий
        try:
            self.window.after(10, _do_restore)
        except tk.TclError:
            pass
    
    def _final_raise(self):
        """
        Финальное поднятие окна после messagebox.
        Вызывается через 100мс после основного восстановления.
        """
        try:
            if not self.window.winfo_exists():
                return
            self.window.lift()
            self.window.focus_force()
            self.window.attributes('-topmost', True)
            self.window.after(100, lambda: self.window.attributes('-topmost', False))
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
    # Метод восстановления состояния окна
    # ========================================================================
    def _restore_window_state(self):
        """
        Восстановить окно в полноэкранном режиме.
        Вызывать после операций для гарантии, что окно открыто.
        [ИЗМЕНЕНО] Использует отложенное восстановление через after().
        """
        def _do_restore():
            try:
                if not self.window.winfo_exists():
                    return
                
                if self.window.state() == 'iconic':
                    self.window.deiconify()
                    self.window.update_idletasks()
                
                self.window.state('zoomed')
                self.window.lift()
                self.window.focus_force()
                self.window.attributes('-topmost', True)
                self.window.after(100, lambda: self.window.attributes('-topmost', False))
            except tk.TclError:
                pass
            except Exception as e:
                print(f"⚠ Ошибка восстановления окна: {e}")
        
        try:
            self.window.after(10, _do_restore)
        except tk.TclError:
            pass
    
    # ========================================================================
    # [НОВОЕ] ТАЙМЕР АВТООБНОВЛЕНИЯ ДАННЫХ
    # ========================================================================
    def _start_auto_refresh_timer(self):
        """
        Запустить таймер автообновления данных.
        В сетевом режиме каждые 3 секунды вызывает _on_auto_refresh().
        """
        try:
            from client_config import MODE
            if MODE == 'network':
                self._auto_refresh_interval = 3000  # 3 секунды
                self._auto_refresh_stopped = False
                self._schedule_auto_refresh()
        except ImportError:
            pass
    
    def _schedule_auto_refresh(self):
        """Запланировать следующее автообновление"""
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
        """
        Выполнить автообновление.
        Проверяет, изменилась ли БД, и если да — вызывает _on_auto_refresh().
        """
        try:
            # Проверяем, не остановлен ли таймер
            if getattr(self, '_auto_refresh_stopped', False):
                return
            
            # Проверяем, существует ли окно
            if not hasattr(self, 'window') or not self.window.winfo_exists():
                return
            
            # Проверяем, изменилась ли БД
            from database.connection import get_db_sync_monitor
            monitor = get_db_sync_monitor()
            
            if monitor.check_for_changes(force=True):
                # БД изменилась — обновляем данные в окне
                try:
                    self._on_auto_refresh()
                except Exception as e:
                    print(f"⚠ Ошибка автообновления: {e}")
            
            # Планируем следующее обновление
            self._schedule_auto_refresh()
        except Exception as e:
            print(f"⚠ Ошибка в _do_auto_refresh: {e}")
            # Планируем следующее обновление даже при ошибке
            try:
                self._schedule_auto_refresh()
            except:
                pass
    
    def _on_auto_refresh(self):
        """
        Метод автообновления данных в окне.
        Переопределяется в наследниках для обновления конкретных данных.
        По умолчанию — ничего не делает.
        """
        pass
    
    # ========================================================================
    # Закрытие окна
    # ========================================================================
    def _on_close(self):
        """
        Закрытие окна.
        Гарантированное освобождение grab и уничтожение дочерних окон.
        """
        # Останавливаем таймер автообновления
        try:
            self._auto_refresh_stopped = True
        except Exception:
            pass
        
        try:
            # Освобождаем grab, если он установлен
            try:
                self.window.grab_release()
            except tk.TclError:
                pass
            
            # Закрываем все дочерние Toplevel окна (диалоги, messagebox)
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
            
            # Вызываем callback ПЕРЕД уничтожением окна
            if self.on_exit_callback:
                try:
                    self.on_exit_callback()
                except Exception:
                    pass
            
            # Уничтожаем основное окно
            try:
                self.window.destroy()
            except tk.TclError:
                pass
        except Exception as e:
            print(f"⚠ Ошибка закрытия окна: {e}")
    
    def get_frame(self):
        return self.window
    
    # ========================================================================
    # Создание панелей
    # ========================================================================
    def create_left_panel_with_scroll(self, parent_frame, width=None):
        """
        Создать левую панель с прокруткой.
        Прокрутка колесом мыши ПОЛНОСТЬЮ ОТКЛЮЧЕНА.
        Скроллбар работает только через клик и перетаскивание мышью.
        """
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
        
        # Сохраняем ссылки
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
    
    # ========================================================================
    # Вспомогательные методы для создания элементов
    # ========================================================================
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