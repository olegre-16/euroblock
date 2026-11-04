"""
Кастомный виджет Combobox с автодополнением.
Использует собственный popup на базе Listbox.
[ИЗМЕНЕНО] Блокировка прокрутки родительской панели при работе с combobox.
"""
import tkinter as tk
from config.settings import COLORS, FONTS, SIZES


class AutocompleteCombobox(tk.Frame):
    """Combobox с автодополнением и собственным popup-списком."""
    
    def __init__(self, parent, values=None, font=None, height=10, **kwargs):
        super().__init__(parent, **kwargs)
        self._values = list(values) if values else []
        self._filtered_values = list(self._values)
        self._popup = None
        self._listbox = None
        self._select_callback = None
        self._text_change_callbacks = []
        self._font = font or FONTS['field']
        self._height = height
        
        # Поле ввода
        self.entry = tk.Entry(
            self,
            font=self._font,
            relief=tk.SOLID,
            bd=1,
            justify='left'
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=SIZES['field_ipady'])
        
        # Кнопка со стрелкой
        self.btn = tk.Button(
            self,
            text="▼",
            font=self._font,
            command=self._toggle_popup,
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            relief=tk.SOLID,
            bd=1,
            width=2,
            cursor='hand2'
        )
        self.btn.pack(side=tk.RIGHT, padx=(3, 0))
        
        # Привязка событий
        self.entry.bind('<KeyRelease>', self._on_keyrelease)
        self.entry.bind('<Down>', self._on_down_key)
        self.entry.bind('<Up>', self._on_up_key)
        self.entry.bind('<Return>', self._on_enter_key)
        self.entry.bind('<Escape>', self._close_popup)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        
        # [НОВОЕ] Блокируем прокрутку колесом на entry и btn,
        # чтобы не прокручивалась родительская панель
        self.entry.bind('<MouseWheel>', self._block_mousewheel)
        self.btn.bind('<MouseWheel>', self._block_mousewheel)
        self.bind('<MouseWheel>', self._block_mousewheel)
    
    # [НОВОЕ] Блокировка прокрутки
    def _block_mousewheel(self, event):
        """Блокировать прокрутку колесом мыши, чтобы не прокручивался родитель"""
        # Если открыт popup — прокручиваем список в popup
        if self._popup and self._popup.winfo_exists() and self._listbox:
            self._listbox.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        # Возвращаем 'break' чтобы событие не всплывало до родителя
        return 'break'
    
    # ===== Публичные методы =====
    def get(self):
        return self.entry.get()
    
    def set(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self._notify_text_change()
    
    def clear(self):
        self.entry.delete(0, tk.END)
        self._close_popup()
        self._notify_text_change()
    
    def set_values(self, values):
        self._values = list(values)
        self._filtered_values = list(self._values)
    
    def bind_select(self, callback):
        self._select_callback = callback
    
    def bind_text_change(self, callback):
        """Привязать внешнюю функцию к событию изменения текста."""
        self._text_change_callbacks.append(callback)
    
    def focus_set(self):
        self.entry.focus_set()
    
    def _notify_text_change(self):
        for callback in self._text_change_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Ошибка в обработчике изменения текста: {e}")
    
    # ===== Обработчики событий =====
    def _on_keyrelease(self, event):
        if event.keysym in (
            'Up', 'Down', 'Left', 'Right',
            'Return', 'Escape', 'Tab',
            'Shift_L', 'Shift_R',
            'Control_L', 'Control_R',
            'Alt_L', 'Alt_R',
            'Caps_Lock', 'Super_L', 'Super_R',
            'Num_Lock', 'Scroll_Lock'
        ):
            return
        value = self.entry.get()
        if not value:
            self._filtered_values = list(self._values)
        else:
            self._filtered_values = [
                v for v in self._values
                if value.lower() in v.lower()
            ]
        if self._filtered_values:
            self._show_popup()
        else:
            self._close_popup()
        self._notify_text_change()
    
    def _on_down_key(self, event):
        if self._listbox and self._popup and self._popup.winfo_exists():
            selection = self._listbox.curselection()
            if not selection:
                self._listbox.selection_set(0)
                self._listbox.activate(0)
            else:
                idx = selection[0]
                if idx < self._listbox.size() - 1:
                    self._listbox.selection_clear(0, tk.END)
                    self._listbox.selection_set(idx + 1)
                    self._listbox.activate(idx + 1)
                    self._listbox.see(idx + 1)
            return 'break'
    
    def _on_up_key(self, event):
        if self._listbox and self._popup and self._popup.winfo_exists():
            selection = self._listbox.curselection()
            if selection:
                idx = selection[0]
                if idx > 0:
                    self._listbox.selection_clear(0, tk.END)
                    self._listbox.selection_set(idx - 1)
                    self._listbox.activate(idx - 1)
                    self._listbox.see(idx - 1)
            return 'break'
    
    def _on_enter_key(self, event):
        if self._listbox and self._popup and self._popup.winfo_exists():
            selection = self._listbox.curselection()
            if selection:
                value = self._listbox.get(selection[0])
                self._select_value(value)
                return 'break'
    
    def _on_focus_out(self, event):
        self.after(200, self._check_and_close)
    
    def _check_and_close(self):
        if not self._popup or not self._popup.winfo_exists():
            return
        try:
            focused = self.winfo_toplevel().focus_get()
            if focused != self.entry and focused != self.btn:
                if self._listbox and focused != self._listbox:
                    current = focused
                    is_in_popup = False
                    while current:
                        if current == self._popup:
                            is_in_popup = True
                            break
                        try:
                            current = current.master
                        except (AttributeError, tk.TclError):
                            break
                    if not is_in_popup:
                        self._close_popup()
        except tk.TclError:
            pass
    
    def _toggle_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
        else:
            value = self.entry.get()
            if not value:
                self._filtered_values = list(self._values)
            else:
                self._filtered_values = [
                    v for v in self._values
                    if value.lower() in v.lower()
                ]
            if self._filtered_values:
                self._show_popup()
            self.entry.focus_set()
    
    # ===== Работа с popup =====
    def _show_popup(self):
        if not self._filtered_values:
            self._close_popup()
            return
        if self._popup and self._popup.winfo_exists():
            self._update_listbox()
            return
        
        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.configure(bg=COLORS['panel_bg'])
        self.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = max(self.entry.winfo_width(), 100)
        visible_items = min(len(self._filtered_values), self._height)
        item_height = 22
        height = visible_items * item_height + 4
        self._popup.wm_geometry(f"{width}x{height}+{x}+{y}")
        
        list_frame = tk.Frame(self._popup, bg=COLORS['panel_bg'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._listbox = tk.Listbox(
            list_frame,
            font=self._font,
            selectmode=tk.SINGLE,
            activestyle='dotbox',
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text'],
            selectbackground=COLORS['button_primary'],
            selectforeground=COLORS['button_text'],
            highlightthickness=0,
            borderwidth=1,
            relief=tk.SOLID,
            yscrollcommand=scrollbar.set
        )
        self._listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._listbox.yview)
        
        self._update_listbox()
        
        self._listbox.bind('<Double-Button-1>', self._on_listbox_double_click)
        self._listbox.bind('<Motion>', self._on_listbox_motion)
        
        # [НОВОЕ] Блокируем прокрутку на popup — чтобы не прокручивался родитель
        self._popup.bind('<MouseWheel>', self._block_mousewheel)
        self._listbox.bind('<MouseWheel>', self._on_listbox_mousewheel)
    
    # [НОВОЕ] Прокрутка списка в popup
    def _on_listbox_mousewheel(self, event):
        """Прокрутить список в popup"""
        if self._listbox:
            self._listbox.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        return 'break'
    
    def _update_listbox(self):
        if not self._listbox:
            return
        self._listbox.delete(0, tk.END)
        for value in self._filtered_values:
            self._listbox.insert(tk.END, value)
        if self._popup and self._popup.winfo_exists():
            visible_items = min(len(self._filtered_values), self._height)
            item_height = 22
            height = visible_items * item_height + 4
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height()
            width = max(self.entry.winfo_width(), 100)
            self._popup.wm_geometry(f"{width}x{height}+{x}+{y}")
    
    def _close_popup(self, event=None):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        self._listbox = None
    
    def _on_listbox_double_click(self, event):
        selection = self._listbox.curselection()
        if selection:
            value = self._listbox.get(selection[0])
            self._select_value(value)
    
    def _on_listbox_motion(self, event):
        try:
            index = self._listbox.nearest(event.y)
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(index)
            self._listbox.activate(index)
        except tk.TclError:
            pass
    
    def _select_value(self, value):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self._close_popup()
        if self._select_callback:
            self._select_callback(value)
        self._notify_text_change()
    
    def set_disabled(self, disabled, placeholder_text=None):
        """Включить/выключить поле ввода."""
        if disabled:
            if placeholder_text:
                self.entry.config(state='normal')
                self.entry.delete(0, tk.END)
                self.entry.insert(0, placeholder_text)
            self.entry.config(state='disabled', fg=COLORS['work_area_text'])
            self.btn.config(state='disabled')
        else:
            self.entry.config(state='normal', fg=COLORS['title_text'])
            self.btn.config(state='normal')
            if placeholder_text is not None:
                self.entry.delete(0, tk.END)


def setup_combobox_autocomplete(combobox, values):
    """УСТАРЕЛА. Используйте класс AutocompleteCombobox."""
    import warnings
    warnings.warn(
        "setup_combobox_autocomplete устарела. Используйте AutocompleteCombobox.",
        DeprecationWarning,
        stacklevel=2
    )