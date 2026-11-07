"""
Главный файл программы "ООО Евроблок".
[ИЗМЕНЕНО] Упрощена логика завершения — без потоков и TerminateProcess.
"""
import sys
import subprocess
import os
import atexit
import tkinter as tk


# ============================================================================
# ФЛАГ ЗАВЕРШЕНИЯ
# ============================================================================
_exiting = False


def _force_exit():
    """Принудительное завершение процесса."""
    global _exiting
    if _exiting:
        return
    _exiting = True
    
    try:
        from database.connection import close_pool
        close_pool()
    except Exception:
        pass
    
    try:
        from database.cache import query_cache
        query_cache.clear()
    except Exception:
        pass
    
    # Принудительное завершение
    os._exit(0)


# Регистрируем в atexit — вызывается при любом завершении
atexit.register(_force_exit)


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
            _wait_user("Нажмите OK для выхода...")
            sys.exit(1)
    else:
        print("✓ Все необходимые библиотеки установлены")
    
    print()


check_and_install_dependencies()


# ============================================================================
# БЕЗОПАСНЫЙ ВЫВОД СООБЩЕНИЙ
# ============================================================================
def _wait_user(message="Нажмите OK для выхода..."):
    """Безопасно показать сообщение пользователю."""
    if hasattr(sys.stdin, 'isatty') and sys.stdin is not None:
        try:
            if sys.stdin.isatty():
                input(message)
                return
        except (RuntimeError, OSError, AttributeError):
            pass
    
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        temp_root = tk.Tk()
        temp_root.withdraw()
        temp_root.attributes('-topmost', True)
        
        messagebox.showinfo("Евроблок", message)
        
        temp_root.destroy()
    except Exception:
        import time
        print(message)
        time.sleep(5)


# ============================================================================
# ИМПОРТЫ
# ============================================================================
from tkinter import messagebox
from config.settings import COLORS, FONTS
from database.connection import (
    init_database, close_pool, get_database_info,
    database_exists, validate_database, DB_PATH, CURRENT_DB_VERSION
)


# ============================================================================
# ПУТЬ К ПАПКЕ КОНФИГУРАЦИИ
# ============================================================================
def _get_config_dir():
    """Получить папку с конфигурацией"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# ПРОВЕРКА ПЕРВОГО ЗАПУСКА И МАСТЕР НАСТРОЙКИ
# ============================================================================
def check_first_run_and_setup(root):
    """Проверить первый запуск и запустить мастер настройки."""
    config_dir = _get_config_dir()
    
    try:
        from ui.windows.setup_wizard import is_first_run, run_setup_wizard
    except ImportError as e:
        print(f"⚠ Модуль мастера настройки не найден: {e}")
        return True
    
    if not is_first_run(config_dir):
        return True
    
    print("→ Обнаружен первый запуск программы")
    print("→ Запуск мастера настройки...")
    print()
    
    root.withdraw()
    root.update()
    
    try:
        result = run_setup_wizard(root, config_dir)
    except Exception as e:
        print(f"✗ Ошибка мастера настройки: {e}")
        import traceback
        traceback.print_exc()
        result = None
    finally:
        try:
            root.deiconify()
            root.update()
        except tk.TclError:
            pass
    
    if result is None:
        print("✗ Настройка отменена пользователем")
        return False
    
    print(f"✓ Настройка завершена: {result}")
    return True


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
    """Очистить файл уведомлений при старте."""
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
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================
def main():
    """Основная функция запуска программы"""
    root = None
    
    try:
        # Вывод информации о режиме работы
        from client_config import MODE, print_mode_info, NETWORK_DB_PATH, check_db_available
        print_mode_info()
        print()
        
        # Очистка устаревших данных
        cleanup_stale_locks_on_startup()
        cleanup_notification_file_on_startup()
        
        # Инициализация БД
        init_database()
        
        # ====================================================================
        # Создаём ОДИН root на всё приложение
        # ====================================================================
        root = tk.Tk()
        
        # Проверяем первый запуск (мастер настроек)
        if not check_first_run_and_setup(root):
            try:
                root.destroy()
            except:
                pass
            print("Программа завершена.")
            os._exit(0)
        
        # Гарантированно показываем root после мастера
        try:
            root.deiconify()
            root.state('zoomed')
            root.lift()
            root.focus_force()
            root.update()
        except tk.TclError:
            pass
        
        # Проверка доступности БД (для сетевого режима)
        if MODE == 'network':
            check = check_db_available()
            if not check['available']:
                result = messagebox.askretrycancel(
                    "База данных недоступна",
                    f"{check['error']}\n\n"
                    f"Путь: {DB_PATH}\n\n"
                    f"Повторить попытку подключения?",
                    parent=root
                )
                if not result:
                    _reset_settings(root)
                    return
                else:
                    check = check_db_available()
                    if not check['available']:
                        messagebox.showerror(
                            "Ошибка подключения",
                            f"Не удалось подключиться к базе данных.\n\n{check['error']}",
                            parent=root
                        )
                        root.destroy()
                        os._exit(1)
        
        # Загрузка логотипа и установка иконки
        from utils.resources import load_logo, set_window_icon
        logo_image = load_logo()
        if logo_image:
            set_window_icon(root, logo_image)
            print(f"✓ Логотип загружен и установлен как иконка окна")
        
        # Заголовок окна с информацией о режиме
        if MODE == 'network':
            db_name = os.path.basename(NETWORK_DB_PATH) if NETWORK_DB_PATH else 'сеть'
            root.title(f"ООО Евроблок [СЕТЬ: {db_name}]")
        else:
            root.title("ООО Евроблок - производство и финансы")
        
        # ====================================================================
        # Запуск приложения
        # ====================================================================
        from ui.main_window import EuroblockApp
        app = EuroblockApp(root, logo_image=logo_image)
        
        # Запускаем главный цикл
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"⚠ Ошибка в mainloop: {e}")
        
        print("→ Завершение работы программы...")
        
    except PermissionError as e:
        print()
        print("=" * 70)
        print("ОШИБКА БЛОКИРОВКИ ФАЙЛА")
        print("=" * 70)
        print()
        print(f"Файл базы данных заблокирован:\n{e}")
        print()
        _wait_user("Нажмите OK для выхода...")
        os._exit(1)
        
    except Exception as e:
        print()
        print("=" * 70)
        print("КРИТИЧЕСКАЯ ОШИБКА")
        print("=" * 70)
        print()
        print(f"Произошла ошибка при запуске программы:\n{e}")
        print()
        import traceback
        traceback.print_exc()
        print()
        
        _wait_user("Нажмите OK для выхода...")
        os._exit(1)
    
    # ========================================================================
    # ГАРАНТИРОВАННОЕ ЗАВЕРШЕНИЕ ПОСЛЕ MAINLOOP
    # ========================================================================
    # Закрываем пул соединений
    try:
        close_pool()
    except Exception:
        pass
    
    # Принудительное завершение процесса
    os._exit(0)


def _reset_settings(root):
    """Сбросить настройки и запустить мастер заново"""
    config_dir = _get_config_dir()
    config_file = os.path.join(config_dir, 'network_config.ini')
    marker_file = os.path.join(config_dir, '.first_run_done')
    
    try:
        if os.path.exists(config_file):
            os.remove(config_file)
        if os.path.exists(marker_file):
            os.remove(marker_file)
        print("✓ Настройки сброшены")
    except Exception as e:
        print(f"✗ Ошибка сброса настроек: {e}")
    
    print("→ Перезапуск программы...")
    
    try:
        close_pool()
    except Exception:
        pass
    
    try:
        root.destroy()
    except:
        pass
    
    python = sys.executable
    script = sys.argv[0]
    os.execl(python, python, script)


if __name__ == "__main__":
    main()