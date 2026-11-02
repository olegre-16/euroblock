"""
Утилиты для работы с PDF.
Кэширование шрифтов, общие функции для генерации отчётов.
"""
import os
import sys
import tempfile
import subprocess
from typing import Optional


# ============================================================================
# КЭШИРОВАНИЕ ШРИФТОВ
# ============================================================================

_font_cache = {}


def get_cyrillic_font() -> str:
    """
    Получить имя кириллического шрифта с кэшированием.
    
    Пытается найти системный шрифт с поддержкой кириллицы.
    Результат кэшируется для ускорения повторных вызовов.
    
    Returns:
        Имя зарегистрированного шрифта
    """
    if 'cyrillic' in _font_cache:
        return _font_cache['cyrillic']
    
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        _font_cache['cyrillic'] = 'Helvetica'
        return 'Helvetica'
    
    # Список возможных путей к шрифтам
    font_paths = []
    
    # Windows
    if os.name == 'nt':
        font_paths.extend([
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/Arial.ttf',
            'C:/Windows/Fonts/times.ttf',
            'C:/Windows/Fonts/calibri.ttf',
        ])
    # Linux
    elif os.name == 'posix':
        font_paths.extend([
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
        ])
    # macOS
    elif sys.platform == 'darwin':
        font_paths.extend([
            '/System/Library/Fonts/Helvetica.ttc',
            '/Library/Fonts/Arial.ttf',
        ])
    
    # Пытаемся зарегистрировать первый найденный шрифт
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                _font_cache['cyrillic'] = 'CyrillicFont'
                return 'CyrillicFont'
            except Exception:
                continue
    
    # Если не нашли — используем Helvetica (без кириллицы)
    _font_cache['cyrillic'] = 'Helvetica'
    return 'Helvetica'


# ============================================================================
# СОЗДАНИЕ ВРЕМЕННЫХ ФАЙЛОВ
# ============================================================================

def create_temp_pdf(prefix: str = 'report_') -> str:
    """
    Создать временный файл для PDF.
    
    Args:
        prefix: префикс имени файла
    
    Returns:
        Путь к созданному файлу
    """
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix='.pdf',
        prefix=prefix
    )
    temp_file.close()
    return temp_file.name


def cleanup_temp_file(file_path: str):
    """
    Удалить временный файл.
    
    Args:
        file_path: путь к файлу
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Не удалось удалить временный файл {file_path}: {e}")


# ============================================================================
# ОТКРЫТИЕ PDF
# ============================================================================

def open_pdf(file_path: str) -> bool:
    """
    Открыть PDF-файл в системном просмотрщике.
    
    Args:
        file_path: путь к PDF-файлу
    
    Returns:
        True, если файл успешно открыт, иначе False
    """
    try:
        if os.name == 'nt':  # Windows
            os.startfile(file_path)
            return True
        elif os.name == 'posix':  # Linux
            subprocess.call(['xdg-open', file_path])
            return True
        elif sys.platform == 'darwin':  # macOS
            subprocess.call(['open', file_path])
            return True
        else:
            return False
    except Exception as e:
        print(f"Не удалось открыть PDF: {e}")
        return False


# ============================================================================
# ОБЩИЕ СТИЛИ ДЛЯ PDF
# ============================================================================

def get_common_styles(font_name: str):
    """
    Получить общие стили для PDF-отчётов.
    
    Args:
        font_name: имя шрифта
    
    Returns:
        Словарь со стилями
    """
    from reportlab.lib.styles import ParagraphStyle
    
    return {
        'title': ParagraphStyle(
            'Title',
            fontName=font_name,
            fontSize=14,
            alignment=1,  # По центру
            spaceAfter=5,
            leading=16
        ),
        'subtitle': ParagraphStyle(
            'Subtitle',
            fontName=font_name,
            fontSize=10,
            alignment=1,
            spaceAfter=10,
            leading=12
        ),
        'month_title': ParagraphStyle(
            'MonthTitle',
            fontName=font_name,
            fontSize=11,
            alignment=0,
            spaceAfter=3,
            spaceBefore=8,
            leading=13
        ),
        'product_title': ParagraphStyle(
            'ProductTitle',
            fontName=font_name,
            fontSize=10,
            alignment=0,
            spaceAfter=2,
            spaceBefore=5,
            leading=12
        ),
        'cell': ParagraphStyle(
            'Cell',
            fontName=font_name,
            fontSize=8,
            leading=9
        ),
        'cell_small': ParagraphStyle(
            'CellSmall',
            fontName=font_name,
            fontSize=7,
            leading=8
        ),
    }


# ============================================================================
# ФОРМАТИРОВАНИЕ ЧИСЕЛ
# ============================================================================

def format_number(value, decimals: int = 0) -> str:
    """
    Форматировать число для отображения.
    
    Args:
        value: число
        decimals: количество знаков после запятой
    
    Returns:
        Отформатированная строка
    """
    if value is None or value == '':
        return '0'
    
    try:
        num = float(value)
        
        if decimals == 0:
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:g}"
        else:
            return f"{num:.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_money(value) -> str:
    """
    Форматировать денежную сумму.
    
    Args:
        value: число
    
    Returns:
        Отформатированная строка с двумя знаками после запятой
    """
    return format_number(value, decimals=2)


# ============================================================================
# ЦВЕТА ДЛЯ ТАБЛИЦ
# ============================================================================

class TableColors:
    """Стандартные цвета для оформления таблиц в PDF"""
    
    HEADER_BG = '#ffffff'        # Белый фон заголовка
    HEADER_TEXT = '#000000'      # Чёрный текст заголовка
    ROW_EVEN_BG = '#f9f9f9'      # Светло-серый для чётных строк
    ROW_ODD_BG = '#ffffff'       # Белый для нечётных строк
    TOTAL_BG = '#ecf0f1'         # Бледно-серый для итогов
    GRAND_TOTAL_BG = '#d5dbdb'   # Более тёмный серый для общих итогов
    GRID_COLOR = '#808080'       # Серый цвет сетки
    BORDER_COLOR = '#000000'     # Чёрный цвет границ
    
    @classmethod
    def get_hex(cls, color_name: str) -> str:
        """Получить HEX-код цвета по имени"""
        return getattr(cls, color_name.upper(), '#ffffff')