"""
Окно "Отчет по производству продукции" - отчет о производстве
[ИЗМЕНЕНО] Применена пагинация к журналу производства справа.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import sys
import subprocess
import tempfile
from config.settings import COLORS, FONTS, PADDING, SIZES
from database.repositories import (
    products_repo, equipment_repo, production_repo
)
from ui.widgets.date_entry import DateEntry
from ui.widgets.combobox_autocomplete import AutocompleteCombobox
from ui.widgets.paginated_treeview import PaginatedTreeview
from ui.base_window import BaseToplevelWindow


class ProductionReportWindow(BaseToplevelWindow):
    """Окно отчета по производству продукции"""
    def __init__(self, parent, on_exit_callback):
        all_products = products_repo.get_all()
        self.product_list = [row[0] for row in all_products]
        self.volume_map = {row[0]: (row[1] if row[1] else 1) for row in all_products}
        self.equipment_list = [row[0] for row in equipment_repo.get_all()]
        super().__init__(parent, on_exit_callback, title="Отчет по производству продукции")
    
    def _build_ui(self):
        self.create_title_section(self.window, "Отчет по производству продукции")
        content_frame = self.create_content_frame(self.window)
        left_inner = self.create_left_panel_with_scroll(content_frame)
        
        self.add_field_label(left_inner, "Дата (начало периода):")
        self.start_date_entry = DateEntry(left_inner)
        self.start_date_entry.pack(fill=tk.X, padx=10, pady=(10, 4))
        
        self.add_field_label(left_inner, "Дата (конец периода):")
        self.end_date_entry = DateEntry(left_inner)
        self.end_date_entry.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Оборудование:")
        self.equipment_combo = AutocompleteCombobox(left_inner, values=self.equipment_list)
        self.equipment_combo.pack(fill=tk.X, padx=10, pady=(0, 4))
        
        self.add_field_label(left_inner, "Продукция:")
        self.product_combo = AutocompleteCombobox(left_inner, values=self.product_list)
        self.product_combo.pack(fill=tk.X, padx=10, pady=(0, 6))
        
        self.hint_label = tk.Label(
            left_inner, text="Пустые поля - отчет по всей продукции",
            font=FONTS['hint'], bg=COLORS['panel_bg'], fg=COLORS['work_area_text'], anchor='w'
        )
        self.hint_label.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.report_btn = self.add_button(left_inner, "Открыть отчет",
                                          self.generate_pdf_report,
                                          color=COLORS['button_primary'])
        self.summary_report_btn = self.add_button(left_inner, "Открыть сводный отчет",
                                                  self.generate_summary_report,
                                                  color=COLORS['button_primary'])
        self.color_summary_report_btn = self.add_button(left_inner, "Сводный отчет (цвет)",
                                                        self.generate_color_summary_report,
                                                        color=COLORS['button_primary'])
        self.exit_btn = self.add_button(left_inner, "Выход", self._on_close,
                                        color=COLORS['button_settings'], side=tk.BOTTOM)
        
        # ===== ПРАВАЯ ЧАСТЬ С ПАГИНАЦИЕЙ =====
        right_frame = self.create_right_panel(content_frame)
        tk.Label(
            right_frame, text="Журнал производства продукции",
            font=FONTS['menu'], bg=COLORS['panel_bg'], fg=COLORS['title_text']
        ).pack(pady=(10, 5), anchor='w', padx=10)
        
        self.paginated_tree = PaginatedTreeview(
            right_frame,
            columns=('date', 'equipment', 'product', 'color', 'quantity'),
            headings={
                'date': 'Дата производства', 'equipment': 'Оборудование',
                'product': 'Продукция', 'color': 'Цвет',
                'quantity': 'Количество, шт/м2'
            },
            column_widths={
                'date': 100, 'equipment': 140, 'product': 220,
                'color': 100, 'quantity': 130
            },
            page_size=100,
            load_callback=self._load_production_page
        )
        self.paginated_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.paginated_tree.load_page(0)
    
    def _load_production_page(self, page, page_size):
        rows, total = production_repo.get_all_paged(page, page_size)
        formatted_rows = []
        for row in rows:
            (prod_id, date, equipment, silo, product, color, quantity_pallets,
             cement, enriched_sand, river_sand, keramzit, plasticizer, water, note) = row
            if not product:
                continue
            calc_qty = self._convert_to_units(product, quantity_pallets)
            formatted_rows.append((
                date, equipment or '—', product, color or '—',
                self._format_number(calc_qty)
            ))
        return formatted_rows, total
    
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
                "Установить её автоматически сейчас?\n\n(Требуется интернет-соединение)"
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
            'C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/Arial.ttf',
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
    
    def _convert_to_units(self, product_name, quantity_pallets):
        if quantity_pallets is None:
            return 0
        volume = self.volume_map.get(product_name, 1)
        return (quantity_pallets or 0) * volume
    
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
    
    def _color_sort_key(self, color):
        if not color or color.strip().lower() == 'серый':
            return (1, '')
        return (0, color.strip().lower())
    
    def generate_pdf_report(self):
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
        equipment = self.equipment_combo.get().strip()
        product = self.product_combo.get().strip()
        
        if not start_date or not end_date:
            messagebox.showwarning("Внимание", "Укажите даты периода")
            return
        if not self._validate_date(start_date) or not self._validate_date(end_date):
            messagebox.showwarning("Внимание", "Неверный формат даты")
            return
        if self._date_to_comparable(start_date) > self._date_to_comparable(end_date):
            messagebox.showwarning("Внимание", "Дата начала не может быть позже даты конца")
            return
        
        active_filters = []
        if equipment:
            active_filters.append(('Оборудование', equipment))
        if product:
            active_filters.append(('Продукция', product))
        
        report_data = production_repo.get_production_report(
            start_date, end_date,
            equipment=equipment if equipment else None,
            product=product if product else None
        )
        
        if not report_data:
            messagebox.showinfo("Информация", "Нет данных о производстве за выбранный период.")
            return
        
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.pdf', prefix='Otchet_po_proizvodstvu_'
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
            month_title_style = ParagraphStyle(
                'MonthTitle', fontName=font_name, fontSize=11,
                alignment=0, spaceAfter=3, spaceBefore=8, leading=13
            )
            product_title_style = ParagraphStyle(
                'ProductTitle', fontName=font_name, fontSize=10,
                alignment=0, spaceAfter=2, spaceBefore=5, leading=12
            )
            cell_style = ParagraphStyle(
                'Cell', fontName=font_name, fontSize=8, leading=9
            )
            color_total_style = ParagraphStyle(
                'ColorTotal', fontName=font_name, fontSize=8, leading=9
            )
            product_total_style = ParagraphStyle(
                'ProductTotal', fontName=font_name, fontSize=8, leading=9
            )
            
            title_text = f"Отчет по производству продукции с {start_date} по {end_date}"
            elements.append(Paragraph(title_text, title_style))
            
            if active_filters:
                filters_list = [f"{name}: {value}" for name, value in active_filters]
                subtitle_text = "Критерии: " + " | ".join(filters_list)
            else:
                subtitle_text = "По всей продукции"
            elements.append(Paragraph(subtitle_text, subtitle_style))
            elements.append(Spacer(1, 0.3*cm))
            
            by_month = {}
            for row in report_data:
                prod_id, date, equip_name, prod_name, color_name, quantity_pallets = row
                calc_qty = self._convert_to_units(prod_name, quantity_pallets)
                month_key = self._get_month_sort_key(date)
                month_name = self._get_month_name(date)
                if month_key not in by_month:
                    by_month[month_key] = {'name': month_name, 'rows': []}
                by_month[month_key]['rows'].append({
                    'date': date, 'equipment': equip_name or '',
                    'product': prod_name or '', 'color': color_name or '',
                    'quantity': calc_qty
                })
            
            sorted_months = sorted(by_month.keys(), reverse=True)
            for month_key in sorted_months:
                month_data = by_month[month_key]
                month_name = month_data['name']
                rows = month_data['rows']
                elements.append(Paragraph(f"<b>{month_name}</b>", month_title_style))
                
                by_product = {}
                for row in rows:
                    prod_key = row['product']
                    if prod_key not in by_product:
                        by_product[prod_key] = []
                    by_product[prod_key].append(row)
                
                sorted_products = sorted(by_product.keys(), key=lambda p: p.lower())
                for prod_name in sorted_products:
                    prod_rows = by_product[prod_name]
                    elements.append(Paragraph(f"<i>{prod_name}</i>", product_title_style))
                    
                    by_color = {}
                    for row in prod_rows:
                        color_key = row['color'] or ''
                        if color_key not in by_color:
                            by_color[color_key] = []
                        by_color[color_key].append(row)
                    
                    sorted_colors = sorted(by_color.keys(), key=self._color_sort_key)
                    
                    table_data = [[
                        Paragraph('Дата', cell_style),
                        Paragraph('Цвет', cell_style),
                        Paragraph('Количество,<br/>шт/м2', cell_style)
                    ]]
                    
                    row_indices_by_color = {}
                    color_total_rows = []
                    product_total_row_index = None
                    product_total_qty = 0
                    
                    for color in sorted_colors:
                        color_rows = by_color[color]
                        color_rows.sort(key=lambda r: -self._date_to_comparable(r['date']))
                        color_total_qty = 0
                        color_row_indices = []
                        
                        for row in color_rows:
                            color_total_qty += row['quantity']
                            table_data.append([
                                Paragraph(row['date'], cell_style),
                                Paragraph(row['color'] if row['color'] else '—', cell_style),
                                Paragraph(self._format_number(row['quantity']), cell_style)
                            ])
                            color_row_indices.append(len(table_data) - 1)
                        
                        row_indices_by_color[color] = color_row_indices
                        color_display = color if color else '—'
                        table_data.append([
                            Paragraph('<b>Итого</b>', color_total_style),
                            Paragraph(f'<b>{color_display}</b>', color_total_style),
                            Paragraph(f'<b>{self._format_number(color_total_qty)}</b>', color_total_style)
                        ])
                        color_total_rows.append((color, len(table_data) - 1))
                        product_total_qty += color_total_qty
                    
                    table_data.append([
                        Paragraph('<b>ИТОГО</b>', product_total_style),
                        Paragraph('', product_total_style),
                        Paragraph(f'<b>{self._format_number(product_total_qty)}</b>', product_total_style)
                    ])
                    product_total_row_index = len(table_data) - 1
                    
                    col_widths = [3*cm, 4*cm, 4*cm]
                    table = Table(table_data, colWidths=col_widths, repeatRows=1)
                    table_style = TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('FONTNAME', (0, 0), (-1, 0), font_name),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('TOPPADDING', (0, 0), (-1, 0), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
                        ('TOPPADDING', (0, 1), (-1, -1), 2),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
                        ('LEFTPADDING', (0, 0), (-1, -1), 3),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ])
                    all_data_row_indices = []
                    for indices in row_indices_by_color.values():
                        all_data_row_indices.extend(indices)
                    for i, idx in enumerate(all_data_row_indices):
                        if i % 2 == 0:
                            table_style.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f9f9f9'))
                    for color, idx in color_total_rows:
                        table_style.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#ecf0f1'))
                        table_style.add('LINEABOVE', (0, idx), (-1, idx), 0.5, colors.grey)
                    if product_total_row_index is not None:
                        table_style.add('BACKGROUND', (0, product_total_row_index), (-1, product_total_row_index), colors.HexColor('#d5dbdb'))
                        table_style.add('LINEABOVE', (0, product_total_row_index), (-1, product_total_row_index), 1, colors.black)
                    table.setStyle(table_style)
                    elements.append(table)
                    elements.append(Spacer(1, 0.3*cm))
                
                elements.append(Spacer(1, 0.3*cm))
            
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
    
    def generate_summary_report(self):
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
        if not start_date or not end_date:
            messagebox.showwarning("Внимание", "Укажите даты периода")
            return
        if not self._validate_date(start_date) or not self._validate_date(end_date):
            messagebox.showwarning("Внимание", "Неверный формат даты")
            return
        if self._date_to_comparable(start_date) > self._date_to_comparable(end_date):
            messagebox.showwarning("Внимание", "Дата начала не может быть позже даты конца")
            return
        
        report_data = production_repo.get_production_report(start_date, end_date)
        if not report_data:
            messagebox.showinfo("Информация", "Нет данных о производстве за выбранный период.")
            return
        
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.pdf', prefix='Svodny_otchet_proizvodstvo_'
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
                alignment=1, spaceAfter=10, leading=16
            )
            cell_style = ParagraphStyle(
                'Cell', fontName=font_name, fontSize=9, leading=11
            )
            
            title_text = f"Сводный отчет по производству с {start_date} по {end_date}"
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            by_product = {}
            for row in report_data:
                prod_id, date, equip_name, prod_name, color_name, quantity_pallets = row
                calc_qty = self._convert_to_units(prod_name, quantity_pallets)
                if prod_name not in by_product:
                    by_product[prod_name] = 0
                by_product[prod_name] += calc_qty
            
            sorted_products = sorted(by_product.keys(), key=lambda p: p.lower())
            table_data = [[
                Paragraph('<b>Продукция</b>', cell_style),
                Paragraph('<b>Общее количество,<br/>шт/м2</b>', cell_style)
            ]]
            for prod_name in sorted_products:
                qty = by_product[prod_name]
                table_data.append([
                    Paragraph(prod_name, cell_style),
                    Paragraph(self._format_number(qty), cell_style)
                ])
            
            col_widths = [12*cm, 4*cm]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table_style = TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ])
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9f9f9'))
            table.setStyle(table_style)
            elements.append(table)
            
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
            messagebox.showerror("Ошибка", f"Не удалось сформировать сводный отчет:\n\n{e}")
    
    def generate_color_summary_report(self):
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
        if not start_date or not end_date:
            messagebox.showwarning("Внимание", "Укажите даты периода")
            return
        if not self._validate_date(start_date) or not self._validate_date(end_date):
            messagebox.showwarning("Внимание", "Неверный формат даты")
            return
        if self._date_to_comparable(start_date) > self._date_to_comparable(end_date):
            messagebox.showwarning("Внимание", "Дата начала не может быть позже даты конца")
            return
        
        report_data = production_repo.get_production_report(start_date, end_date)
        if not report_data:
            messagebox.showinfo("Информация", "Нет данных о производстве за выбранный период.")
            return
        
        try:
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, suffix='.pdf', prefix='Svodny_otchet_proizvodstvo_cvet_'
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
                alignment=1, spaceAfter=10, leading=16
            )
            cell_style = ParagraphStyle(
                'Cell', fontName=font_name, fontSize=9, leading=11
            )
            
            title_text = f"Сводный отчет (цвет) по производству с {start_date} по {end_date}"
            elements.append(Paragraph(title_text, title_style))
            elements.append(Spacer(1, 0.5*cm))
            
            by_product_color = {}
            for row in report_data:
                prod_id, date, equip_name, prod_name, color_name, quantity_pallets = row
                calc_qty = self._convert_to_units(prod_name, quantity_pallets)
                color = color_name or ''
                if prod_name not in by_product_color:
                    by_product_color[prod_name] = {}
                if color not in by_product_color[prod_name]:
                    by_product_color[prod_name][color] = 0
                by_product_color[prod_name][color] += calc_qty
            
            sorted_products = sorted(by_product_color.keys(), key=lambda p: p.lower())
            table_data = [[
                Paragraph('<b>Продукция</b>', cell_style),
                Paragraph('<b>Цвет</b>', cell_style),
                Paragraph('<b>Общее количество,<br/>шт/м2</b>', cell_style)
            ]]
            data_row_indices = []
            for prod_name in sorted_products:
                colors_dict = by_product_color[prod_name]
                sorted_colors = sorted(colors_dict.keys(), key=self._color_sort_key)
                for color in sorted_colors:
                    qty = colors_dict[color]
                    color_display = color if color else '—'
                    table_data.append([
                        Paragraph(prod_name, cell_style),
                        Paragraph(color_display, cell_style),
                        Paragraph(self._format_number(qty), cell_style)
                    ])
                    data_row_indices.append(len(table_data) - 1)
            
            col_widths = [10*cm, 3.5*cm, 3.5*cm]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table_style = TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('FONTNAME', (0, 0), (-1, 0), font_name),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, 0), 5),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 1), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ])
            for i, idx in enumerate(data_row_indices):
                if i % 2 == 0:
                    table_style.add('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f9f9f9'))
            table.setStyle(table_style)
            elements.append(table)
            
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
            messagebox.showerror("Ошибка", f"Не удалось сформировать сводный отчет (цвет):\n\n{e}")