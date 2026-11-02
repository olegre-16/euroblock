"""
Модуль для работы с ресурсами программы (логотипы, иконки).
Корректно определяет пути как при запуске из исходного кода, так и из EXE.
"""
import os
import sys
import tkinter as tk
from tkinter import PhotoImage


def get_assets_dir():
    """
    Получить путь к папке assets.
    - При запуске из EXE — папка рядом с EXE-файлом
    - При запуске из скрипта — папка assets в корне проекта
    """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    assets_path = os.path.join(base_path, 'assets')
    
    if not os.path.exists(assets_path):
        os.makedirs(assets_path, exist_ok=True)
    
    return assets_path


def get_logo_path():
    """Получить путь к файлу логотипа (PNG)"""
    return os.path.join(get_assets_dir(), 'logo.png')


def get_icon_path():
    """Получить путь к файлу иконки окна (.ico)"""
    return os.path.join(get_assets_dir(), 'icon.ico')


def load_logo():
    """
    Загрузить оригинальный логотип программы (PNG).
    
    Returns:
        PhotoImage объект или None, если логотип не найден
    """
    logo_path = get_logo_path()
    
    if not os.path.exists(logo_path):
        print(f"⚠ Логотип не найден: {logo_path}")
        return None
    
    try:
        image = PhotoImage(file=logo_path)
        return image
    except tk.TclError as e:
        print(f"⚠ Ошибка загрузки логотипа: {e}")
        return None


def resize_logo(image, target_height):
    """
    Масштабировать логотип пропорционально до нужной высоты.
    
    Args:
        image: исходный PhotoImage
        target_height: целевая высота в пикселях
    
    Returns:
        Новый PhotoImage с нужной высотой или None
    """
    if image is None:
        return None
    
    orig_height = image.height()
    orig_width = image.width()
    
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
        new_image = image.zoom(best_zoom, best_zoom).subsample(best_subsample, best_subsample)
        return new_image
    except tk.TclError as e:
        print(f"⚠ Ошибка масштабирования логотипа: {e}")
        return image


def set_window_icon(window, logo_image):
    """
    Установить иконку для окна Tkinter.
    Меняет стандартную иконку Python на логотип программы.
    
    Приоритет:
    1. PhotoImage (если передан logo_image)
    2. .ico файл (если есть icon.ico)
    3. Ничего (остаётся стандартная иконка)
    
    Args:
        window: окно Tk или Toplevel
        logo_image: PhotoImage с логотипом (опционально)
    """
    # Сначала пробуем PhotoImage
    if logo_image is not None:
        try:
            window.iconphoto(True, logo_image)
            return
        except tk.TclError:
            pass
    
    # Fallback: пробуем .ico файл
    icon_path = get_icon_path()
    if os.path.exists(icon_path):
        try:
            window.iconbitmap(icon_path)
            return
        except tk.TclError:
            pass
    
    # Если ничего не получилось — остаётся стандартная иконка
    print("⚠ Не удалось установить иконку окна")