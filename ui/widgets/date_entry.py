"""
Кастомный виджет выбора даты (календарь).

Логика работы:
- Поле ввода изначально пустое
- Клик на поле ввода НЕ открывает календарь (можно редактировать вручную)
- Клик на кнопку 📅 открывает/закрывает календарь
- При получении фокуса полем ввода календарь закрывается (если был открыт)
- При выборе даты в календаре она записывается в поле, календарь закрывается
- Текущая дата подсвечивается светло-серым цветом
"""
import tkinter as tk
from datetime import datetime
import calendar
from config.settings import COLORS, FONTS, SIZES


class DateEntry(tk.Frame):
    """Виджет выбора даты с popup-календарём"""
    
    def __init__(self, parent, date_format='%d.%m.%Y', **kwargs):
        super().__init__(parent, **kwargs)
        self.date_format = date_format
        self.selected_date = None
        self.popup = None
        
        # Поле ввода с кнопкой
        self.entry = tk.Entry(
            self,
            font=FONTS['field'],
            width=12,
            relief=tk.SOLID,
            bd=1,
            justify='left'
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=SIZES['field_ipady'])
        
        # При получении фокуса полем ввода — закрываем календарь (если открыт)
        self.entry.bind('<FocusIn>', self._on_entry_focus_in)
        
        # Кнопка 📅 — открывает/закрывает календарь
        self.btn = tk.Button(
            self,
            text="📅",
            font=FONTS['field'],
            command=self._toggle_popup,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=5,
            cursor='hand2'
        )
        self.btn.pack(side=tk.RIGHT, padx=(3, 0))
        self.btn.bind('<Enter>', lambda e: self.btn.config(bg=COLORS['button_primary_hover']))
        self.btn.bind('<Leave>', lambda e: self.btn.config(bg=COLORS['button_primary']))
    
    # ===== Публичные методы =====
    
    def get_date(self):
        """Получить выбранную дату в формате строки (может быть пустой)"""
        return self.entry.get().strip()
    
    def set_date(self, date_str):
        """Установить дату из строки"""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, date_str)
        try:
            self.selected_date = datetime.strptime(date_str, self.date_format)
        except ValueError:
            self.selected_date = None
    
    def clear(self):
        """Очистить поле даты"""
        self.entry.delete(0, tk.END)
        self.selected_date = None
    
    def get_date_object(self):
        """Получить дату как datetime объект (None если не выбрана)"""
        try:
            return datetime.strptime(self.entry.get().strip(), self.date_format)
        except ValueError:
            return None
    
    # ===== Обработчики событий =====
    
    def _on_entry_focus_in(self, event):
        """При получении фокуса полем ввода — закрываем календарь"""
        if self.popup and self.popup.winfo_exists():
            self._close_popup()
    
    def _toggle_popup(self):
        """Открыть/закрыть календарь по кнопке 📅"""
        if self.popup and self.popup.winfo_exists():
            self._close_popup()
        else:
            self._show_popup()
    
    # ===== Работа с popup =====
    
    def _show_popup(self):
        """Показать popup с календарём"""
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
        
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 2
        
        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True)
        self.popup.wm_geometry(f"+{x}+{y}")
        self.popup.configure(bg=COLORS['panel_bg'])
        
        # Определяем отображаемый месяц/год
        if self.selected_date is None:
            today = datetime.now()
            self.view_year = today.year
            self.view_month = today.month
        else:
            self.view_year = self.selected_date.year
            self.view_month = self.selected_date.month
        
        self._build_calendar()
        
        # Закрытие по Escape
        self.popup.bind('<Escape>', lambda e: self._close_popup())
        # Возвращаем фокус на поле ввода
        self.entry.focus_set()
    
    def _close_popup(self):
        """Закрыть popup"""
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
            self.popup = None
    
    def _build_calendar(self):
        """Построить календарь"""
        for widget in self.popup.winfo_children():
            widget.destroy()
        
        # Заголовок с навигацией
        header = tk.Frame(self.popup, bg=COLORS['panel_bg'])
        header.pack(fill=tk.X, padx=5, pady=5)
        
        prev_btn = tk.Button(
            header, text="◀", font=FONTS['field'],
            command=self._prev_month,
            bg=COLORS['panel_bg'], relief=tk.FLAT, cursor='hand2'
        )
        prev_btn.pack(side=tk.LEFT)
        
        month_names = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        title = tk.Label(
            header,
            text=f"{month_names[self.view_month - 1]} {self.view_year}",
            font=FONTS['calendar_header'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        title.pack(side=tk.LEFT, expand=True)
        
        next_btn = tk.Button(
            header, text="▶", font=FONTS['field'],
            command=self._next_month,
            bg=COLORS['panel_bg'], relief=tk.FLAT, cursor='hand2'
        )
        next_btn.pack(side=tk.RIGHT)
        
        # Дни недели
        week_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        week_frame = tk.Frame(self.popup, bg=COLORS['panel_bg'])
        week_frame.pack(fill=tk.X, padx=5)
        
        for i, day in enumerate(week_days):
            color = COLORS['calendar_weekend'] if i >= 5 else COLORS['title_text']
            lbl = tk.Label(
                week_frame, text=day,
                font=FONTS['calendar_header'],
                bg=COLORS['panel_bg'],
                fg=color,
                width=4
            )
            lbl.grid(row=0, column=i, padx=1, pady=2)
        
        # Сетка дней
        days_frame = tk.Frame(self.popup, bg=COLORS['panel_bg'])
        days_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        cal = calendar.monthcalendar(self.view_year, self.view_month)
        today = datetime.now().date()
        
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    lbl = tk.Label(
                        days_frame, text="",
                        width=4, height=1,
                        bg=COLORS['panel_bg']
                    )
                else:
                    current_date = datetime(self.view_year, self.view_month, day).date()
                    
                    # Определяем цвет дня
                    # Приоритет: выбранная дата > текущая дата > выходные > обычный день
                    if self.selected_date is not None and current_date == self.selected_date.date():
                        bg_color = COLORS['calendar_selected']
                        fg_color = COLORS['button_text']
                    elif current_date == today:
                        bg_color = COLORS['calendar_today']      # Светло-серый
                        fg_color = COLORS['calendar_today_fg']   # Тёмный текст
                    elif col_idx >= 5:
                        bg_color = COLORS['panel_bg']
                        fg_color = COLORS['calendar_weekend']
                    else:
                        bg_color = COLORS['panel_bg']
                        fg_color = COLORS['title_text']
                    
                    lbl = tk.Label(
                        days_frame, text=str(day),
                        font=FONTS['calendar_day'],
                        bg=bg_color,
                        fg=fg_color,
                        width=4, height=1,
                        relief=tk.FLAT,
                        cursor='hand2'
                    )
                    lbl.bind('<Button-1>', lambda e, d=day: self._select_day(d))
                    lbl.bind('<Enter>', lambda e, l=lbl, bg=bg_color: self._on_day_enter(l, bg))
                    lbl.bind('<Leave>', lambda e, l=lbl, bg=bg_color: self._on_day_leave(l, bg))
                
                lbl.grid(row=row_idx, column=col_idx, padx=1, pady=1)
        
        # Кнопка "Сегодня"
        today_btn = tk.Button(
            self.popup, text="Сегодня",
            font=FONTS['menu'],
            command=self._select_today,
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=10, pady=3,
            cursor='hand2'
        )
        today_btn.pack(pady=(0, 5))
    
    def _on_day_enter(self, label, original_bg):
        """Эффект при наведении на день"""
        if label['bg'] not in [COLORS['calendar_selected'], COLORS['calendar_today']]:
            label.config(bg='#d5dbdb')
    
    def _on_day_leave(self, label, original_bg):
        """Эффект при уходе курсора с дня"""
        if label['bg'] == '#d5dbdb':
            label.config(bg=original_bg)
    
    def _select_day(self, day):
        """Выбрать день — записать в поле и закрыть календарь"""
        self.selected_date = datetime(self.view_year, self.view_month, day)
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.selected_date.strftime(self.date_format))
        self._close_popup()
    
    def _select_today(self):
        """Выбрать сегодняшнюю дату и закрыть календарь"""
        self.selected_date = datetime.now()
        self.view_year = self.selected_date.year
        self.view_month = self.selected_date.month
        self.entry.delete(0, tk.END)
        self.entry.insert(0, self.selected_date.strftime(self.date_format))
        self._close_popup()
    
    def _prev_month(self):
        """Перейти к предыдущему месяцу"""
        if self.view_month == 1:
            self.view_month = 12
            self.view_year -= 1
        else:
            self.view_month -= 1
        self._build_calendar()
    
    def _next_month(self):
        """Перейти к следующему месяцу"""
        if self.view_month == 12:
            self.view_month = 1
            self.view_year += 1
        else:
            self.view_month += 1
        self._build_calendar()