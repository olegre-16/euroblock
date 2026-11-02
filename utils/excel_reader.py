"""
Парсер XLSX файлов на стандартных библиотеках Python.
Не требует установки openpyxl или других внешних библиотек.
"""
import zipfile
import xml.etree.ElementTree as ET


NAMESPACES = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


def _column_index_from_cell_ref(cell_ref):
    """Извлечь индекс колонки из ссылки на ячейку (A1 -> 0, B2 -> 1)"""
    letters = ''.join(c for c in cell_ref if c.isalpha()).upper()
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1


def _load_shared_strings(zf):
    """Загрузить общие строки из XLSX"""
    shared_strings = []
    if 'xl/sharedStrings.xml' in zf.namelist():
        with zf.open('xl/sharedStrings.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            
            for si in root.findall(f'{{{NAMESPACES["main"]}}}si'):
                text_parts = []
                for t in si.iter(f'{{{NAMESPACES["main"]}}}t'):
                    if t.text:
                        text_parts.append(t.text)
                shared_strings.append(''.join(text_parts))
    return shared_strings


def _get_active_sheet_file(zf):
    """Определить файл активного листа"""
    sheet_file = 'xl/worksheets/sheet1.xml'
    
    if 'xl/workbook.xml' in zf.namelist():
        try:
            with zf.open('xl/workbook.xml') as f:
                wb_tree = ET.parse(f)
                wb_root = wb_tree.getroot()
                
                sheets = wb_root.findall(f'{{{NAMESPACES["main"]}}}sheets/{{{NAMESPACES["main"]}}}sheet')
                if sheets:
                    first_sheet = sheets[0]
                    sheet_id = first_sheet.get(f'{{{NAMESPACES["r"]}}}id')
                    
                    if sheet_id and 'xl/_rels/workbook.xml.rels' in zf.namelist():
                        with zf.open('xl/_rels/workbook.xml.rels') as f:
                            rels_tree = ET.parse(f)
                            rels_root = rels_tree.getroot()
                            
                            for rel in rels_root:
                                if rel.get('Id') == sheet_id:
                                    target = rel.get('Target')
                                    if target:
                                        sheet_file = 'xl/' + target.lstrip('/')
                                    break
        except Exception:
            pass
    
    return sheet_file


def _parse_cell_value(cell, shared_strings):
    """Извлечь значение из ячейки"""
    cell_type = cell.get('t', '')
    value_elem = cell.find(f'{{{NAMESPACES["main"]}}}v')
    
    if value_elem is None or value_elem.text is None:
        return None
    
    if cell_type == 's':
        try:
            idx = int(value_elem.text)
            if 0 <= idx < len(shared_strings):
                return shared_strings[idx]
        except ValueError:
            return None
    elif cell_type == 'inlineStr':
        is_elem = cell.find(f'{{{NAMESPACES["main"]}}}is')
        if is_elem is not None:
            text_parts = []
            for t in is_elem.iter(f'{{{NAMESPACES["main"]}}}t'):
                if t.text:
                    text_parts.append(t.text)
            return ''.join(text_parts)
    else:
        return value_elem.text
    
    return None


def read_xlsx_first_column(file_path):
    """Прочитать первую колонку из XLSX файла"""
    values = []
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            shared_strings = _load_shared_strings(zf)
            sheet_file = _get_active_sheet_file(zf)
            
            if sheet_file not in zf.namelist():
                raise ValueError(f"Файл листа {sheet_file} не найден в архиве")
            
            with zf.open(sheet_file) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                rows = root.findall(f'{{{NAMESPACES["main"]}}}sheetData/{{{NAMESPACES["main"]}}}row')
                
                for row in rows:
                    first_cell_value = None
                    
                    for cell in row.findall(f'{{{NAMESPACES["main"]}}}c'):
                        cell_ref = cell.get('r', '')
                        col_index = _column_index_from_cell_ref(cell_ref)
                        
                        if col_index == 0:
                            first_cell_value = _parse_cell_value(cell, shared_strings)
                            break
                    
                    if first_cell_value is not None and str(first_cell_value).strip():
                        values.append(str(first_cell_value))
    
    except zipfile.BadZipFile:
        raise ValueError("Файл не является валидным ZIP/XLSX архивом")
    except KeyError as e:
        raise ValueError(f"Файл повреждён или имеет неверную структуру: {e}")
    except ET.ParseError as e:
        raise ValueError(f"Ошибка разбора XML в файле: {e}")
    
    return values


def read_xlsx_rows(file_path, max_columns=None):
    """
    Прочитать несколько колонок из XLSX файла.
    
    Args:
        file_path: путь к .xlsx файлу
        max_columns: максимальное количество колонок для чтения (None — все)
    
    Returns:
        list: список строк, где каждая строка — список значений
    """
    rows_data = []
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zf:
            shared_strings = _load_shared_strings(zf)
            sheet_file = _get_active_sheet_file(zf)
            
            if sheet_file not in zf.namelist():
                raise ValueError(f"Файл листа {sheet_file} не найден в архиве")
            
            with zf.open(sheet_file) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                rows = root.findall(f'{{{NAMESPACES["main"]}}}sheetData/{{{NAMESPACES["main"]}}}row')
                
                for row in rows:
                    row_values = {}
                    
                    for cell in row.findall(f'{{{NAMESPACES["main"]}}}c'):
                        cell_ref = cell.get('r', '')
                        col_index = _column_index_from_cell_ref(cell_ref)
                        
                        if max_columns is not None and col_index >= max_columns:
                            continue
                        
                        value = _parse_cell_value(cell, shared_strings)
                        if value is not None:
                            row_values[col_index] = str(value)
                    
                    if row_values:
                        # Определяем максимальный индекс колонки в этой строке
                        max_idx = max(row_values.keys())
                        row_list = [row_values.get(i, '') for i in range(max_idx + 1)]
                        
                        # Проверяем, что строка не полностью пустая
                        if any(str(v).strip() for v in row_list):
                            rows_data.append(row_list)
    
    except zipfile.BadZipFile:
        raise ValueError("Файл не является валидным ZIP/XLSX архивом")
    except KeyError as e:
        raise ValueError(f"Файл повреждён или имеет неверную структуру: {e}")
    except ET.ParseError as e:
        raise ValueError(f"Ошибка разбора XML в файле: {e}")
    
    return rows_data


def is_xlsx_file(file_path):
    """Проверить, является ли файл XLSX"""
    return file_path.lower().endswith('.xlsx')