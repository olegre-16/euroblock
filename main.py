"""
Главный файл программы "ООО Евроблок"
Автоматически проверяет и устанавливает reportlab при запуске.
Поддержка многопользовательского режима.
При запуске программа:
- Проверяет наличие БД в папке программы
- Если БД есть — использует существующую (данные сохраняются)
- Если БД нет — создаёт новую (первый запуск)
- Если БД повреждена — создаёт бэкап и новую БД
- Загружает логотип и устанавливает его как иконку окна
"""
import sys
import subprocess
import os
import atexit

# ============================================================================
# ПРОВЕРКА И УСТАНОВКА ЗАВИСИМОСТЕЙ
# ============================================================================
def check_and_install_dependencies():
    """Проверить наличие reportlab и установить при отсутствии"""
    print("=" * 70)
    print("ООО Евроблок - Проверка зависимостей")
    print("=" * 70)
    print()
    try:
        import reportlab
        print(f"✓ reportlab - установлена (версия {reportlab.Version})")
        missing = False
    except ImportError:
        print("✗ reportlab - НЕ установлена")
        missing = True
    print()
    if missing:
        print("Обнаружена отсутствующая библиотека: reportlab")
        print("Выполняется автоматическая установка...")
        print()
        print("Установка reportlab...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "reportlab", "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✓ reportlab успешно установлена")
            print()
            print("=" * 70)
            print("✓ Все зависимости успешно установлены!")
            print("=" * 70)
            print()
        except subprocess.CalledProcessError:
            print("✗ Ошибка при установке reportlab")
            print()
            print("=" * 70)
            print("ОШИБКА УСТАНОВКИ")
            print("=" * 70)
            print()
            print("Не удалось автоматически установить библиотеку reportlab.")
            print()
            print("Возможные причины:")
            print("  1. Отсутствует интернет-соединение")
            print("  2. Недостаточно прав для установки")
            print("  3. Блокировка антивирусом или сетевым экраном")
            print()
            print("Решение:")
            print("  1. Проверьте интернет-соединение")
            print("  2. Запустите программу от имени администратора")
            print("  3. Установите библиотеку вручную командой:")
            print("     pip install reportlab")
            print()
            input("Нажмите Enter для выхода...")
            sys.exit(1)
    else:
        print("✓ Все необходимые библиотеки установлены")
        print()
    print("Запуск программы...")
    print()

# Запускаем проверку
check_and_install_dependencies()

# ============================================================================
# ИМПОРТЫ
# ============================================================================
import tkinter as tk
from tkinter import messagebox
from config.settings import COLORS, FONTS
from database.connection import (
    init_database, close_pool, get_database_info,
    database_exists, validate_database, DB_PATH, CURRENT_DB_VERSION
)
from ui.main_window import EuroblockApp

# ============================================================================
# [НОВОЕ] ОЧИСТКА БЛОКИРОВОК ПРИ СТАРТЕ
# ============================================================================
def cleanup_stale_locks_on_startup():
    """
    Очистить устаревшие блокировки при запуске программы.
    Это решает проблему, когда после аварийного завершения программы
    блокировки остаются в файле и мешают работе.
    """
    try:
        from database.locking import get_lock_manager
        lock_manager = get_lock_manager(DB_PATH)
        # Очищаем блокировки старше 5 минут (300 секунд)
        lock_manager.cleanup_stale_locks(max_age=300)
        print("✓ Устаревшие блокировки очищены")
    except Exception as e:
        print(f"⚠ Не удалось очистить блокировки: {e}")

# ============================================================================
# [НОВОЕ] ОЧИСТКА ФАЙЛА УВЕДОМЛЕНИЙ ПРИ СТАРТЕ
# ============================================================================
def cleanup_notification_file_on_startup():
    """
    Очистить файл уведомлений при старте, если он слишком большой.
    Предотвращает накопление старых уведомлений.
    """
    try:
        notification_file = DB_PATH + '.notifications'
        if os.path.exists(notification_file):
            size = os.path.getsize(notification_file)
            # Если файл больше 1 МБ — очищаем
            if size > 1024 * 1024:
                os.remove(notification_file)
                print(f"✓ Файл уведомлений очищен (был {size / 1024:.1f} КБ)")
    except Exception as e:
        print(f"⚠ Не удалось очистить файл уведомлений: {e}")

# ============================================================================
# ДИАГНОСТИКА
# ============================================================================
def run_diagnostics():
    """Запустить диагностику производительности"""
    import time
    print("\n" + "=" * 70)
    print("ДИАГНОСТИКА ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 70)
    try:
        info = get_database_info()
        print(f"\nБаза данных: {info['path']}")
        print(f"Размер: {info['size_mb']} МБ")
        print(f"Версия БД: {info['version']}")
        print(f"Таблиц: {info['tables_count']}")
        print("\nКоличество записей:")
        for table, count in info['table_stats'].items():
            print(f"  {table}: {count}")
    except Exception as e:
        print(f"Ошибка получения информации о БД: {e}")
    
    print("\nПроверка целостности БД...")
    validation = validate_database()
    print(f"  Существует: {validation['exists']}")
    print(f"  Валидна: {validation['valid']}")
    print(f"  Целостность: {validation['integrity']}")
    print(f"  Версия: {validation['version']}")
    if validation['error']:
        print(f"  Ошибка: {validation['error']}")
    
    print("\nТест скорости чтения...")
    try:
        from database.repositories import sales_repo
        start = time.time()
        data = sales_repo.get_all()
        duration = time.time() - start
        print(f"  Прочитано {len(data)} записей за {duration:.3f} сек")
        if duration > 0:
            print(f"  Скорость: {len(data)/duration:.0f} записей/сек")
    except Exception as e:
        print(f"  Ошибка: {e}")
    
    try:
        from database.cache import query_cache
        stats = query_cache.get_stats()
        print(f"\nСтатистика кэша:")
        print(f"  Размер: {stats['size']} / {stats['max_size']}")
        print(f"  Попаданий: {stats['hits']}")
        print(f"  Промахов: {stats['misses']}")
        print(f"  Процент попаданий: {stats['hit_rate']}%")
    except Exception as e:
        print(f"Ошибка получения статистики кэша: {e}")
    
    print("\n" + "=" * 70)

# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================
def main():
    """Основная функция запуска программы"""
    try:
        if '--diagnostics' in sys.argv:
            run_diagnostics()
            return
        
        print()
        if database_exists():
            print(f"✓ База данных найдена: {DB_PATH}")
            print(f"  Размер: {os.path.getsize(DB_PATH) / (1024*1024):.2f} МБ")
            print()
        else:
            print(f"→ База данных не найдена (первый запуск)")
            print(f"  Будет создана новая БД: {DB_PATH}")
            print()
        
        # ====================================================================
        # [НОВОЕ] Очистка устаревших данных при запуске
        # ====================================================================
        cleanup_stale_locks_on_startup()
        cleanup_notification_file_on_startup()
        
        init_database()
        atexit.register(close_pool)
        
        # ====================================================================
        # ЗАПУСК ГРАФИЧЕСКОГО ИНТЕРФЕЙСА
        # ====================================================================
        root = tk.Tk()
        
        # ===== ЗАГРУЗКА ЛОГОТИПА И УСТАНОВКА ИКОНКИ ОКНА =====
        from utils.resources import load_logo, set_window_icon
        
        # Загружаем оригинальный логотип
        logo_image = load_logo()
        if logo_image:
            # Устанавливаем логотип как иконку окна
            set_window_icon(root, logo_image)
            print(f"✓ Логотип загружен и установлен как иконка окна")
            print(f"  Размер логотипа: {logo_image.width()}x{logo_image.height()} px")
        else:
            print("⚠ Логотип не найден, используется стандартная иконка")
        
        # =========================================================
        # Запуск приложения
        app = EuroblockApp(root, logo_image=logo_image)
        root.mainloop()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("КРИТИЧЕСКАЯ ОШИБКА")
        print("=" * 70)
        print()
        print(f"Произошла ошибка при запуске программы:\n{e}")
        print()
        if 'database' in str(e).lower() or 'sqlite' in str(e).lower():
            print("Возможные решения:")
            print("  1. Закройте все экземпляры программы")
            print("  2. Проверьте, что файл euroblock.db не повреждён")
            print("  3. При необходимости удалите файл euroblock.db")
            print("     (все данные будут потеряны!)")
            print()
        print("Если проблема сохраняется, обратитесь к разработчику.")
        print()
        input("Нажмите Enter для выхода...")
        sys.exit(1)

if __name__ == "__main__":
    main()