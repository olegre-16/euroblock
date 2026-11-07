"""
Окно "Отчет по цементу" - отчет о движении цемента по силосам
Оформление идентично окну "Производство продукции".
[ИЗМЕНЕНО]
- Добавлена колонка "Коррекция" в табличную часть
- Остаток корректно рассчитывается с учётом корректировок
- Защита от ошибки распаковки кортежей (поддержка 5 и 6 значений)
- Таблицы создаются для ВСЕХ силосов (даже без данных)
- Используется grid() для равномерного распределения таблиц
- PDF-отчёт в книжной ориентации (A4 portrait)
- В отчёте по конкретному силосу:
  * Даты идут по возрастанию
  * Перед каждой корректировкой — итоги поступлений и расхода
  * После корректировки — накопление начинается заново
  * В конце — общий итог за период (приход, расход, корректировка)
- В отчёте по всем силосам:
  * Добавлена колонка "Расход цемента, кг"
  * 4 колонки: Силос | Поступление | Расход | Корректировка
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import sys
import subprocess
import tempfile
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import cement_silos_repo, cement_receipts_repo
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.widgets.silo_canvas import SiloCanvas
from ui.base_window import BaseToplevelWindow


class CementReportWindow(BaseToplevelWindow):
    """Окно отчета по цементу"""
    def __init__(self, parent, on_exit_callback):
        self.silo_list = [row[0] for row in cement_silos_repo.get_all()]
        super().__init__(parent, on_exit_callback, title="Отчет по цементу")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Отчет по цементу")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата (начало периода):")
        self.start_date_entry = DateEntry(left_inner)
        self.start_date_entry.pack(fill=tk.X, padx=10, pady=(10, 4))
        
        self.add_field_label(left_inner, "Дата (конец периода):")
        self.end_date_entry = DateEntry(left_inner)
        self.end_date_entry.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Силос цемента:")
        self.silo_combo = AutocompleteCombobox(
            left_inner, values=self.silo_list
        )
        self.silo_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.hint_label = tk.Label(
            left_inner,
            text="Пустое поле - отчет по всем силосам",
            font=FONTS['hint'],
            bg=COLORS['panel_bg'],
            fg=COLORS['work_area_text'],
            anchor='w'
        )
        self.hint_label.pack(fill=tk.X, padx=10, pady=(0, 15))
        
        self.report_btn = self.add_button(left_inner, "Открыть отчет",
                                          self.generate_pdf_report,
                                          color=COLORS['button_primary'])
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ===== ПРАВАЯ ЧАСТЬ =====
        right_frame = self.create_right_panel(content_frame)
        
        # Визуализация силосов
        silos_frame = tk.Frame(
            right_frame,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=SIZES['panel_border']
        )
        silos_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(
            silos_frame,
            text="Текущий уровень наполнения силосов",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        self.silos_canvas_container = tk.Frame(silos_frame, bg=COLORS['panel_bg'])
        self.silos_canvas_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        silos_data = cement_silos_repo.get_all()
        balances = cement_receipts_repo.get_current_balance_by_silo()
        self.silos_canvas = SiloCanvas(
            self.silos_canvas_container,
            silos_data,
            balances
        )
        self.silos_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Заголовок блока таблиц
        tk.Label(
            right_frame,
            text="Отчет по движению цемента",
            font=FONTS['menu'],
            bg=COLORS['panel_bg'],
            fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        # Контейнер для таблиц
        self.tables_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        self.tables_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.load_report_data()
    
    def _format_number(self, value):
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
    
    # ========================================================================
    # [НОВОЕ] Безопасная распаковка строки отчёта по цементу
    # Поддерживает старый формат (5 значений) и новый (6 значений)
    # ========================================================================
    def _unpack_cement_report_row(self, row):
        """
        Приводит строку отчёта по цементу к единому виду:
        (date, silo, receipt, consumption, correction, balance)
        
        Поддерживает:
        - старый формат из 5 колонок (без correction):
          (date, silo, receipt, consumption, balance)
        - новый формат из 6 колонок:
          (date, silo, receipt, consumption, correction, balance)
        """
        if len(row) == 6:
            return row
        
        if len(row) == 5:
            date, silo, receipt, consumption, balance = row
            return date, silo, receipt, consumption, 0, balance
        
        raise ValueError(f"Неожиданный формат строки отчёта по цементу: {row}")
    
    # ========================================================================
    # [ИЗМЕНЕНО] Загрузка данных с равномерным распределением через grid
    # ========================================================================
    def load_report_data(self):
        """
        Загрузить данные отчета.
        - Создаются таблицы для ВСЕХ силосов (даже без данных)
        - Таблицы равномерно делят пространство по вертикали через grid()
        - Защита от ошибки распаковки кортежей
        """
        # Очищаем контейнер
        for widget in self.tables_container.winfo_children():
            widget.destroy()
        
        # Получаем все данные отчета
        report_data = cement_receipts_repo.get_cement_report()
        
        # Получаем список ВСЕХ силосов из справочника
        all_silos = cement_silos_repo.get_all()
        
        if not all_silos:
            no_data_label = tk.Label(
                self.tables_container,
                text="Силоса не настроены. Добавьте их в Настройках.",
                font=FONTS['menu'],
                bg=COLORS['panel_bg'],
                fg=COLORS['work_area_text']
            )
            no_data_label.pack(expand=True)
            return
        
        # Группируем данные по силосам (с безопасной распаковкой)
        data_by_silo = {}
        if report_data:
            for row in report_data:
                date, silo, receipt, consumption, correction, balance = self._unpack_cement_report_row(row)
                if silo not in data_by_silo:
                    data_by_silo[silo] = []
                data_by_silo[silo].append((date, silo, receipt, consumption, correction, balance))
        
        # Настраиваем grid-контейнер для равномерного распределения
        self.tables_container.grid_columnconfigure(0, weight=1)
        
        # На случай перезагрузки очищаем веса старых строк
        for i in range(50):
            self.tables_container.grid_rowconfigure(i, weight=0)
        
        # Создаем таблицу для КАЖДОГО силоса (даже если данных нет)
        for row_idx, (silo_name, capacity) in enumerate(all_silos):
            self.tables_container.grid_rowconfigure(row_idx, weight=1)
            
            silo_data = data_by_silo.get(silo_name, [])
            self._create_silo_table(row_idx, silo_name, silo_data)
    
    # ========================================================================
    # [ИЗМЕНЕНО] Создание таблицы с колонкой "Коррекция"
    # ========================================================================
    def _create_silo_table(self, row_idx, silo_name, silo_data):
        """
        Создать таблицу отчета для одного силоса.
        Колонки: Дата | Поступление | Расход | Коррекция | Остаток
        """
        silo_block = tk.Frame(
            self.tables_container,
            bg=COLORS['panel_bg'],
            relief=tk.RAISED,
            bd=1
        )
        silo_block.grid(
            row=row_idx, column=0,
            sticky='nsew',
            padx=0, pady=1
        )
        
        silo_block.grid_rowconfigure(0, weight=0)
        silo_block.grid_rowconfigure(1, weight=1)
        silo_block.grid_columnconfigure(0, weight=1)
        
        # Заголовок блока силоса
        header_frame = tk.Frame(silo_block, bg=COLORS['button_primary'])
        header_frame.grid(row=0, column=0, sticky='ew')
        
        tk.Label(
            header_frame,
            text=f"  {silo_name}",
            font=FONTS['menu'],
            bg=COLORS['button_primary'],
            fg=COLORS['button_text'],
            anchor='w'
        ).pack(fill=tk.X, padx=5, pady=3)
        
        # Контейнер для Treeview
        tree_container = tk.Frame(silo_block, bg=COLORS['panel_bg'])
        tree_container.grid(row=1, column=0, sticky='nsew')
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        
        # [ИЗМЕНЕНО] Добавлена колонка 'correction'
        tree = ttk.Treeview(
            tree_container,
            columns=('date', 'receipt', 'consumption', 'correction', 'balance'),
            show='headings',
            selectmode='browse'
        )
        
        tree.grid(row=0, column=0, sticky='nsew')
        tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.configure(command=tree.yview)
        
        tree.heading('date', text='Дата', anchor='w')
        tree.heading('receipt', text='Поступление', anchor='w')
        tree.heading('consumption', text='Расход', anchor='w')
        tree.heading('correction', text='Коррекция', anchor='w')
        tree.heading('balance', text='Остаток', anchor='w')
        
        tree.column('date', width=90, anchor='w')
        tree.column('receipt', width=110, anchor='w')
        tree.column('consumption', width=110, anchor='w')
        tree.column('correction', width=110, anchor='w')
        tree.column('balance', width=110, anchor='w')
        
        # Заполняем данными
        if silo_data:
            for row in silo_data:
                date, silo, receipt, consumption, correction, balance = self._unpack_cement_report_row(row)
                receipt_str = self._format_number(receipt) if receipt and receipt > 0 else ''
                consumption_str = self._format_number(consumption) if consumption and consumption > 0 else ''
                # [НОВОЕ] Коррекция может быть как положительной, так и отрицательной
                correction_str = self._format_number(correction) if correction and correction != 0 else ''
                balance_str = self._format_number(balance)
                tree.insert(
                    '', 'end',
                    values=(date, receipt_str, consumption_str, correction_str, balance_str)
                )
        else:
            tree.insert(
                '', 'end',
                values=('—', 'Нет данных', 'Нет данных', 'Нет данных', '—')
            )
    
    # ========================================================================
    # ГЕНЕРАЦИЯ PDF-ОТЧЁТА
    # ========================================================================
    def _validate_date(self, date_str):
        try:
            datetime.strptime(date_str, '%d.%m.%Y')
            return True
        except ValueError:
            return False
    
    def _date_to_comparable(self, date_str):
        try:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                return int(f"{year}{month.zfill(2)}{day.zfill(2)}")
        except (ValueError, AttributeError):
            pass
        return 0
    
    def _check_reportlab_installed(self):
        try:
            import reportlab
            return True
        except ImportError:
            return False
    
    def _install_reportlab(self):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _ensure_reportlab(self):
        if not self._check_reportlab_installed():
            result = messagebox.askyesno(
                "Необходима установка",
                "Для формирования PDF-отчетов требуется библиотека 'reportlab'.\n\n"
                "Установить её автоматически сейчас?\n\n"
                "(Требуется интернет-соединение)"
            )
            if result:
                if self._install_reportlab():
                    messagebox.showinfo("Успех", "Библиотека reportlab успешно установлена!")
                    return True
                else:
                    messagebox.showerror("Ошибка установки", "Не удалось установить библиотеку.")
                    return False
            else:
                return False
        return True
    
    def _register_cyrillic_font(self, pdfmetrics, TTFont):
        font_registered = False
        font_paths = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/Arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                    font_registered = True
                    break
                except Exception:
                    continue
        return 'CyrillicFont' if font_registered else 'Helvetica'
    
    def generate_pdf_report(self):
        """Генерация PDF-отчёта по цементу (книжная ориентация)"""
        if not self._ensure_reportlab():
            return
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            messagebox.showerror("Ошибка", "Не удалось загрузить библиотеку reportlab.")
            return
        
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        silo_name = self.silo_combo.get().strip()
        
        if not start_date or not end_date:
            messagebox.showwarning("Внимание", "Укажите даты периода")
            return
        if not self._validate_date(start_date) or not self._validate_date(end_date):
            messagebox.showwarning("Внимание", "Неверный формат даты")
            return
        if self._date_to_comparable(start_date) > self._date_to_comparable(end_date):
            messagebox.showwarning("Внимание", "Дата начала не может быть позже даты конца")
            return
        
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.pdf', prefix='Otchet_po_cementu_'
            )
            temp_file.close()
            file_path = temp_file.name
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать временный файл:\n\n{e}")
            return
        
        try:
            font_name = self._register_cyrillic_font(pdfmetrics, TTFont)
            
            doc = SimpleDocTemplate(
                file_path, pagesize=A4,
                rightMargin=1.5*cm, leftMargin=1.5*cm,
                topMargin=2*cm, bottomMargin=2*cm
            )
            
            elements = []
            
            title_style = ParagraphStyle(
                'Title', fontName=font_name, fontSize=14,
                alignment=1, spaceAfter=5, leading=16
            )
            subtitle_style = ParagraphStyle(
                'Subtitle', fontName=font_name, fontSize=10,
                alignment=1, spaceAfter=10, leading=12
            )
            cell_style = ParagraphStyle(
                'Cell', fontName=font_name, fontSize=8, leading=9
            )
            
            title_text = f"Отчет по цементу с {start_date} по {end_date}"
            elements.append(Paragraph(title_text, title_style))
            
            if silo_name:
                subtitle_text = f"Силос: {silo_name}"
            else:
                subtitle_text = "По всем силосам"
            elements.append(Paragraph(subtitle_text, subtitle_style))
            elements.append(Spacer(1, 0.3*cm))
            
            if silo_name:
                elements.extend(self._build_silo_report(
                    silo_name, start_date, end_date, cell_style, font_name
                ))
            else:
                elements.extend(self._build_general_report(
                    start_date, end_date, cell_style, font_name
                ))
            
            doc.build(elements)
            
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':
                    subprocess.call(['xdg-open', file_path])
            except Exception as e:
                messagebox.showwarning(
                    "Предупреждение",
                    f"PDF сформирован, но не удалось открыть автоматически:\n\n{e}\n\n"
                    f"Файл сохранен во временной папке:\n{file_path}"
                )
        except Exception as e:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
            messagebox.showerror("Ошибка", f"Не удалось сформировать PDF-отчет:\n\n{e}")
    
    def _build_general_report(self, start_date, end_date, cell_style, font_name):
        """
        Построить общий отчёт по всем силосам помесячно.
        Добавлена колонка "Расход цемента, кг".
        """
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        
        report_data = cement_receipts_repo.get_monthly_report_with_corrections(
            start_date, end_date
        )
        
        if not report_data:
            return [Paragraph("Нет данных за выбранный период", cell_style)]
        
        elements = []
        
        by_month = {}
        for sort_key, month_str, silo, receipt, consumption, correction in report_data:
            if month_str not in by_month:
                by_month[month_str] = []
            by_month[month_str].append((sort_key, silo, receipt, consumption, correction))
        
        month_order = {
            'Январь': '01', 'Февраль': '02', 'Март': '03', 'Апрель': '04',
            'Май': '05', 'Июнь': '06', 'Июль': '07', 'Август': '08',
            'Сентябрь': '09', 'Октябрь': '10', 'Ноябрь': '11', 'Декабрь': '12'
        }
        
        def month_sort_key(m):
            parts = m.split()
            if len(parts) == 2:
                month_name, year = parts
                return int(year) * 100 + int(month_order.get(month_name, '00'))
            return 0
        
        sorted_months = sorted(by_month.keys(), key=month_sort_key, reverse=True)
        
        for month_str in sorted_months:
            month_data = by_month[month_str]
            
            month_title_style = ParagraphStyle(
                'MonthTitle', fontName=font_name, fontSize=10,
                alignment=0, spaceAfter=3, spaceBefore=5, leading=12
            )
            elements.append(Paragraph(f"<b>{month_str}</b>", month_title_style))
            
            table_data = [[
                Paragraph('Силос', cell_style),
                Paragraph('Поступление<br/>цемента, кг', cell_style),
                Paragraph('Расход<br/>цемента, кг', cell_style),
                Paragraph('Корректировка,<br/>кг', cell_style)
            ]]
            
            month_total_receipt = 0
            month_total_consumption = 0
            month_total_correction = 0
            
            month_data.sort(key=lambda x: x[1].lower())
            
            for sort_key, silo, receipt, consumption, correction in month_data:
                table_data.append([
                    Paragraph(silo, cell_style),
                    Paragraph(self._format_number(receipt), cell_style),
                    Paragraph(self._format_number(consumption), cell_style),
                    Paragraph(self._format_number(correction), cell_style)
                ])
                month_total_receipt += receipt
                month_total_consumption += consumption
                month_total_correction += correction
            
            table_data.append([
                Paragraph('<b>Итого за месяц</b>', cell_style),
                Paragraph(f'<b>{self._format_number(month_total_receipt)}</b>', cell_style),
                Paragraph(f'<b>{self._format_number(month_total_consumption)}</b>', cell_style),
                Paragraph(f'<b>{self._format_number(month_total_correction)}</b>', cell_style)
            ])
            
            col_widths = [5*cm, 4.3*cm, 4.3*cm, 4.4*cm]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table_style = TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 3),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('TOPPADDING', (0, -1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 3),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 1), (-1, -2), 2),
                ('BOTTOMPADDING', (0, 1), (-1, -2), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ])
            
            for i in range(1, len(table_data) - 1):
                if i % 2 == 0:
                    table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9'))
            
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.3*cm))
        
        return elements
    
    def _build_silo_report(self, silo_name, start_date, end_date, cell_style, font_name):
        """
        Построить отчёт по конкретному силосу по датам.
        [ИЗМЕНЕНО]
        - Даты идут по возрастанию (хронологически)
        - Итоги поступлений и расхода выводятся ПЕРЕД КАЖДОЙ корректировкой
        - После корректировки накопление начинается заново
        - В конце отчёта — общий итог за период: приход, расход, корректировка
        """
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        
        daily_data = cement_receipts_repo.get_silo_daily_report(
            silo_name, start_date, end_date
        )
        
        if not daily_data:
            return [Paragraph("Нет данных за выбранный период", cell_style)]
        
        elements = []
        
        section_title_style = ParagraphStyle(
            'SectionTitle', fontName=font_name, fontSize=10,
            alignment=0, spaceAfter=5, spaceBefore=5, leading=12
        )
        elements.append(Paragraph(f"<b>Силос: {silo_name}</b>", section_title_style))
        
        table_data = [[
            Paragraph('Дата', cell_style),
            Paragraph('Поступление<br/>цемента, кг', cell_style),
            Paragraph('Расход<br/>цемента, кг', cell_style),
            Paragraph('Корректировка,<br/>кг', cell_style)
        ]]
        
        # Накопительные суммы для промежуточных итогов (перед корректировками)
        accumulated_receipt = 0
        accumulated_consumption = 0
        has_accumulated = False
        
        # [НОВОЕ] Общие итоги за весь период
        total_receipt = 0
        total_consumption = 0
        total_correction = 0
        
        # Обрабатываем все операции в хронологическом порядке
        for date, receipt_qty, consumption_qty, is_correction in daily_data:
            if is_correction == 1:
                # === КОРРЕКТИРОВКА ===
                # Сначала выводим промежуточный итог (если есть накопленные данные)
                if has_accumulated and (accumulated_receipt > 0 or accumulated_consumption > 0):
                    table_data.append([
                        Paragraph('<b>Итого до корректировки:</b>', cell_style),
                        Paragraph(f'<b>{self._format_number(accumulated_receipt)}</b>', cell_style),
                        Paragraph(f'<b>{self._format_number(accumulated_consumption)}</b>', cell_style),
                        Paragraph('', cell_style)
                    ])
                
                # Сбрасываем накопленные суммы для следующего блока
                accumulated_receipt = 0
                accumulated_consumption = 0
                has_accumulated = False
                
                # Выводим строку корректировки
                table_data.append([
                    Paragraph(date, cell_style),
                    Paragraph('', cell_style),
                    Paragraph('', cell_style),
                    Paragraph(self._format_number(receipt_qty), cell_style)
                ])
                
                # Накапливаем общую корректировку
                total_correction += receipt_qty
            else:
                # === ОБЫЧНАЯ ОПЕРАЦИЯ (поступление/расход) ===
                table_data.append([
                    Paragraph(date, cell_style),
                    Paragraph(self._format_number(receipt_qty) if receipt_qty > 0 else '', cell_style),
                    Paragraph(self._format_number(consumption_qty) if consumption_qty > 0 else '', cell_style),
                    Paragraph('', cell_style)
                ])
                # Накапливаем суммы для промежуточных итогов
                accumulated_receipt += receipt_qty
                accumulated_consumption += consumption_qty
                has_accumulated = True
                
                # Накапливаем общие итоги за период
                total_receipt += receipt_qty
                total_consumption += consumption_qty
        
        # Финальный промежуточный итог (если после последней корректировки есть данные)
        if has_accumulated and (accumulated_receipt > 0 or accumulated_consumption > 0):
            table_data.append([
                Paragraph('<b>Итого до конца периода:</b>', cell_style),
                Paragraph(f'<b>{self._format_number(accumulated_receipt)}</b>', cell_style),
                Paragraph(f'<b>{self._format_number(accumulated_consumption)}</b>', cell_style),
                Paragraph('', cell_style)
            ])
        
        # [НОВОЕ] Общий итог за весь период: приход, расход, корректировка
        table_data.append([
            Paragraph('<b>ИТОГО ЗА ПЕРИОД:</b>', cell_style),
            Paragraph(f'<b>{self._format_number(total_receipt)}</b>', cell_style),
            Paragraph(f'<b>{self._format_number(total_consumption)}</b>', cell_style),
            Paragraph(f'<b>{self._format_number(total_correction)}</b>', cell_style)
        ])
        
        # Ширина колонок для 4 колонок в книжном A4
        col_widths = [3.5*cm, 4.8*cm, 4.8*cm, 4.9*cm]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table_style = TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 3),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ])
        
        # Подсветка строк
        for i, row in enumerate(table_data[1:], start=1):
            row_text = str(row[0])
            if 'ИТОГО ЗА ПЕРИОД' in row_text:
                # Общий итог за период — тёмно-серый фон + жирная линия сверху и снизу
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#d5dbdb'))
                table_style.add('LINEABOVE', (0, i), (-1, i), 1, colors.black)
                table_style.add('LINEBELOW', (0, i), (-1, i), 1, colors.black)
            elif 'Итого' in row_text:
                # Промежуточный итог — светло-серый фон + линия сверху
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1'))
                table_style.add('LINEABOVE', (0, i), (-1, i), 0.5, colors.grey)
            elif i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9'))
        
        table.setStyle(table_style)
        elements.append(table)
        
        return elements

    def _on_auto_refresh(self):
        """
        Автообновление данных при изменении БД другим компьютером.
        Вызывается таймером из BaseToplevelWindow каждые 3 секунды.
        """
        try:
            self.load_report_data()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в CementReportWindow: {e}")