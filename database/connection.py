"""
Модуль подключения и инициализации базы данных.
Поддержка многопользовательского режима через сетевой диск.
Все компьютеры равноправны — любой подключается к общей БД.

[ИЗМЕНЕНО]
- Поддержка сетевого пути к БД через client_config
- Для сетевого режима используется journal_mode=DELETE (вместо WAL)
  — это критически важно для стабильной работы по сети!
- Для локального режима используется journal_mode=WAL (быстрее)
- cache_size=0 в сетевом режиме — отключение кэша SQLite
- get_connection() всегда проверяет изменения БД в сетевом режиме
- DBSyncMonitor.check_for_changes(force=True) — принудительная проверка
- Увеличенные таймауты и число повторных попыток для сети
- Обработка "disk I/O error" с повторными попытками
- Синхронизация кэша между клиентами через DBSyncMonitor
- Очистка файлов блокировки при запуске (release_db_locks)
- Retry-логика для сетевого режима (safe_connect)
- Безопасный вывод ошибок (_show_error_and_exit)
- Обработка PermissionError при создании/удалении БД
- Упрощённый close_pool() для гарантированного завершения
- Миграция 3: таблица reserve_sales_history
- Версия БД обновлена до 1.0.1
"""
import sqlite3
import os
import sys
import threading
import shutil
import time
from datetime import datetime


# ============================================================================
# ОПРЕДЕЛЕНИЕ ПУТИ К БД
# ============================================================================
def get_db_path():
    """
    Получить путь к базе данных.
    Приоритет:
    1. Из client_config (с учётом network_config.ini)
    2. Локальный путь по умолчанию
    """
    try:
        from client_config import DB_PATH as CONFIG_DB_PATH
        return CONFIG_DB_PATH
    except ImportError:
        pass
    
    # Fallback — стандартный путь
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, 'euroblock.db')


# Путь к базе данных
DB_PATH = get_db_path()

# Текущая версия структуры БД (для миграций)
CURRENT_DB_VERSION = '1.0.1'


# ============================================================================
# ПРОВЕРКА ДОСТУПНОСТИ СЕТЕВОГО ПУТИ
# ============================================================================
def check_network_path(db_path: str) -> dict:
    """
    Проверить доступность сетевого пути к БД.
    Возвращает словарь с результатами проверки.
    """
    result = {
        'accessible': False,
        'path': db_path,
        'db_exists': False,
        'db_size': 0,
        'writable': False,
        'error': None
    }
    
    try:
        db_dir = os.path.dirname(db_path)
        
        if not os.path.exists(db_dir):
            result['error'] = f"Сетевая папка недоступна: {db_dir}"
            return result
        
        result['accessible'] = True
        
        if os.path.exists(db_path):
            result['db_exists'] = True
            result['db_size'] = os.path.getsize(db_path)
        
        test_file = os.path.join(db_dir, '.write_test_temp')
        try:
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('test')
            os.remove(test_file)
            result['writable'] = True
        except Exception as e:
            result['error'] = f"Нет прав на запись: {e}"
    
    except Exception as e:
        result['error'] = f"Ошибка проверки: {e}"
    
    return result


# ============================================================================
# ОЧИСТКА БЛОКИРОВОК БД
# ============================================================================
def release_db_locks():
    """
    Очистить файлы блокировки SQLite (.db-wal, .db-shm, .db-journal).
    Вызывается при запуске в локальном режиме, если предыдущий экземпляр
    программы аварийно завершился и оставил заблокированные файлы.
    """
    lock_files = [
        DB_PATH + '-wal',
        DB_PATH + '-shm',
        DB_PATH + '-journal'
    ]
    
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                print(f"  ✓ Удалён файл блокировки: {os.path.basename(lock_file)}")
            except PermissionError:
                print(f"  ⚠ Не удалось удалить {os.path.basename(lock_file)} — файл занят")
            except Exception as e:
                print(f"  ⚠ Ошибка удаления {os.path.basename(lock_file)}: {e}")


# ============================================================================
# БЕЗОПАСНОЕ ПОДКЛЮЧЕНИЕ С ПОВТОРНЫМИ ПОПЫТКАМИ
# ============================================================================
def safe_connect(db_path, timeout=30, max_retries=10):
    """
    Безопасное подключение к БД с повторными попытками.
    - Увеличено число попыток до 10
    - Добавлена обработка "disk I/O error"
    - Для сетевого режима используется journal_mode=DELETE
    - Нарастающий интервал ожидания между попытками
    """
    # Определяем режим работы
    try:
        from client_config import MODE
        is_network = (MODE == 'network')
    except ImportError:
        is_network = False
    
    last_error = None
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(
                db_path, 
                timeout=timeout, 
                check_same_thread=False,
                isolation_level=None  # Авто-коммит для стабильности
            )
            
            if is_network:
                # Для сетевого режима — СТАБИЛЬНАЯ конфигурация
                # journal_mode=DELETE вместо WAL — критически важно для сети!
                conn.execute('PRAGMA journal_mode=DELETE')
                conn.execute(f'PRAGMA busy_timeout={int(timeout * 1000)}')
                conn.execute('PRAGMA cache_size=0')            # Отключение кэша
                conn.execute('PRAGMA synchronous=FULL')        # Максимальная надёжность
                conn.execute('PRAGMA temp_store=MEMORY')
                conn.execute('PRAGMA foreign_keys=ON')
                conn.execute('PRAGMA locking_mode=NORMAL')
                conn.execute('PRAGMA cache_spill=OFF')
            else:
                # Для локального режима — быстрая конфигурация с WAL
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute(f'PRAGMA busy_timeout={int(timeout * 1000)}')
                conn.execute('PRAGMA cache_size=10000')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA temp_store=MEMORY')
                conn.execute('PRAGMA foreign_keys=ON')
            
            # Проверяем работоспособность соединения
            conn.execute('SELECT 1')
            return conn
            
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            last_error = e
            error_msg = str(e).lower()
            # Повторяем попытки при "disk I/O error", "locked" или "unable to open"
            if 'disk i/o' in error_msg or 'locked' in error_msg or 'unable to open' in error_msg:
                wait_time = min(2 + attempt, 10)  # Нарастающий интервал ожидания
                print(f"  ⚠ Попытка {attempt + 1}/{max_retries}: {e}, ждём {wait_time}с...")
                time.sleep(wait_time)
            else:
                raise
        except PermissionError as e:
            last_error = e
            print(f"  ⚠ Попытка {attempt + 1}/{max_retries}: Нет доступа к файлу, ждём...")
            time.sleep(2)
    
    raise sqlite3.OperationalError(
        f"Не удалось подключиться к БД после {max_retries} попыток: {last_error}"
    )


# ============================================================================
# СИНХРОНИЗАЦИЯ КЭША МЕЖДУ КЛИЕНТАМИ
# ============================================================================
class DBSyncMonitor:
    """
    Монитор изменений БД для синхронизации кэша между клиентами.
    Проверяет timestamp файла БД и инвалидирует кэш при изменениях.
    Используется в многопользовательском режиме, чтобы все компьютеры
    видели изменения друг друга.
    """
    def __init__(self, db_path, check_interval=2):
        self.db_path = db_path
        self.check_interval = check_interval
        self.last_mtime = None
        self.last_check_time = 0
        self._on_change_callbacks = []
        
        # Инициализируем начальное значение
        self._update_mtime()
    
    def _update_mtime(self):
        """Обновить известное время модификации файла БД"""
        try:
            if os.path.exists(self.db_path):
                self.last_mtime = os.path.getmtime(self.db_path)
            else:
                self.last_mtime = None
        except Exception:
            self.last_mtime = None
        self.last_check_time = time.time()
    
    def check_for_changes(self, force=False) -> bool:
        """
        Проверить, изменилась ли БД с последней проверки.
        
        Args:
            force: если True — игнорировать check_interval и проверять всегда
        
        Returns:
            True, если изменения обнаружены.
        """
        current_time = time.time()
        
        # Если force=False — проверяем не чаще, чем раз в check_interval секунд
        if not force and (current_time - self.last_check_time < self.check_interval):
            return False
        
        self.last_check_time = current_time
        
        try:
            if not os.path.exists(self.db_path):
                if self.last_mtime is not None:
                    self.last_mtime = None
                    return True
                return False
            
            current_mtime = os.path.getmtime(self.db_path)
            
            if self.last_mtime is None or current_mtime != self.last_mtime:
                self.last_mtime = current_mtime
                # Вызываем коллбэки
                for callback in self._on_change_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        print(f"⚠ Ошибка в коллбэке синхронизации: {e}")
                return True
            
            return False
        except Exception:
            return False
    
    def on_change(self, callback):
        """Зарегистрировать коллбэк на изменение БД"""
        self._on_change_callbacks.append(callback)
    
    def force_check(self):
        """Принудительно обновить timestamp (после записи)"""
        self._update_mtime()


# Глобальный монитор синхронизации
_db_sync_monitor = None


def get_db_sync_monitor():
    """Получить глобальный монитор синхронизации"""
    global _db_sync_monitor
    if _db_sync_monitor is None:
        try:
            from client_config import CHECK_INTERVAL
            check_interval = CHECK_INTERVAL
        except ImportError:
            check_interval = 2
        _db_sync_monitor = DBSyncMonitor(DB_PATH, check_interval)
    return _db_sync_monitor


# ============================================================================
# ПУЛ СОЕДИНЕНИЙ
# ============================================================================
class ConnectionPool:
    """Пул соединений с базой данных для многопользовательской работы"""
    def __init__(self, db_path, pool_size=10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = []
        self.lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self.pool.append(conn)
    
    def _create_connection(self):
        """
        Создать соединение с БД с учётом режима работы.
        - Для сетевого режима: journal_mode=DELETE, synchronous=FULL, timeout=120, cache_size=0
        - Для локального режима: journal_mode=WAL, synchronous=NORMAL
        - Повторные попытки при "disk I/O error"
        """
        try:
            from client_config import MODE, BUSY_TIMEOUT
            
            if MODE == 'network':
                timeout = max(BUSY_TIMEOUT, 120)  # Минимум 120 сек для сети
                is_network = True
            else:
                timeout = 30.0
                is_network = False
        except ImportError:
            timeout = 30.0
            is_network = False
        
        # Повторные попытки подключения при "disk I/O error"
        last_error = None
        for attempt in range(5):
            try:
                conn = sqlite3.connect(
                    self.db_path, 
                    timeout=timeout, 
                    check_same_thread=False,
                    isolation_level=None  # Авто-коммит для стабильности
                )
                
                if is_network:
                    # Для сетевого режима — СТАБИЛЬНАЯ конфигурация
                    conn.execute('PRAGMA journal_mode=DELETE')
                    conn.execute(f'PRAGMA busy_timeout={int(timeout * 1000)}')
                    conn.execute('PRAGMA cache_size=0')            # Отключение кэша
                    conn.execute('PRAGMA synchronous=FULL')        # Максимальная надёжность
                    conn.execute('PRAGMA temp_store=MEMORY')
                    conn.execute('PRAGMA foreign_keys=ON')
                    conn.execute('PRAGMA locking_mode=NORMAL')
                    conn.execute('PRAGMA cache_spill=OFF')
                else:
                    # Для локального режима — быстрая конфигурация с WAL
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute(f'PRAGMA busy_timeout={int(timeout * 1000)}')
                    conn.execute('PRAGMA cache_size=10000')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    conn.execute('PRAGMA temp_store=MEMORY')
                    conn.execute('PRAGMA foreign_keys=ON')
                
                return conn
                
            except sqlite3.OperationalError as e:
                last_error = e
                error_msg = str(e).lower()
                if 'disk i/o' in error_msg or 'locked' in error_msg or 'unable to open' in error_msg:
                    print(f"  ⚠ Попытка {attempt + 1}/5: {e}, ждём...")
                    time.sleep(2)
                else:
                    raise
            except sqlite3.DatabaseError as e:
                last_error = e
                error_msg = str(e).lower()
                if 'disk i/o' in error_msg:
                    print(f"  ⚠ Попытка {attempt + 1}/5: {e}, ждём...")
                    time.sleep(2)
                else:
                    raise
        
        raise sqlite3.OperationalError(
            f"Не удалось подключиться к БД после 5 попыток: {last_error}"
        )
    
    def get_connection(self):
        with self.lock:
            if self.pool:
                return self.pool.pop()
            else:
                return self._create_connection()
    
    def return_connection(self, conn):
        with self.lock:
            if len(self.pool) < self.pool_size:
                self.pool.append(conn)
            else:
                try:
                    conn.close()
                except:
                    pass
    
    def close_all(self):
        """Закрыть все соединения в пуле"""
        with self.lock:
            for conn in self.pool:
                try:
                    conn.close()
                except Exception:
                    pass
            self.pool.clear()


_connection_pool = None
_pool_lock = threading.Lock()


def get_pool():
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = ConnectionPool(DB_PATH, pool_size=10)
    return _connection_pool


def get_connection():
    """
    Получить соединение из пула.
    [ИЗМЕНЕНО] В сетевом режиме всегда проверяет изменения БД
    и очищает кэш запросов для синхронизации с другими клиентами.
    """
    try:
        from client_config import MODE
        is_network = (MODE == 'network')
    except ImportError:
        is_network = False
    
    monitor = get_db_sync_monitor()
    
    if is_network:
        # В сетевом режиме проверяем изменения ПРИ КАЖДОМ запросе
        if monitor.check_for_changes(force=True):
            try:
                from database.cache import query_cache
                query_cache.clear()
            except ImportError:
                pass
    else:
        # В локальном режиме — обычная проверка с интервалом
        if monitor.check_for_changes():
            try:
                from database.cache import query_cache
                query_cache.clear()
            except ImportError:
                pass
    
    return get_pool().get_connection()


def return_connection(conn):
    """Вернуть соединение в пул и обновить timestamp"""
    pool = get_pool()
    pool.return_connection(conn)
    
    # После возврата соединения обновляем timestamp
    monitor = get_db_sync_monitor()
    monitor.force_check()


# ============================================================================
# ПРОВЕРКА И АНАЛИЗ БАЗЫ ДАННЫХ
# ============================================================================
def database_exists() -> bool:
    """Проверить, существует ли файл базы данных."""
    return os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0


def validate_database() -> dict:
    """
    Проверить целостность и валидность базы данных.
    [ВАЖНО] Используется только для локального режима.
    Для сетевого режима эта функция не вызывается, т.к.
    PRAGMA integrity_check конфликтует с другими клиентами.
    """
    result = {
        'exists': False,
        'valid': False,
        'integrity': 'unknown',
        'version': None,
        'tables_count': 0,
        'error': None
    }
    
    if not database_exists():
        result['error'] = 'База данных не найдена'
        return result
    
    result['exists'] = True
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()
        result['integrity'] = integrity_result[0] if integrity_result else 'unknown'
        
        if result['integrity'] != 'ok':
            result['error'] = f'Нарушена целостность БД: {result["integrity"]}'
            conn.close()
            return result
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        result['tables_count'] = cursor.fetchone()[0]
        
        try:
            cursor.execute("SELECT value FROM app_settings WHERE key='db_version'")
            row = cursor.fetchone()
            result['version'] = row[0] if row else '0.0.0'
        except sqlite3.OperationalError:
            result['version'] = '0.0.0'
        
        result['valid'] = True
        conn.close()
    except sqlite3.DatabaseError as e:
        result['error'] = f'Ошибка базы данных: {e}'
    except Exception as e:
        result['error'] = f'Неизвестная ошибка: {e}'
    
    return result


def backup_database(backup_dir: str = None) -> str:
    """Создать резервную копию базы данных."""
    if not database_exists():
        return None
    
    try:
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'euroblock_backup_{timestamp}.db')
        
        shutil.copy2(DB_PATH, backup_file)
        return backup_file
    except Exception as e:
        print(f"✗ Ошибка создания резервной копии: {e}")
        return None


def compare_version(v1: str, v2: str) -> int:
    """Сравнить две версии в формате 'x.y.z'."""
    def parse_version(v):
        try:
            parts = v.split('.')
            return tuple(int(p) for p in parts)
        except:
            return (0, 0, 0)
    
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    
    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


# ============================================================================
# БЕЗОПАСНЫЙ ВЫВОД ОШИБОК
# ============================================================================
def _show_error_and_exit(title, message):
    """
    Показать ошибку пользователю и завершить программу.
    Работает как в консольном, так и в GUI режиме.
    Не использует input() — безопасно для EXE.
    """
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        temp_root = tk.Tk()
        temp_root.withdraw()
        temp_root.attributes('-topmost', True)
        
        messagebox.showerror(title, message)
        
        temp_root.destroy()
    except Exception:
        print(f"\n{'=' * 70}")
        print(f"ОШИБКА: {title}")
        print(f"{'=' * 70}")
        print(message)
        print(f"{'=' * 70}\n")
    
    sys.exit(1)


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================================================
def init_database():
    """
    Инициализация базы данных с проверкой существования.
    - В сетевом режиме БД НИКОГДА не удаляется
    - В сетевом режиме не делается проверка целостности
    - Добавлена обработка блокировки файла
    - Используется safe_connect() для сетевого режима
    """
    print("=" * 70)
    print("Инициализация базы данных")
    print("=" * 70)
    print(f"Путь к БД: {DB_PATH}")
    print()
    
    # Определяем режим работы
    try:
        from client_config import MODE
        is_network = (MODE == 'network')
    except ImportError:
        is_network = False
    
    # Очистка файлов блокировки (только для локального режима)
    if not is_network:
        print("→ Проверка файлов блокировки...")
        release_db_locks()
        print()
    
    # Проверка доступности БД
    try:
        from client_config import check_db_available
        check_result = check_db_available()
        
        if not check_result['available']:
            print(f"✗ Ошибка: {check_result['error']}")
            print()
            
            if is_network:
                print("РЕЖИМ: Многопользовательский (сетевая БД)")
                print()
                print("Возможные причины:")
                print("  1. Сетевая папка недоступна")
                print("  2. Неверный путь в network_config.ini")
                print("  3. Нет прав доступа к сетевой папке")
                print("  4. Сетевое соединение отсутствует")
                print()
                print("Решение:")
                print("  1. Проверьте путь в network_config.ini")
                print("  2. Убедитесь, что сетевая папка доступна")
                print("  3. Проверьте права доступа (чтение/запись)")
            else:
                print("РЕЖИМ: Локальный")
                print()
                print("Возможные причины:")
                print("  1. Папка программы недоступна")
                print("  2. Нет прав на запись")
            
            print()
            _show_error_and_exit(
                "Ошибка подключения к базе данных",
                check_result['error']
            )
        
        if is_network:
            print(f"✓ Многопользовательский режим: база данных доступна")
            print(f"  - Запись разрешена: {'Да' if check_result['writable'] else 'НЕТ!'}")
            
            if not check_result['writable']:
                print()
                print("✗ ОШИБКА: Нет прав на запись!")
                print("  Обратитесь к администратору сетевого ресурса.")
                print()
                _show_error_and_exit(
                    "Нет прав на запись",
                    "Обратитесь к администратору сетевого ресурса."
                )
            
            if check_result['db_exists']:
                print(f"  - База данных найдена ({check_result.get('db_size', 0) / (1024*1024):.2f} МБ)")
            else:
                print(f"  - База данных будет создана (первый запуск)")
        else:
            print(f"✓ Локальный режим: база данных доступна")
        
        print()
    except ImportError:
        pass
    
    # ========================================================================
    # РАЗНАЯ ЛОГИКА ДЛЯ СЕТЕВОГО И ЛОКАЛЬНОГО РЕЖИМОВ
    # ========================================================================
    
    if is_network:
        # ====================================================================
        # СЕТЕВОЙ РЕЖИМ: НЕ трогаем существующую БД!
        # ====================================================================
        print("→ Сетевой режим: подключаемся к общей базе данных...")
        
        if database_exists():
            # БД существует — просто подключаемся
            print(f"✓ База данных найдена: {DB_PATH}")
            print("→ Подключение к существующей базе данных...")
            
            try:
                conn = safe_connect(DB_PATH, timeout=120, max_retries=10)
                
                # Проверяем, что БД валидна, но БЕЗ integrity_check
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                    cursor.fetchone()
                    print("✓ Структура БД проверена")
                except Exception as e:
                    print(f"⚠ Предупреждение при проверке: {e}")
                
                conn.close()
                print("✓ Подключение успешно установлено")
            except Exception as e:
                print(f"✗ Ошибка подключения: {e}")
                print()
                print("Возможные причины:")
                print("  1. База данных заблокирована другим компьютером")
                print("  2. Сетевое соединение нестабильно")
                print("  3. Недостаточно прав доступа")
                print("  4. Файл повреждён")
                print()
                print("Решение:")
                print("  1. Подождите несколько секунд и попробуйте снова")
                print("  2. Убедитесь, что основной компьютер работает")
                print("  3. Проверьте сетевое соединение")
                print("  4. Если проблема повторяется — перезагрузите компьютеры")
                print()
                _show_error_and_exit(
                    "Ошибка подключения к базе данных",
                    f"Не удалось подключиться к БД:\n{e}\n\n"
                    f"Подождите несколько секунд и попробуйте снова."
                )
            
            # Инициализируем пул соединений
            get_pool()
            
            print()
            print("=" * 70)
            print("✓ Подключено к общей базе данных")
            print("  Работаем с существующими данными.")
            print("=" * 70)
            print()
            return
        else:
            # БД не существует — создаём её (первый запуск в сети)
            print("→ База данных не найдена (первый запуск в сети)")
            print("→ Создаётся новая база данных...")
            print()
            
            try:
                _create_new_database()
            except PermissionError as e:
                print(f"✗ Ошибка создания БД: {e}")
                print()
                print("Возможно, нет прав на запись в сетевую папку.")
                print()
                _show_error_and_exit(
                    "Ошибка создания базы данных",
                    f"Не удалось создать БД:\n{e}\n\n"
                    f"Проверьте права доступа к сетевой папке."
                )
            except sqlite3.OperationalError as e:
                print(f"✗ Ошибка SQLite: {e}")
                _show_error_and_exit(
                    "Ошибка базы данных",
                    f"SQLite ошибка:\n{e}"
                )
            
            print()
            print("=" * 70)
            print("✓ База данных успешно создана в сетевой папке")
            print("=" * 70)
            print()
            return
    
    else:
        # ====================================================================
        # ЛОКАЛЬНЫЙ РЕЖИМ: старая логика с проверкой целостности
        # ====================================================================
        if database_exists():
            print("✓ Файл базы данных найден")
            
            validation = validate_database()
            if validation['valid']:
                print(f"✓ База данных валидна")
                print(f"  - Версия БД: {validation['version']}")
                print(f"  - Таблиц: {validation['tables_count']}")
                print(f"  - Целостность: {validation['integrity']}")
                print()
                
                db_version = validation['version']
                if compare_version(db_version, CURRENT_DB_VERSION) < 0:
                    print(f"→ Версия БД ({db_version}) старше текущей ({CURRENT_DB_VERSION})")
                    print("→ Применяются миграции...")
                    _apply_migrations(db_version)
                else:
                    print(f"✓ Версия БД актуальна")
                
                print()
                print("✓ Используется существующая база данных")
                print("  Все ваши данные сохранены!")
                print("=" * 70)
                print()
                
                get_pool()
                return
            else:
                # БД повреждена — в локальном режиме можно удалить и создать заново
                print(f"✗ База данных повреждена: {validation['error']}")
                print()
                print("→ Создаётся резервная копия повреждённой БД...")
                
                close_pool()
                time.sleep(0.5)
                
                backup_path = backup_database()
                if backup_path:
                    print(f"✓ Резервная копия создана: {backup_path}")
                    print()
                    print("→ Создаётся новая база данных...")
                    
                    try:
                        if os.path.exists(DB_PATH):
                            os.remove(DB_PATH)
                        for ext in ['-wal', '-shm', '-journal']:
                            wal_file = DB_PATH + ext
                            if os.path.exists(wal_file):
                                try:
                                    os.remove(wal_file)
                                except PermissionError:
                                    print(f"  ⚠ Файл {ext} занят")
                    except PermissionError as e:
                        print(f"✗ Не удалось удалить повреждённую БД: {e}")
                        _show_error_and_exit(
                            "Файл базы данных заблокирован",
                            f"Не удалось удалить повреждённую БД:\n{DB_PATH}\n\n"
                            f"Закройте все экземпляры программы и попробуйте снова."
                        )
                    except Exception as e:
                        print(f"✗ Не удалось удалить повреждённую БД: {e}")
                        _show_error_and_exit(
                            "Ошибка удаления БД",
                            f"Не удалось удалить повреждённую БД:\n{e}"
                        )
                else:
                    print("✗ Не удалось создать резервную копию")
                    print("→ Продолжаем с созданием новой БД...")
        else:
            print("→ База данных не найдена (первый запуск)")
            print("→ Создаётся новая база данных...")
            print()
        
        try:
            _create_new_database()
        except PermissionError as e:
            print(f"✗ Ошибка создания БД: {e}")
            _show_error_and_exit(
                "Ошибка создания базы данных",
                f"Не удалось создать БД:\n{e}\n\n"
                f"Закройте все экземпляры программы и попробуйте снова."
            )
        except sqlite3.OperationalError as e:
            print(f"✗ Ошибка SQLite: {e}")
            _show_error_and_exit(
                "Ошибка базы данных",
                f"SQLite ошибка:\n{e}"
            )
        
        print()
        print("=" * 70)
        print("✓ База данных успешно создана и инициализирована")
        print("=" * 70)
        print()


def _create_new_database():
    """Создать новую базу данных со всеми таблицами и индексами"""
    is_pooled = True
    try:
        from client_config import MODE
        if MODE == 'network':
            conn = safe_connect(DB_PATH, timeout=120, max_retries=10)
            is_pooled = False
        else:
            conn = get_connection()
            is_pooled = True
    except ImportError:
        conn = get_connection()
        is_pooled = True
    
    cursor = conn.cursor()
    try:
        # ====================================================================
        # ТАБЛИЦА НАСТРОЕК ПРИЛОЖЕНИЯ
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value)
            VALUES ('db_version', ?)
        ''', (CURRENT_DB_VERSION,))
        
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value)
            VALUES ('created_at', ?)
        ''', (datetime.now().strftime('%d.%m.%Y %H:%M:%S'),))
        
        # ====================================================================
        # СПРАВОЧНИКИ
        # ====================================================================
        dictionaries = [
            'payment_types', 'materials', 'purposes', 'equipment',
            'payers', 'customers', 'suppliers', 'colors'
        ]
        
        for table_name in dictionaries:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # ====================================================================
        # ОСНОВНЫЕ ТАБЛИЦЫ
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                volume_per_pallet REAL,
                production_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cement_silos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                capacity REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cement_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_date TEXT NOT NULL,
                silo_name TEXT NOT NULL,
                quantity_kg REAL NOT NULL,
                supplier_name TEXT,
                is_correction INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS production (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                production_date TEXT NOT NULL,
                equipment_name TEXT,
                silo_name TEXT,
                product_name TEXT,
                color_name TEXT,
                quantity_pallets REAL,
                cement_kg REAL DEFAULT 0,
                enriched_sand_kg REAL DEFAULT 0,
                river_sand_kg REAL DEFAULT 0,
                keramzit_kg REAL DEFAULT 0,
                plasticizer_kg REAL DEFAULT 0,
                water_kg REAL DEFAULT 0,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                color_name TEXT NOT NULL,
                stock_qty REAL DEFAULT 0,
                reserved_qty REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_name, color_name)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reserved_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                product_name TEXT NOT NULL,
                color_name TEXT,
                quantity REAL NOT NULL,
                customer_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sold_from_reserve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                sale_date TEXT NOT NULL,
                product_name TEXT NOT NULL,
                color_name TEXT,
                quantity REAL NOT NULL,
                customer_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для истории реализаций из резерва
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reserve_sales_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reserve_id INTEGER NOT NULL,
                sale_date TEXT NOT NULL,
                quantity REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reserve_id) REFERENCES reserved_products(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adjustment_date TEXT NOT NULL,
                product_name TEXT NOT NULL,
                color_name TEXT,
                qty_before REAL NOT NULL,
                qty_after REAL NOT NULL,
                difference REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                product_name TEXT NOT NULL,
                color_name TEXT,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                equipment_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_date TEXT NOT NULL,
                income REAL DEFAULT 0,
                expense REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS general_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                supplier_name TEXT,
                material_name TEXT,
                quantity REAL DEFAULT 0,
                price REAL DEFAULT 0,
                payer_name TEXT,
                payment_type_name TEXT,
                purpose_name TEXT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ====================================================================
        # ИНДЕКСЫ
        # ====================================================================
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_production_date ON production(production_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_operations_date ON cash_operations(operation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_general_expenses_date ON general_expenses(expense_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cement_receipts_date ON cement_receipts(receipt_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reserved_products_dates ON reserved_products(start_date, end_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_adjustments_date ON adjustments(adjustment_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_production_product ON production(product_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_production_equipment ON production(equipment_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_production_date_product ON production(production_date, product_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_date_product ON sales(sale_date, product_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cement_receipts_silo_date ON cement_receipts(silo_name, receipt_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reserve_sales_history_reserve ON reserve_sales_history(reserve_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reserve_sales_history_date ON reserve_sales_history(sale_date)')
        
        conn.commit()
        cursor.execute('ANALYZE')
    except Exception as e:
        conn.rollback()
        print(f"✗ Ошибка создания БД: {e}")
        raise
    finally:
        if is_pooled:
            return_connection(conn)
        else:
            try:
                conn.close()
            except:
                pass


def _apply_migrations(from_version: str):
    """Применить миграции от указанной версии до текущей."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # ====================================================================
        # МИГРАЦИЯ 1: Добавление таблицы app_settings
        # ====================================================================
        if compare_version(from_version, '0.0.0') == 0:
            print("  → Миграция 1: Создание таблицы app_settings...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT OR REPLACE INTO app_settings (key, value)
                VALUES ('db_version', '1.0.0')
            ''')
            cursor.execute('''
                INSERT OR REPLACE INTO app_settings (key, value)
                VALUES ('created_at', ?)
            ''', (datetime.now().strftime('%d.%m.%Y %H:%M:%S'),))
            from_version = '1.0.0'
        
        # ====================================================================
        # МИГРАЦИЯ 2: Добавление поля equipment_name в sales
        # ====================================================================
        if compare_version(from_version, '1.0.0') < 0:
            try:
                cursor.execute('ALTER TABLE sales ADD COLUMN equipment_name TEXT')
                print("  → Миграция 2: Добавлено поле equipment_name в sales")
            except sqlite3.OperationalError:
                pass
        
        # ====================================================================
        # МИГРАЦИЯ 3: Создание таблицы reserve_sales_history
        # ====================================================================
        if compare_version(from_version, '1.0.0') >= 0 and compare_version(from_version, '1.0.1') < 0:
            print("  → Миграция 3: Создание таблицы reserve_sales_history...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reserve_sales_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reserve_id INTEGER NOT NULL,
                    sale_date TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reserve_id) REFERENCES reserved_products(id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reserve_sales_history_reserve 
                ON reserve_sales_history(reserve_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reserve_sales_history_date 
                ON reserve_sales_history(sale_date)
            ''')
            from_version = '1.0.1'
        
        # ====================================================================
        # Обновляем версию БД
        # ====================================================================
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value)
            VALUES ('db_version', ?)
        ''', (CURRENT_DB_VERSION,))
        
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value)
            VALUES ('last_migration_at', ?)
        ''', (datetime.now().strftime('%d.%m.%Y %H:%M:%S'),))
        
        conn.commit()
        print(f"  ✓ Миграции завершены. Текущая версия: {CURRENT_DB_VERSION}")
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Ошибка миграции: {e}")
        raise
    finally:
        return_connection(conn)


# ============================================================================
# СЕРВИСНЫЕ ФУНКЦИИ
# ============================================================================
def optimize_database():
    """Оптимизировать базу данных"""
    conn = get_connection()
    try:
        print("Оптимизация базы данных...")
        conn.execute('VACUUM')
        conn.execute('ANALYZE')
        print("✓ База данных оптимизирована")
    except Exception as e:
        print(f"✗ Ошибка оптимизации: {e}")
    finally:
        return_connection(conn)


def get_database_info():
    """Получить информацию о базе данных"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_stats = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            table_stats[table] = count
        
        version = 'unknown'
        try:
            cursor.execute("SELECT value FROM app_settings WHERE key='db_version'")
            row = cursor.fetchone()
            if row:
                version = row[0]
        except:
            pass
        
        return {
            'path': DB_PATH,
            'size_bytes': db_size,
            'size_mb': round(db_size / (1024 * 1024), 2),
            'tables_count': len(tables),
            'table_stats': table_stats,
            'version': version
        }
    finally:
        return_connection(conn)


def get_setting(key: str, default=None):
    """Получить настройку из БД"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key=?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default
    except:
        return default
    finally:
        return_connection(conn)


def set_setting(key: str, value):
    """Сохранить настройку в БД"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, str(value)))
        conn.commit()
    finally:
        return_connection(conn)


def close_pool():
    """Закрыть пул соединений"""
    global _connection_pool
    if _connection_pool is not None:
        try:
            _connection_pool.close_all()
        except Exception:
            pass
        _connection_pool = None