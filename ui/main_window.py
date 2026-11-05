"""
Главное окно программы "ООО Евроблок".
[ИЗМЕНЕНО] В заголовке окна отображается режим работы (СЕТЬ/СЕРВЕР/локальный).
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from config.settings import COLORS, FONTS, PADDING, SIZES
from ui.settings_panel import SettingsPanel
from ui.windows.cement_receipt_window import CementReceiptWindow
from ui.windows.production_window import ProductionWindow
from ui.windows.reserved_products_window import ReservedProductsWindow
from ui.windows.sales_window import SalesWindow
from ui.windows.cash_window import CashWindow
from ui.windows.general_expenses_window import GeneralExpensesWindow
from ui.windows.cement_report_window import CementReportWindow
from ui.windows.expenses_report_window import ExpensesReportWindow
from ui.windows.sales_report_window import SalesReportWindow
from ui.windows.production_report_window import ProductionReportWindow
from ui.windows.inert_materials_window import InertMaterialsWindow
from database.repositories import (
    products_repo, production_repo, warehouse_repo,
    cement_silos_repo, cement_receipts_repo, reserved_products_repo,
    adjustment_repo, sales_repo, cash_repo, general_expenses_repo
)
from ui.widgets.silo_canvas import SiloCanvas
from utils.resources import load_logo, set_window_icon


class EuroblockApp:
    def __init__(self, root, logo_image=None):
        self.root = root
        
        # [НОВОЕ] Определяем режим работы для заголовка
        try:
            from client_config import MODE, NETWORK_DB_PATH
            if MODE == 'network':
                db_name = os.path.basename(NETWORK_DB_PATH) if NETWORK_DB_PATH else 'сеть'
                self.root.title(f"ООО Евроблок - производство и финансы [СЕТЬ: {db_name}]")
            elif MODE == 'server':
                self.root.title("ООО Евроблок - производство и финансы [СЕРВЕР]")
            else:
                self.root.title("ООО Евроблок - производство и финансы")
        except ImportError:
            self.root.title("ООО Евроблок - производство и финансы")
        
        self.root.state('zoomed')
        self.root.configure(bg=COLORS['background'])
        
        # ===== УСТАНОВКА ИКОНКИ ОКНА =====
        set_window_icon(root, logo_image)
        
        # ===== ГЛОБАЛЬНАЯ НАСТРОЙКА СТИЛЕЙ TTK =====
        style = ttk.Style()
        style.configure('TCombobox', font=FONTS['field'])
        style.configure('TCombobox', padding=(5, SIZES['field_ipady'], 5, SIZES['field_ipady']))
        self.root.option_add('*TCombobox*Listbox.font', FONTS['field'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', COLORS['button_primary'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', COLORS['button_text'])
        style.configure('Treeview', font=FONTS['table_cell'], rowheight=25)
        style.configure('Treeview.Heading', font=FONTS['table_heading'])
        
        self.current_settings_panel = None
        self.current_window = None
        self.main_buttons = []
        
        # ===== МАСШТАБИРОВАНИЕ ЛОГОТИПА =====
        self.logo_image = None
        if logo_image is not None:
            import tkinter.font as tkfont
            title_font = tkfont.Font(root, font=FONTS['title'])
            subtitle_font = tkfont.Font(root, font=FONTS['subtitle'])
            title_height = title_font.metrics('linespace')
            subtitle_height = subtitle_font.metrics('linespace')
            total_height = title_height + PADDING['title_subtitle'] + subtitle_height
            self.logo_image = self._resize_logo(logo_image, total_height)
        
        # Главный контейнер
        self.main_frame = tk.Frame(root, bg=COLORS['background'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ===== ЗАГОЛОВОК С ЛОГОТИПОМ =====
        self.title_frame = tk.Frame(self.main_frame, bg=COLORS['background'])
        self.title_frame.pack(fill=tk.X, padx=PADDING['main'], pady=PADDING['main'])
        
        if self.logo_image:
            logo_container = tk.Frame(self.title_frame, bg=COLORS['background'])
            logo_container.pack(side=tk.LEFT, padx=(0, 15))
            logo_label = tk.Label(
                logo_container,
                image=self.logo_image,
                bg=COLORS['background']
            )
            logo_label.pack(anchor='w')
            
            text_container = tk.Frame(self.title_frame, bg=COLORS['background'])
            text_container.pack(side=tk.LEFT, fill=tk.Y)
            
            self.title_label = tk.Label(
                text_container,
                text="ООО Евроблок",
                font=FONTS['title'],
                bg=COLORS['background'],
                fg=COLORS['title_text']
            )
            self.title_label.pack(anchor='w')
            
            self.subtitle_label = tk.Label(
                text_container,
                text="производство и финансы",
                font=FONTS['subtitle'],
                bg=COLORS['background'],
                fg=COLORS['subtitle_text']
            )
            self.subtitle_label.pack(anchor='w', pady=(PADDING['title_subtitle'], 0))
        else:
            self.title_label = tk.Label(
                self.title_frame,
                text="ООО Евроблок",
                font=FONTS['title'],
                bg=COLORS['background'],
                fg=COLORS['title_text']
            )
            self.title_label.pack(anchor='w')
            
            self.subtitle_label = tk.Label(
                self.title_frame,
                text="производство и финансы",
                font=FONTS['subtitle'],
                bg=COLORS['background'],
                fg=COLORS['subtitle_text']
            )
            self.subtitle_label.pack(anchor='w', pady=(PADDING['title_subtitle'], 0))
        
        # Контейнер для панели и рабочей области
        self.content_frame = tk.Frame(self.main_frame, bg=COLORS['background'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING['main'], pady=(0, PADDING['main']))
        
        # Левая панель с кнопками
        self.left_panel = tk.Frame(
            self.content_frame, 
            bg=COLORS['panel_bg'], 
            relief=tk.RAISED, 
            bd=SIZES['panel_border']
        )
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, PADDING['main']))
        
        main_buttons_list = [
            "Поступление цемента",
            "Производство продукции",
            "Продукция в резерве",
            "Реализация продукции",
            "Касса",
            "Расходы общие",
            "Отчет по цементу",
            "Отчет по расходам",
            "Отчет по реализации",
            "Отчет по производству продукции",
            "Расход инертных материалов"
        ]
        
        max_length = max(len(btn) for btn in main_buttons_list + ["Выход из программы"])
        button_width = max_length + SIZES['button_width_extra']
        
        self.button_frame = tk.Frame(self.left_panel, bg=COLORS['panel_bg'])
        self.button_frame.pack(fill=tk.BOTH, expand=True, padx=PADDING['button_x'], pady=PADDING['button_x'])
        
        for btn_text in main_buttons_list:
            btn = tk.Button(
                self.button_frame,
                text=btn_text,
                font=FONTS['menu'],
                width=button_width,
                anchor='w',
                command=lambda b=btn_text: self.show_section(b),
                bg=COLORS['button_primary'],
                fg=COLORS['button_text'],
                relief=tk.FLAT,
                padx=PADDING['button_x'],
                pady=PADDING['button_y']
            )
            btn.pack(fill=tk.X, pady=PADDING['button_spacing'])
            btn.bind('<Enter>', lambda e, b=btn: self._on_main_enter(b))
            btn.bind('<Leave>', lambda e, b=btn: self._on_main_leave(b))
            self.main_buttons.append(btn)
        
        # Кнопка "Выход из программы"
        self.exit_main_frame = tk.Frame(self.left_panel, bg=COLORS['panel_bg'])
        self.exit_main_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=PADDING['button_x'], pady=(PADDING['exit_spacing_top'], PADDING['button_x']))
        
        self.exit_main_btn = tk.Button(
            self.exit_main_frame,
            text="Выход из программы",
            font=FONTS['menu'],
            width=button_width,
            anchor='w',
            command=self.exit_program,
            bg=COLORS['button_settings'],
            fg=COLORS['button_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y'],
            cursor='hand2'
        )
        self.exit_main_btn.pack(fill=tk.X)
        self.exit_main_btn.bind('<Enter>', lambda e: self._on_exit_main_enter())
        self.exit_main_btn.bind('<Leave>', lambda e: self._on_exit_main_leave())
        self.main_buttons.append(self.exit_main_btn)
        
        # Кнопка "Настройки"
        self.settings_frame = tk.Frame(self.left_panel, bg=COLORS['panel_bg'])
        self.settings_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=PADDING['button_x'], pady=(0, PADDING['button_x']))
        
        self.settings_btn = tk.Button(
            self.settings_frame,
            text="Настройки",
            font=FONTS['menu'],
            width=button_width,
            anchor='w',
            command=self.show_settings,
            bg=COLORS['button_import'],
            fg=COLORS['title_text'],
            relief=tk.FLAT,
            padx=PADDING['button_x'],
            pady=PADDING['button_y']
        )
        self.settings_btn.pack(fill=tk.X)
        self.settings_btn.bind('<Enter>', lambda e: self.settings_btn.config(bg=COLORS['button_import_hover']))
        self.settings_btn.bind('<Leave>', lambda e: self.settings_btn.config(bg=COLORS['button_import']))
        
        # Рабочая область
        self.work_area = tk.Frame(
            self.content_frame, 
            bg=COLORS['panel_bg'], 
            relief=tk.RAISED, 
            bd=SIZES['panel_border']
        )
        self.work_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.show_welcome()
    
    def _resize_logo(self, image, target_height):
        """Масштабировать логотип пропорционально"""
        if image is None:
            return None
        orig_height = image.height()
        if orig_height == 0 or target_height <= 0:
            return image
        if abs(orig_height - target_height) <= 2:
            return image
        ratio = target_height / orig_height
        best_diff = float('inf')
        best_zoom = 1
        best_subsample = 1
        for subsample in range(1, 30):
            zoom = max(1, round(ratio * subsample))
            actual_ratio = zoom / subsample
            diff = abs(actual_ratio - ratio)
            if diff < best_diff:
                best_diff = diff
                best_zoom = zoom
                best_subsample = subsample
                if diff < 0.01:
                    break
        try:
            return image.zoom(best_zoom, best_zoom).subsample(best_subsample, best_subsample)
        except tk.TclError:
            return image
    
    def _on_main_enter(self, btn):
        if str(btn['state']) != 'disabled':
            btn.config(bg=COLORS['button_primary_hover'])
    
    def _on_main_leave(self, btn):
        if str(btn['state']) != 'disabled':
            btn.config(bg=COLORS['button_primary'])
    
    def _on_exit_main_enter(self):
        if str(self.exit_main_btn['state']) != 'disabled':
            self.exit_main_btn.config(bg=COLORS['button_settings_hover'])
    
    def _on_exit_main_leave(self):
        if str(self.exit_main_btn['state']) != 'disabled':
            self.exit_main_btn.config(bg=COLORS['button_settings'])
    
    def disable_main_buttons(self):
        for btn in self.main_buttons:
            btn.config(state='disabled', bg=COLORS['button_disabled'])
        self.settings_btn.config(state='disabled', bg=COLORS['button_disabled'])
    
    def enable_main_buttons(self):
        for btn in self.main_buttons:
            if btn == self.exit_main_btn:
                btn.config(state='normal', bg=COLORS['button_settings'])
            else:
                btn.config(state='normal', bg=COLORS['button_primary'])
        self.settings_btn.config(state='normal', bg=COLORS['button_import'])
    
    def clear_work_area(self):
        for widget in self.work_area.winfo_children():
            widget.destroy()
        self.current_settings_panel = None
    
    def _destroy_current_window_safely(self):
        """Безопасно уничтожить текущее открытое окно."""
        if self.current_window is not None:
            try:
                window = None
                if hasattr(self.current_window, 'window'):
                    window = self.current_window.window
                elif hasattr(self.current_window, 'main_frame'):
                    toplevel = self.current_window.main_frame.winfo_toplevel()
                    if str(toplevel) != str(self.root):
                        window = toplevel
                
                if window is not None and window.winfo_exists():
                    try:
                        window.grab_release()
                    except tk.TclError:
                        pass
                    window.destroy()
            except tk.TclError:
                pass
            except Exception as e:
                print(f"⚠ Ошибка закрытия окна: {e}")
            finally:
                self.current_window = None
    
    def show_welcome(self):
        """Показать приветственную рабочую область с тремя блоками"""
        self.clear_work_area()
        
        welcome_container = tk.Frame(self.work_area, bg=COLORS['background'])
        welcome_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_half = tk.Frame(welcome_container, bg=COLORS['background'])
        left_half.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_half = tk.Frame(welcome_container, bg=COLORS['background'])
        right_half.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ===== БЛОК 1: Склад =====
        warehouse_frame = tk.Frame(
            left_half,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        warehouse_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            warehouse_frame,
            text="Склад",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        wh_tree_container = tk.Frame(warehouse_frame, bg=COLORS['panel_bg'])
        wh_tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        wh_scrollbar_y = ttk.Scrollbar(wh_tree_container, orient=tk.VERTICAL)
        wh_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.warehouse_tree = ttk.Treeview(
            wh_tree_container,
            columns=('product', 'color', 'stock', 'reserved', 'remaining'),
            show='headings',
            yscrollcommand=wh_scrollbar_y.set,
            selectmode='browse'
        )
        self.warehouse_tree.heading('product', text='Продукция', anchor='w')
        self.warehouse_tree.heading('color', text='Цвет', anchor='w')
        self.warehouse_tree.heading('stock', text='Склад, шт/м2', anchor='w')
        self.warehouse_tree.heading('reserved', text='Резерв, шт/м2', anchor='w')
        self.warehouse_tree.heading('remaining', text='Остаток, шт/м2', anchor='w')
        self.warehouse_tree.column('product', width=240, anchor='w')
        self.warehouse_tree.column('color', width=80, anchor='w')
        self.warehouse_tree.column('stock', width=100, anchor='w')
        self.warehouse_tree.column('reserved', width=100, anchor='w')
        self.warehouse_tree.column('remaining', width=100, anchor='w')
        wh_scrollbar_y.config(command=self.warehouse_tree.yview)
        self.warehouse_tree.pack(fill=tk.BOTH, expand=True)
        self.warehouse_tree.bind('<Double-Button-1>', self._on_warehouse_double_click)
        
        self.load_warehouse_data()
        
        # ===== БЛОК 2: Силоса =====
        silos_frame = tk.Frame(
            right_half,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        silos_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            silos_frame,
            text="Текущий уровень наполнения силосов",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        silos_canvas_container = tk.Frame(silos_frame, bg=COLORS['panel_bg'])
        silos_canvas_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        silos_data = cement_silos_repo.get_all()
        balances = cement_receipts_repo.get_current_balance_by_silo()
        self.silos_canvas = SiloCanvas(
            silos_canvas_container,
            silos_data,
            balances
        )
        self.silos_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # ===== БЛОК 3: Производство продукции =====
        prod_frame = tk.Frame(
            right_half,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        prod_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(
            prod_frame,
            text="Производство продукции",
            font=FONTS['section_title'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        prod_tree_container = tk.Frame(prod_frame, bg=COLORS['panel_bg'])
        prod_tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        prod_scrollbar_y = ttk.Scrollbar(prod_tree_container, orient=tk.VERTICAL)
        prod_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.production_tree = ttk.Treeview(
            prod_tree_container,
            columns=('date', 'equipment', 'product', 'color', 'quantity'),
            show='headings',
            yscrollcommand=prod_scrollbar_y.set,
            selectmode='browse'
        )
        self.production_tree.heading('date', text='Дата', anchor='w')
        self.production_tree.heading('equipment', text='Оборудование', anchor='w')
        self.production_tree.heading('product', text='Продукция', anchor='w')
        self.production_tree.heading('color', text='Цвет', anchor='w')
        self.production_tree.heading('quantity', text='Кол-во, шт/м2', anchor='w')
        self.production_tree.column('date', width=60, anchor='w')
        self.production_tree.column('equipment', width=90, anchor='w')
        self.production_tree.column('product', width=200, anchor='w')
        self.production_tree.column('color', width=80, anchor='w')
        self.production_tree.column('quantity', width=100, anchor='w')
        prod_scrollbar_y.config(command=self.production_tree.yview)
        self.production_tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_production_summary()
    
    def _on_warehouse_double_click(self, event):
        """Открывает окно корректировки остатков при двойном клике"""
        selected = self.warehouse_tree.selection()
        if not selected:
            return
        item = self.warehouse_tree.item(selected[0])
        values = item['values']
        product = values[0]
        color = values[1] if values[1] != '—' else ''
        current_stock_str = str(values[2]).replace(',', '.')
        try:
            current_stock = float(current_stock_str)
        except ValueError:
            current_stock = 0.0
        self._show_adjustment_dialog(product, color, current_stock)
    
    def _show_adjustment_dialog(self, product, color, current_stock):
        """Диалоговое окно корректировки остатков"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Корректировка остатков")
        dialog.configure(bg=COLORS['panel_bg'])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        max_len = max(len(product or ''), len(color or ''), len(str(current_stock)))
        dialog_width = max(400, min(500 + (max_len - 20) * 8, 600))
        dialog_height = 320
        
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        x = root_x + (root_w - dialog_width) // 2
        y = root_y + (root_h - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        tk.Label(
            dialog, 
            text="Корректировка остатков", 
            font=FONTS['section_title'], 
            bg=COLORS['panel_bg'], 
            fg=COLORS['title_text']
        ).pack(pady=(15, 10))
        
        tk.Frame(dialog, height=2, bg=COLORS['button_primary']).pack(fill=tk.X, padx=20, pady=(0, 10))
        
        info_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        info_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        def _add_info_row(label_text, value_text):
            row = tk.Frame(info_frame, bg=COLORS['panel_bg'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(
                row, 
                text=f"{label_text}:", 
                font=FONTS['field'], 
                bg=COLORS['panel_bg'], 
                fg=COLORS['work_area_text'], 
                width=22, 
                anchor='w'
            ).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(
                row, 
                text=value_text, 
                font=FONTS['field'], 
                bg=COLORS['panel_bg'], 
                fg=COLORS['title_text'], 
                anchor='w', 
                justify='left', 
                wraplength=dialog_width - 180
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        _add_info_row("Продукция", product)
        _add_info_row("Цвет", color if color else '—')
        _add_info_row("Текущий остаток", self._format_number(current_stock))
        
        tk.Frame(dialog, height=1, bg=COLORS['work_area_text']).pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(
            dialog, 
            text="Новый остаток (шт/м2):", 
            font=FONTS['menu'], 
            bg=COLORS['panel_bg'], 
            fg=COLORS['title_text']
        ).pack(anchor='w', padx=20, pady=(0, 5))
        
        new_stock_var = tk.StringVar(value=self._format_number(current_stock))
        new_stock_entry = tk.Entry(
            dialog, 
            textvariable=new_stock_var, 
            font=FONTS['field'], 
            relief=tk.SOLID, 
            bd=1, 
            justify='left'
        )
        new_stock_entry.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        def on_save():
            new_val_str = new_stock_var.get().strip().replace(',', '.')
            try:
                new_qty = float(new_val_str)
            except ValueError:
                messagebox.showwarning("Внимание", "Неверный формат количества")
                return
            qty_before = current_stock
            success, old_qty, diff = warehouse_repo.set_stock(product, color, new_qty, qty_before)
            if success:
                today = datetime.now().strftime('%d.%m.%Y')
                adj_success, adj_msg = adjustment_repo.log_adjustment(
                    today, product, color, qty_before, new_qty, diff
                )
                if adj_success:
                    messagebox.showinfo("Успех", "Остатки скорректированы и сохранены в историю")
                    dialog.destroy()
                    self.load_warehouse_data()
                else:
                    messagebox.showerror("Ошибка", f"Склад обновлен, но история не сохранена: {adj_msg}")
            else:
                messagebox.showerror("Ошибка", f"Не удалось обновить данные: {old_qty}")
        
        def on_cancel():
            dialog.grab_release()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS['panel_bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        save_btn = tk.Button(
            btn_frame, 
            text="Сохранить", 
            font=FONTS['menu'], 
            command=on_save, 
            bg=COLORS['button_primary'], 
            fg=COLORS['button_text'], 
            relief=tk.FLAT, 
            padx=15, 
            pady=5, 
            cursor='hand2'
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        save_btn.bind('<Enter>', lambda e: save_btn.config(bg=COLORS['button_primary_hover']))
        save_btn.bind('<Leave>', lambda e: save_btn.config(bg=COLORS['button_primary']))
        
        cancel_btn = tk.Button(
            btn_frame, 
            text="Отмена", 
            font=FONTS['menu'], 
            command=on_cancel, 
            bg=COLORS['button_settings'], 
            fg=COLORS['button_text'], 
            relief=tk.FLAT, 
            padx=15, 
            pady=5, 
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.RIGHT)
        cancel_btn.bind('<Enter>', lambda e: cancel_btn.config(bg=COLORS['button_settings_hover']))
        cancel_btn.bind('<Leave>', lambda e: cancel_btn.config(bg=COLORS['button_settings']))
        
        dialog.bind('<Escape>', lambda e: on_cancel())
        new_stock_entry.focus_set()
        self.root.wait_window(dialog)
    
    def load_warehouse_data(self):
        """Загружает данные в таблицу 'Склад'."""
        for item in self.warehouse_tree.get_children():
            self.warehouse_tree.delete(item)
        
        records = production_repo.get_all()
        all_products = products_repo.get_all()
        volume_map = {row[0]: (row[1] if row[1] else 1) for row in all_products}
        
        stock_grouped = {}
        for row in records:
            product = row[4]
            color = row[5] or ''
            quantity = row[6] or 0
            if not product:
                continue
            calc_qty = (quantity or 0) * volume_map.get(product, 1)
            key = (product.strip(), color.strip())
            stock_grouped[key] = stock_grouped.get(key, 0) + calc_qty
        
        adjustments = adjustment_repo.get_adjustments_sum()
        for key, diff in adjustments.items():
            stock_grouped[key] = stock_grouped.get(key, 0) + diff
        
        sold_from_reserve_sum = reserved_products_repo.get_sold_sum()
        for key, sold_qty in sold_from_reserve_sum.items():
            stock_grouped[key] = stock_grouped.get(key, 0) - sold_qty
        
        direct_sales_sum = sales_repo.get_sales_sum()
        for key, sold_qty in direct_sales_sum.items():
            stock_grouped[key] = stock_grouped.get(key, 0) - sold_qty
        
        reserved_records = reserved_products_repo.get_all_reserved()
        reserved_grouped = {}
        for row in reserved_records:
            product = row[3] or ''
            color = row[4] or ''
            quantity = row[5] or 0
            key = (product.strip(), color.strip())
            reserved_grouped[key] = reserved_grouped.get(key, 0) + quantity
        
        all_keys = (set(stock_grouped.keys()) | 
                   set(reserved_grouped.keys()) | 
                   set(sold_from_reserve_sum.keys()) | 
                   set(direct_sales_sum.keys()) |
                   set(adjustments.keys()))
        
        def sort_key(key):
            product, color = key
            has_brak = 1 if '(брак)' in product else 0
            return (has_brak, product.lower(), color.lower())
        
        for key in sorted(all_keys, key=sort_key):
            product, color = key
            stock_qty = stock_grouped.get(key, 0)
            reserved_qty = reserved_grouped.get(key, 0)
            remaining_qty = stock_qty - reserved_qty
            
            has_activity = (key in sold_from_reserve_sum or 
                          key in direct_sales_sum or 
                          key in adjustments)
            
            if stock_qty == 0 and reserved_qty == 0 and not has_activity:
                continue
            
            self.warehouse_tree.insert(
                '', 'end',
                values=(
                    product,
                    color if color else '—',
                    self._format_number(stock_qty),
                    self._format_number(reserved_qty),
                    self._format_number(remaining_qty)
                )
            )
    
    def load_production_summary(self):
        """Загрузить сводку производства"""
        for item in self.production_tree.get_children():
            self.production_tree.delete(item)
        
        records = production_repo.get_all()
        all_products = products_repo.get_all()
        volume_map = {row[0]: (row[1] if row[1] else 1) for row in all_products}
        
        for row in records:
            product = row[4]
            color = row[5] or ''
            quantity = row[6] or 0
            equipment = row[2] or ''
            date = row[1]
            if not product:
                continue
            calc_qty = (quantity or 0) * volume_map.get(product, 1)
            self.production_tree.insert(
                '', 'end',
                values=(
                    date,
                    equipment,
                    product,
                    color if color else '—',
                    self._format_number(calc_qty)
                )
            )
    
    def _format_number(self, value):
        """Форматировать число"""
        if value is None or value == '':
            return '0'
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:g}"
        except (ValueError, TypeError):
            return str(value)
    
    def show_section(self, section_name):
        """Показать содержимое раздела главного меню."""
        self._destroy_current_window_safely()
        
        all_windows = {
            "Поступление цемента": CementReceiptWindow,
            "Производство продукции": ProductionWindow,
            "Продукция в резерве": ReservedProductsWindow,
            "Реализация продукции": SalesWindow,
            "Касса": CashWindow,
            "Расходы общие": GeneralExpensesWindow,
            "Отчет по цементу": CementReportWindow,
            "Отчет по расходам": ExpensesReportWindow,
            "Отчет по реализации": SalesReportWindow,
            "Отчет по производству продукции": ProductionReportWindow,
            "Расход инертных материалов": InertMaterialsWindow,
        }
        
        if section_name in all_windows:
            self.disable_main_buttons()
            window_class = all_windows[section_name]
            self.root.update_idletasks()
            self.current_window = window_class(self.root, self.hide_current_window)
        else:
            self.clear_work_area()
            self.disable_main_buttons()
            self._show_placeholder(section_name)
    
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
    
    def show_settings(self):
        self._destroy_current_window_safely()
        self.clear_work_area()
        self.disable_main_buttons()
        self.current_settings_panel = SettingsPanel(
            self.work_area, 
            self.hide_settings,
            on_open_window_callback=self._on_settings_window_open,
            on_close_window_callback=self._on_settings_window_close
        )
        self.current_settings_panel.get_frame().pack(fill=tk.BOTH, expand=True)
    
    def _on_settings_window_open(self):
        if self.current_settings_panel:
            self.current_settings_panel.disable_all()
    
    def _on_settings_window_close(self):
        if self.current_settings_panel:
            self.current_settings_panel.enable_all()
    
    def hide_settings(self):
        self.clear_work_area()
        self.enable_main_buttons()
        self.show_welcome()
    
    def hide_current_window(self):
        """Разблокировать кнопки главного меню после закрытия окна"""
        self.current_window = None
        self.clear_work_area()
        self.enable_main_buttons()
        self.show_welcome()
    
    def exit_program(self):
        if messagebox.askyesno("Выход", "Вы действительно хотите выйти из программы?"):
            self.root.destroy()