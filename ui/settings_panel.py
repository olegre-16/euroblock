"""
Панель настроек программы
"""
import tkinter as tk
from config.settings import COLORS, FONTS, PADDING, SIZES

from ui.windows.payment_type_window import PaymentTypeWindow
from ui.windows.materials_window import MaterialsWindow
from ui.windows.purposes_window import PurposesWindow
from ui.windows.equipment_window import EquipmentWindow
from ui.windows.payers_window import PayersWindow
from ui.windows.customers_window import CustomersWindow
from ui.windows.suppliers_window import SuppliersWindow
from ui.windows.products_window import ProductsWindow
from ui.windows.cement_silos_window import CementSilosWindow
from ui.windows.colors_window import ColorsWindow


class SettingsPanel:
    def __init__(self, parent, on_exit_callback, on_open_window_callback=None, on_close_window_callback=None):
        self.parent = parent
        self.on_exit_callback = on_exit_callback
        self.on_open_window_callback = on_open_window_callback
        self.on_close_window_callback = on_close_window_callback
        
        self.current_window = None
        self.settings_buttons = []
        
        self.settings_frame = tk.Frame(parent, bg=COLORS['background'])
        
        self.title_label = tk.Label(
            self.settings_frame,
            text="Настройки",
            font=FONTS['section_title'],
            bg=COLORS['background'],
            fg=COLORS['title_text']
        )
        self.title_label.pack(pady=(20, 0), anchor='w', padx=20)
        
        separator = tk.Frame(self.settings_frame, height=2, bg=COLORS['button_primary'])
        separator.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        self.content_frame = tk.Frame(self.settings_frame, bg=COLORS['background'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.left_panel = tk.Frame(
            self.content_frame, 
            bg=COLORS['panel_bg'], 
            relief=tk.RAISED, 
            bd=SIZES['panel_border']
        )
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        
        buttons = [
            "Вид оплаты",
            "Материалы и услуги",
            "Назначение",
            "Оборудование",
            "Плательщик",
            "Покупатель",
            "Поставщик",
            "Продукция",
            "Силос цемента",
            "Цвет"
        ]
        
        max_length = max(len(btn) for btn in buttons)
        button_width = max_length + SIZES['button_width_extra']
        
        self.button_frame = tk.Frame(self.left_panel, bg=COLORS['panel_bg'])
        self.button_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING['button_x'], pady=PADDING['button_x'])
        
        for btn_text in buttons:
            btn = tk.Button(
                self.button_frame,
                text=btn_text,
                font=FONTS['menu'],
                width=button_width,
                anchor='w',
                command=lambda b=btn_text: self.show_setting(b),
                bg=COLORS['button_primary'],
                fg=COLORS['button_text'],
                relief=tk.FLAT,
                padx=PADDING['button_x'],
                pady=PADDING['button_y']
            )
            btn.pack(fill=tk.X, pady=PADDING['button_spacing'])
            btn.bind('<Enter>', lambda e, b=btn: self._on_enter(b))
            btn.bind('<Leave>', lambda e, b=btn: self._on_leave(b))
            self.settings_buttons.append(btn)
        
        self.exit_frame = tk.Frame(self.left_panel, bg=COLORS['panel_bg'])
        self.exit_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=PADDING['button_x'], pady=PADDING['button_x'])
        
        self.exit_btn = tk.Button(
            self.exit_frame,
            text="Выход",
            font=FONTS['menu'],
            width=button_width,
            anchor='w',
            command=self.on_exit_callback,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y']
        )
        self.exit_btn.pack(fill=tk.X)
        self.exit_btn.bind('<Enter>', lambda e: self._on_exit_enter())
        self.exit_btn.bind('<Leave>', lambda e: self._on_exit_leave())
        
        self.work_area = tk.Frame(
            self.content_frame, 
            bg=COLORS['panel_bg'], 
            relief=tk.RAISED, 
            bd=SIZES['panel_border']
        )
        self.work_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.show_welcome()
    
    def _on_enter(self, btn):
        if str(btn['state']) != 'disabled':
            btn.config(bg=COLORS['button_primary_hover'])
    
    def _on_leave(self, btn):
        if str(btn['state']) != 'disabled':
            btn.config(bg=COLORS['button_primary'])
    
    def _on_exit_enter(self):
        if str(self.exit_btn['state']) != 'disabled':
            self.exit_btn.config(bg=COLORS['button_settings_hover'])
    
    def _on_exit_leave(self):
        if str(self.exit_btn['state']) != 'disabled':
            self.exit_btn.config(bg=COLORS['button_settings'])
    
    def disable_buttons(self):
        for btn in self.settings_buttons:
            btn.config(state='disabled', bg=COLORS['button_disabled'])
    
    def enable_buttons(self):
        for btn in self.settings_buttons:
            btn.config(state='normal', bg=COLORS['button_primary'])
    
    def disable_exit_button(self):
        self.exit_btn.config(state='disabled', bg=COLORS['button_disabled'])
    
    def enable_exit_button(self):
        self.exit_btn.config(state='normal', bg=COLORS['button_settings'])
    
    def disable_all(self):
        self.disable_buttons()
        self.disable_exit_button()
    
    def enable_all(self):
        self.enable_buttons()
        self.enable_exit_button()
    
    def get_frame(self):
        return self.settings_frame
    
    def clear_work_area(self):
        for widget in self.work_area.winfo_children():
            widget.destroy()
        self.current_window = None
    
    def show_welcome(self):
        self.clear_work_area()
        welcome_label = tk.Label(
            self.work_area,
            text="Выберите раздел из меню слева",
            font=FONTS['work_area'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text']
        )
        welcome_label.pack(expand=True)
    
    def show_setting(self, setting_name):
        """Показать содержимое раздела настроек"""
        self.clear_work_area()
        
        self.disable_all()
        if self.on_open_window_callback:
            self.on_open_window_callback()
        
        # Словарь соответствия кнопок и классов окон
        window_classes = {
            "Вид оплаты": PaymentTypeWindow,
            "Материалы и услуги": MaterialsWindow,
            "Назначение": PurposesWindow,
            "Оборудование": EquipmentWindow,
            "Плательщик": PayersWindow,
            "Покупатель": CustomersWindow,
            "Поставщик": SuppliersWindow,
            "Продукция": ProductsWindow,
            "Силос цемента": CementSilosWindow,
            "Цвет": ColorsWindow,
        }
        
        if setting_name in window_classes:
            window_class = window_classes[setting_name]
            self.current_window = window_class(self.work_area, self.hide_current_window)
            self.current_window.get_frame().pack(fill=tk.BOTH, expand=True)
        else:
            self._show_placeholder(setting_name)
    
    def _show_placeholder(self, name):
        """Показать заглушку для раздела"""
        title_label = tk.Label(
            self.work_area,
            text=name,
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        )
        title_label.pack(pady=20, anchor='w', padx=20)
        
        separator = tk.Frame(self.work_area, height=2, bg=COLORS['button_primary'])
        separator.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        content = tk.Label(
            self.work_area,
            text=f"Раздел \"{name}\" находится в разработке",
            font=FONTS['work_area'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text']
        )
        content.pack(expand=True)
    
    def hide_current_window(self):
        """Закрыть текущее окно и разблокировать все кнопки"""
        self.clear_work_area()
        self.enable_all()
        if self.on_close_window_callback:
            self.on_close_window_callback()
        self.show_welcome()