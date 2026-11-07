"""
Окно "Отчет по расходам" - отчет о расходах с фильтрацией
Оформление идентично окну "Производство продукции".
[ИЗМЕНЕНО] Все messagebox заменены на методы базового класса.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import os
import sys
import subprocess
import tempfile
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    suppliers_repo, materials_repo, payers_repo, payment_types_repo,
    purposes_repo, general_expenses_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.base_window import BaseToplevelWindow


class ExpensesReportWindow(BaseToplevelWindow):
    """Окно отчета по расходам"""
    def __init__(self, parent, on_exit_callback):
        self.supplier_list = [row[0] for row in suppliers_repo.get_all()]
        self.material_list = [row[0] for row in materials_repo.get_all()]
        self.payer_list = [row[0] for row in payers_repo.get_all()]
        self.payment_type_list = [row[0] for row in payment_types_repo.get_all()]
        self.purpose_list = [row[0] for row in purposes_repo.get_all()]
        super().__init__(parent, on_exit_callback, title="Отчет по расходам")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Отчет по расходам")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата (начало периода):")
        self.start_date_entry = DateEntry(left_inner)
        self.start_date_entry.pack(fill=tk.X, padx=10, pady=(10, 4))
        
        self.add_field_label(left_inner, "Дата (конец периода):")
        self.end_date_entry = DateEntry(left_inner)
        self.end_date_entry.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Поставщик:")
        self.supplier_combo = AutocompleteCombobox(left_inner, values=self.supplier_list)
        self.supplier_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Плательщик:")
        self.payer_combo = AutocompleteCombobox(left_inner, values=self.payer_list)
        self.payer_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Вид оплаты:")
        self.payment_type_combo = AutocompleteCombobox(left_inner, values=self.payment_type_list)
        self.payment_type_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Назначение:")
        self.purpose_combo = AutocompleteCombobox(left_inner, values=self.purpose_list)
        self.purpose_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Материалы и услуги:")
        self.material_combo = AutocompleteCombobox(left_inner, values=self.material_list)
        self.material_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.hint_label = tk.Label(
            left_inner, text="Пустые поля - отчет по всем расходам",
            font=FONTS['hint'], bg=COLORS['panel_bg'], fg=COLORS['work_area_text'], anchor='w'
        )
        self.hint_label.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.report_btn = self.add_button(left_inner, "Открыть отчет",
                                          self.generate_pdf_report,
                                          color=COLORS['button_primary'])
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ===== ПРАВАЯ ЧАСТЬ =====
        right_frame = self.create_right_panel(content_frame)
        tk.Label(
            right_frame, text="Журнал общих расходов",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        tree_container = tk.Frame(right_frame, bg=COLORS['panel_bg'])
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=('date', 'supplier', 'material', 'quantity', 'price', 'total',
                     'payer', 'payment_type', 'purpose', 'comment'),
            show='headings', yscrollcommand=scrollbar_y.set, selectmode='browse'
        )
        self.tree.heading('date', text='Дата', anchor='w')
        self.tree.heading('supplier', text='Поставщик', anchor='w')
        self.tree.heading('material', text='Материалы и услуги', anchor='w')
        self.tree.heading('quantity', text='Кол-во', anchor='w')
        self.tree.heading('price', text='Цена, руб', anchor='w')
        self.tree.heading('total', text='Сумма, руб', anchor='w')
        self.tree.heading('payer', text='Плательщик', anchor='w')
        self.tree.heading('payment_type', text='Вид оплаты', anchor='w')
        self.tree.heading('purpose', text='Назначение', anchor='w')
        self.tree.heading('comment', text='Комментарии', anchor='w')
        self.tree.column('date', width=80, anchor='w')
        self.tree.column('supplier', width=150, anchor='w')
        self.tree.column('material', width=180, anchor='w')
        self.tree.column('quantity', width=60, anchor='w')
        self.tree.column('price', width=80, anchor='w')
        self.tree.column('total', width=90, anchor='w')
        self.tree.column('payer', width=150, anchor='w')
        self.tree.column('payment_type', width=150, anchor='w')
        self.tree.column('purpose', width=150, anchor='w')
        self.tree.column('comment', width=230, anchor='w')
        scrollbar_y.config(command=self.tree.yview)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.load_expenses()
    
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
            result = self.ask_yes_no(
                "Необходима установка",
                "Для формирования PDF-отчетов требуется библиотека 'reportlab'.\n\n"
                "Установить её автоматически сейчас?\n\n"
                "(Требуется интернет-соединение)"
            )
            if result:
                if self._install_reportlab():
                    self.show_info("Успех", "Библиотека reportlab успешно установлена!")
                    return True
                else:
                    self.show_error("Ошибка установки", "Не удалось установить библиотеку.")
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
    
    def _get_month_name(self, date_str):
        month_names = {
            '01': 'Январь', '02': 'Февраль', '03': 'Март',
            '04': 'Апрель', '05': 'Май', '06': 'Июнь',
            '07': 'Июль', '08': 'Август', '09': 'Сентябрь',
            '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
        }
        try:
            parts = date_str.split('.')
            if len(parts) == 3:
                month = parts[1]
                year = parts[2]
                return f"{month_names.get(month, month)} {year}"
        except:
            pass
        return date_str
    
    def _get_month_sort_key(self, date_str):
        try:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                return f"{year}{month.zfill(2)}"
        except:
            pass
        return '999999'
    
    def load_expenses(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        records = general_expenses_repo.get_all()
        for row in records:
            (expense_id, date, supplier, material, quantity, price,
             payer, payment_type, purpose, comment) = row
            qty = quantity or 0
            prc = price or 0
            total = qty * prc
            self.tree.insert(
                '', 'end', iid=str(expense_id),
                values=(date, supplier or '—', material or '—',
                        self._format_number(quantity), self._format_number(price),
                        self._format_number(total), payer or '—',
                        payment_type or '—', purpose or '—', comment or '—')
            )
    
    def generate_pdf_report(self):
        if not self._ensure_reportlab():
            return
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            self.show_error("Ошибка", "Не удалось загрузить библиотеку reportlab.")
            return
        
        start_date = self.start_date_entry.get_date()
        end_date = self.end_date_entry.get_date()
        supplier = self.supplier_combo.get().strip()
        payer = self.payer_combo.get().strip()
        payment_type = self.payment_type_combo.get().strip()
        purpose = self.purpose_combo.get().strip()
        material = self.material_combo.get().strip()
        
        if not start_date or not end_date:
            self.show_warning("Внимание", "Укажите даты периода")
            return
        if not self._validate_date(start_date) or not self._validate_date(end_date):
            self.show_warning("Внимание", "Неверный формат даты")
            return
        if self._date_to_comparable(start_date) > self._date_to_comparable(end_date):
            self.show_warning("Внимание", "Дата начала не может быть позже даты конца")
            return
        
        active_filters = []
        filter_values = {}
        if supplier:
            active_filters.append(('supplier', 'Поставщик', supplier))
            filter_values['supplier'] = supplier
        if payer:
            active_filters.append(('payer', 'Плательщик', payer))
            filter_values['payer'] = payer
        if payment_type:
            active_filters.append(('payment_type', 'Вид оплаты', payment_type))
            filter_values['payment_type'] = payment_type
        if purpose:
            active_filters.append(('purpose', 'Назначение', purpose))
            filter_values['purpose'] = purpose
        if material:
            active_filters.append(('material', 'Материалы и услуги', material))
            filter_values['material'] = material
        
        report_data = general_expenses_repo.get_expenses_report(
            start_date, end_date, filter_values if filter_values else None
        )
        
        if not report_data:
            self.show_info("Информация", "Нет данных о расходах за выбранный период.")
            return
        
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.pdf', prefix='Otchet_po_rashodam_'
            )
            temp_file.close()
            file_path = temp_file.name
        except Exception as e:
            self.show_error("Ошибка", f"Не удалось создать временный файл:\n\n{e}")
            return
        
        try:
            font_name = self._register_cyrillic_font(pdfmetrics, TTFont)
            doc = SimpleDocTemplate(
                file_path, pagesize=landscape(A4),
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
            section_title_style = ParagraphStyle(
                'SectionTitle', fontName=font_name, fontSize=11,
                alignment=0, spaceAfter=5, spaceBefore=10, leading=13
            )
            cell_style = ParagraphStyle(
                'Cell', fontName=font_name, fontSize=8, leading=9
            )
            
            title_text = f"Отчет по расходам с {start_date} по {end_date}"
            elements.append(Paragraph(title_text, title_style))
            
            if active_filters:
                fields_list = [f"{name}: {value}" for _, name, value in active_filters]
                subtitle_text = "Фильтры: " + " | ".join(fields_list)
            else:
                subtitle_text = "По всем расходам"
            elements.append(Paragraph(subtitle_text, subtitle_style))
            elements.append(Spacer(1, 0.3*cm))
            
            if not active_filters:
                elements.extend(self._build_all_expenses_table(report_data, cell_style, font_name))
            else:
                for filter_key, filter_name, filter_value in active_filters:
                    filtered_data = general_expenses_repo.get_expenses_report(
                        start_date, end_date, {filter_key: filter_value}
                    )
                    if not filtered_data:
                        continue
                    section_title = f"{filter_name}: {filter_value}"
                    elements.append(Paragraph(section_title, section_title_style))
                    elements.extend(self._build_filtered_table(filtered_data, cell_style, font_name))
                    elements.append(Spacer(1, 0.5*cm))
            
            doc.build(elements)
            
            try:
                if os.name == 'nt':
                    os.startfile(file_path)
                elif os.name == 'posix':
                    subprocess.call(['xdg-open', file_path])
            except Exception as e:
                self.show_warning(
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
            self.show_error("Ошибка", f"Не удалось сформировать PDF-отчет:\n\n{e}")
    
    def _build_all_expenses_table(self, report_data, cell_style, font_name):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        
        by_month = {}
        for row in report_data:
            (exp_id, date, supplier, material, quantity, price,
             payer, payment_type, purpose, comment) = row
            month_key = self._get_month_sort_key(date)
            month_name = self._get_month_name(date)
            if month_key not in by_month:
                by_month[month_key] = {'name': month_name, 'rows': []}
            by_month[month_key]['rows'].append(row)
        
        sorted_months = sorted(by_month.keys(), reverse=True)
        elements = []
        
        for month_key in sorted_months:
            month_data = by_month[month_key]
            month_name = month_data['name']
            rows = month_data['rows']
            
            month_title_style = ParagraphStyle(
                'MonthTitle', fontName=font_name, fontSize=10,
                alignment=0, spaceAfter=3, spaceBefore=5, leading=12
            )
            elements.append(Paragraph(f"<b>{month_name}</b>", month_title_style))
            rows.sort(key=lambda r: (r[3] or '').lower())
            
            table_data = [[
                Paragraph('Дата', cell_style), Paragraph('Поставщик', cell_style),
                Paragraph('Материалы и услуги', cell_style), Paragraph('Кол-во', cell_style),
                Paragraph('Цена, руб', cell_style), Paragraph('Сумма, руб', cell_style),
                Paragraph('Плательщик', cell_style), Paragraph('Вид оплаты', cell_style),
                Paragraph('Назначение', cell_style), Paragraph('Комментарии', cell_style)
            ]]
            
            month_total = 0
            for row in rows:
                (exp_id, date, supplier, material, quantity, price,
                 payer, payment_type, purpose, comment) = row
                qty = quantity or 0
                prc = price or 0
                total = qty * prc
                month_total += total
                table_data.append([
                    Paragraph(date, cell_style),
                    Paragraph(supplier or '', cell_style),
                    Paragraph(material or '', cell_style),
                    Paragraph(self._format_number(quantity), cell_style),
                    Paragraph(self._format_number(price), cell_style),
                    Paragraph(self._format_number(total), cell_style),
                    Paragraph(payer or '', cell_style),
                    Paragraph(payment_type or '', cell_style),
                    Paragraph(purpose or '', cell_style),
                    Paragraph(comment or '', cell_style)
                ])
            
            table_data.append([
                Paragraph('<b>Итого за месяц</b>', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph(f'<b>{self._format_number(month_total)}</b>', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style)
            ])
            
            col_widths = [2*cm, 3.5*cm, 4*cm, 1.5*cm, 2*cm, 2.5*cm, 3.5*cm, 3*cm, 3*cm, 4*cm]
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
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
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
    
    def _build_filtered_table(self, report_data, cell_style, font_name):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        
        by_month = {}
        for row in report_data:
            (exp_id, date, supplier, material, quantity, price,
             payer, payment_type, purpose, comment) = row
            month_key = self._get_month_sort_key(date)
            month_name = self._get_month_name(date)
            if month_key not in by_month:
                by_month[month_key] = {'name': month_name, 'rows': []}
            by_month[month_key]['rows'].append(row)
        
        sorted_months = sorted(by_month.keys(), reverse=True)
        elements = []
        
        for month_key in sorted_months:
            month_data = by_month[month_key]
            month_name = month_data['name']
            rows = month_data['rows']
            
            month_title_style = ParagraphStyle(
                'MonthTitle', fontName=font_name, fontSize=9,
                alignment=0, spaceAfter=2, spaceBefore=3, leading=11
            )
            elements.append(Paragraph(f"<b>{month_name}</b>", month_title_style))
            rows.sort(key=lambda r: self._date_to_comparable(r[1]), reverse=True)
            
            table_data = [[
                Paragraph('Дата', cell_style), Paragraph('Поставщик', cell_style),
                Paragraph('Материалы и услуги', cell_style), Paragraph('Кол-во', cell_style),
                Paragraph('Цена, руб', cell_style), Paragraph('Сумма, руб', cell_style),
                Paragraph('Плательщик', cell_style), Paragraph('Вид оплаты', cell_style),
                Paragraph('Назначение', cell_style), Paragraph('Комментарии', cell_style)
            ]]
            
            month_total = 0
            for row in rows:
                (exp_id, date, supplier, material, quantity, price,
                 payer, payment_type, purpose, comment) = row
                qty = quantity or 0
                prc = price or 0
                total = qty * prc
                month_total += total
                table_data.append([
                    Paragraph(date, cell_style),
                    Paragraph(supplier or '', cell_style),
                    Paragraph(material or '', cell_style),
                    Paragraph(self._format_number(quantity), cell_style),
                    Paragraph(self._format_number(price), cell_style),
                    Paragraph(self._format_number(total), cell_style),
                    Paragraph(payer or '', cell_style),
                    Paragraph(payment_type or '', cell_style),
                    Paragraph(purpose or '', cell_style),
                    Paragraph(comment or '', cell_style)
                ])
            
            table_data.append([
                Paragraph('<b>Итого за месяц</b>', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph(f'<b>{self._format_number(month_total)}</b>', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style),
                Paragraph('', cell_style), Paragraph('', cell_style)
            ])
            
            col_widths = [2*cm, 3.5*cm, 4*cm, 1.5*cm, 2*cm, 2.5*cm, 3.5*cm, 3*cm, 3*cm, 4*cm]
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
                ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
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
            elements.append(Spacer(1, 0.2*cm))
        
        return elements

    def _on_auto_refresh(self):
        """
        Автообновление данных при изменении БД другим компьютером.
        Вызывается таймером из BaseToplevelWindow каждые 3 секунды.
        """
        try:
            self.load_expenses()
        except Exception as e:
            print(f"⚠ Ошибка автообновления в ExpensesReportWindow: {e}")