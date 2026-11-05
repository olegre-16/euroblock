"""
Главный файл программы "ООО Евроблок".
[ИЗМЕНЕНО] Добавлена проверка первого запуска и мастер настройки.
"""
import sys
import subprocess
import os
import atexit
import tkinter as tk


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
        
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "reportlab", "--quiet"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("✓ reportlab успешно установлена")
        except subprocess.CalledProcessError:
            print("✗ Ошибка при установке reportlab")
            input("Нажмите Enter для выхода...")
            sys.exit(1)
    else:
        print("✓ Все необходимые библиотеки установлены")
    
    print()


check_and_install_dependencies()


# ============================================================================
# [НОВОЕ] ПРОВЕРКА ПЕРВОГО ЗАПУСКА И МАСТЕР НАСТРОЙКИ
# ============================================================================
def _get_config_dir():
    """Получить папку с конфигурацией"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def check_first_run_and_setup():
    """
    Проверить первый запуск и запустить мастер настройки.
    Возвращает True, если настройка прошла успешно.
    """
    config_dir = _get_config_dir()
    
    # Импортируем модуль проверки первого запуска
    try:
        from ui.windows.setup_wizard import is_first_run, run_setup_wizard
    except ImportError:
        # Если модуль не найден — пропускаем мастер
        return True
    
    if not is_first_run(config_dir):
        # Уже настроено — пропускаем
        return True
    
    # Первый запуск — показываем мастер настройки
    print("→ Обнаружен первый запуск программы")
    print("→ Запуск мастера настройки...")
    print()
    
    # Создаём временное окно для мастера
    temp_root = tk.Tk()
    temp_root.withdraw()  # Скрываем главное окно
    temp_root.title("Евроблок — первоначальная настройка")
    
    # Запускаем мастер
    result = run_setup_wizard(temp_root, config_dir)
    
    temp_root.destroy()
    
    if result is None:
        # Пользователь отменил настройку
        print("✗ Настройка отменена пользователем")
        return False
    
    print(f"✓ Настройка завершена: {result}")
    return True


# ============================================================================
# ИМПОРТЫ
# ============================================================================
from tkinter import messagebox
from config.settings import COLORS, FONTS
from database.connection import (
    init_database, close_pool, get_database_info,
    database_exists, validate_database, DB_PATH, CURRENT_DB_VERSION
)
from ui.main_window import EuroblockApp


# ============================================================================
# ОЧИСТКА ПРИ СТАРТЕ
# ============================================================================
def cleanup_stale_locks_on_startup():
    """Очистить устаревшие блокировки при запуске программы."""
    try:
        from database.locking import get_lock_manager
        lock_manager = get_lock_manager(DB_PATH)
        lock_manager.cleanup_stale_locks(max_age=300)
        print("✓ Устаревшие блокировки очищены")
    except Exception as e:
        print(f"⚠ Не удалось очистить блокировки: {e}")


def cleanup_notification_file_on_startup():
    """Очистить файл уведомлений при старте, если он слишком большой."""
    try:
        notification_file = DB_PATH + '.notifications'
        if os.path.exists(notification_file):
            size = os.path.getsize(notification_file)
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
    except Exception as e:
        print(f"Ошибка: {e}")
    
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
        
        # [НОВОЕ] Проверка первого запуска и мастер настройки
        if not check_first_run_and_setup():
            print("✗ Настройка не завершена. Завершение работы.")
            return
        
        # Вывод информации о режиме работы
        from client_config import MODE, print_mode_info, check_main_computer_available
        print_mode_info()
        print()
        
        # [НОВОЕ] Проверка доступности основного компьютера
        if MODE == 'network':
            check = check_main_computer_available()
            if not check['available']:
                # Основной компьютер недоступен
                temp_root = tk.Tk()
                temp_root.withdraw()
                
                result = messagebox.askretrycancel(
                    "Основной компьютер недоступен",
                    f"{check['error']}\n\n"
                    f"Путь: {DB_PATH}\n\n"
                    f"Повторить попытку подключения?"
                )
                
                temp_root.destroy()
                
                if not result:
                    # Пользователь хочет изменить настройки
                    _reset_settings()
                    return
                else:
                    # Повторная проверка
                    check = check_main_computer_available()
                    if not check['available']:
                        messagebox.showerror(
                            "Ошибка подключения",
                            f"Не удалось подключиться к основному компьютеру.\n\n"
                            f"{check['error']}"
                        )
                        return
        
        # Определяем путь к БД для отображения
        print()
        if database_exists():
            print(f"✓ База данных найдена: {DB_PATH}")
            try:
                print(f"  Размер: {os.path.getsize(DB_PATH) / (1024*1024):.2f} МБ")
            except:
                pass
        else:
            print(f"→ База данных не найдена (первый запуск)")
            print(f"  Будет создана новая БД: {DB_PATH}")
        
        print()
        
        # Очистка устаревших данных
        cleanup_stale_locks_on_startup()
        cleanup_notification_file_on_startup()
        
        init_database()
        atexit.register(close_pool)
        
        # ====================================================================
        # ЗАПУСК ГРАФИЧЕСКОГО ИНТЕРФЕЙСА
        # ====================================================================
        root = tk.Tk()
        
        # Загрузка логотипа
        from utils.resources import load_logo, set_window_icon
        logo_image = load_logo()
        if logo_image:
            set_window_icon(root, logo_image)
        
        # Заголовок окна с информацией о режиме
        if MODE == 'network':
            db_name = os.path.basename(DB_PATH)
            role = "ОСНОВНОЙ" if check.get('is_main', False) else "КЛИЕНТ"
            root.title(f"ООО Евроблок [{role}]")
        else:
            root.title("ООО Евроблок - производство и финансы")
        
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
        input("Нажмите Enter для выхода...")
        sys.exit(1)


def _reset_settings():
    """Сбросить настройки и запустить мастер заново"""
    config_dir = _get_config_dir()
    config_file = os.path.join(config_dir, 'network_config.ini')
    marker_file = os.path.join(config_dir, '.first_run_done')
    
    # Удаляем файлы конфигурации
    try:
        if os.path.exists(config_file):
            os.remove(config_file)
        if os.path.exists(marker_file):
            os.remove(marker_file)
        print("✓ Настройки сброшены")
    except Exception as e:
        print(f"✗ Ошибка сброса настроек: {e}")
    
    # Перезапускаем программу
    print("→ Перезапуск программы...")
    python = sys.executable
    script = sys.argv[0]
    os.execl(python, python, script)


if __name__ == "__main__":
    main()