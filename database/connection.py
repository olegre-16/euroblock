"""
Модуль подключения и инициализации базы данных.
Поддержка многопользовательского режима (локальный/сетевой/серверный).
При запуске проверяет наличие существующей БД и использует её,
либо создаёт новую при первом запуске.
[ИЗМЕНЕНО] 
- Добавлена поддержка сетевого режима через file path
- Добавлена проверка доступности сетевого пути
- Увеличены таймауты для сетевого режима
- Добавлена миграция 3: таблица reserve_sales_history
- Версия БД обновлена до 1.0.1
"""
import sqlite3
import os
import sys
import threading
import shutil
from datetime import datetime


# ============================================================================
# ОПРЕДЕЛЕНИЕ ПУТИ К БД
# ============================================================================
def get_db_path():
    """
    Получить путь к базе данных.
    Приоритет:
    1. Режим 'network' → путь из network_config.ini или переменных окружения
    2. Режим 'server' → не используется (работа через HTTP)
    3. Запуск из EXE → папка с EXE-файлом
    4. Запуск из скрипта → корень проекта
    """
    # Импортируем здесь, чтобы избежать циклического импорта
    try:
        from client_config import MODE, NETWORK_DB_PATH
        
        # Режим "network" — путь к БД в сетевой папке
        if MODE == 'network' and NETWORK_DB_PATH:
            return NETWORK_DB_PATH
        
        # Режим "server" — путь не нужен (работа через HTTP)
        if MODE == 'server':
            pass  # fallback на локальный путь
    except ImportError:
        pass
    
    # Локальный режим — стандартный путь
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
        
        # Проверяем доступность папки
        if not os.path.exists(db_dir):
            result['error'] = f"Сетевая папка недоступна: {db_dir}"
            return result
        
        result['accessible'] = True
        
        # Проверяем существование БД
        if os.path.exists(db_path):
            result['db_exists'] = True
            result['db_size'] = os.path.getsize(db_path)
        
        # Проверяем возможность записи
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
        """Создать соединение с БД с учётом режима работы"""
        try:
            from client_config import MODE, BUSY_TIMEOUT
            
            # Для сетевого режима увеличиваем таймауты
            if MODE == 'network':
                timeout = max(BUSY_TIMEOUT, 60)  # Минимум 60 сек для сети
            else:
                timeout = 30.0
        except ImportError:
            timeout = 30.0
        
        conn = sqlite3.connect(self.db_path, timeout=timeout, check_same_thread=False)
        
        # Оптимизации для многопользовательской работы
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(f'PRAGMA busy_timeout={int(timeout * 1000)}')
        conn.execute('PRAGMA cache_size=10000')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA temp_store=MEMORY')
        conn.execute('PRAGMA foreign_keys=ON')
        
        # Дополнительные настройки для сетевого режима
        try:
            from client_config import MODE
            if MODE == 'network':
                conn.execute('PRAGMA wal_autocheckpoint=100')
                conn.execute('PRAGMA locking_mode=NORMAL')
        except ImportError:
            pass
        
        return conn
    
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
        with self.lock:
            for conn in self.pool:
                try:
                    conn.close()
                except:
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
    return get_pool().get_connection()


def return_connection(conn):
    get_pool().return_connection(conn)


# ============================================================================
# ПРОВЕРКА И АНАЛИЗ БАЗЫ ДАННЫХ
# ============================================================================
def database_exists() -> bool:
    """
    Проверить, существует ли файл базы данных.
    Returns:
        True, если файл euroblock.db существует в папке программы
    """
    return os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0


def validate_database() -> dict:
    """
    Проверить целостность и валидность базы данных.
    Returns:
         Словарь с результатами проверки:
         {
             'exists': bool,           - существует ли файл
             'valid': bool,            - валидна ли БД
             'integrity': str,         - результат проверки целостности
             'version': str,           - версия БД
             'tables_count': int,      - количество таблиц
             'error': str or None      - сообщение об ошибке
         }
    """
    result = {
        'exists': False,
        'valid': False,
        'integrity': 'unknown',
        'version': None,
        'tables_count': 0,
        'error': None
    }
    
    # Проверяем существование файла
    if not database_exists():
        result['error'] = 'База данных не найдена'
        return result
    
    result['exists'] = True
    
    # Пытаемся подключиться и проверить целостность
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        # Проверка целостности
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()
        result['integrity'] = integrity_result[0] if integrity_result else 'unknown'
        
        if result['integrity'] != 'ok':
            result['error'] = f'Нарушена целостность БД: {result["integrity"]}'
            conn.close()
            return result
        
        # Подсчёт таблиц
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        result['tables_count'] = cursor.fetchone()[0]
        
        # Получение версии БД
        try:
            cursor.execute("SELECT value FROM app_settings WHERE key='db_version'")
            row = cursor.fetchone()
            result['version'] = row[0] if row else '0.0.0'
        except sqlite3.OperationalError:
            # Таблица app_settings ещё не создана
            result['version'] = '0.0.0'
        
        result['valid'] = True
        conn.close()
    except sqlite3.DatabaseError as e:
        result['error'] = f'Ошибка базы данных: {e}'
    except Exception as e:
        result['error'] = f'Неизвестная ошибка: {e}'
    
    return result


def backup_database(backup_dir: str = None) -> str:
    """
    Создать резервную копию базы данных.
    Args:
         backup_dir: папка для бэкапа (по умолчанию — папка 'backups' рядом с БД)
    Returns:
         Путь к созданному файлу бэкапа или None при ошибке
    """
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
    """
    Сравнить две версии в формате "x.y.z".
    Returns:
         -1 если v1 < v2
          0 если v1 == v2
          1 если v1 > v2
    """
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
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ============================================================================
def init_database():
    """
    Инициализация базы данных с проверкой существования.
    Логика работы:
     1. Если БД существует и валидна — используется существующая
     2. Если БД не существует — создаётся новая
     3. Если БД повреждена — создаётся бэкап и новая БД
     4. Если версия БД старая — применяются миграции
    [ИЗМЕНЕНО] Добавлена поддержка сетевого режима.
    """
    print("=" * 70)
    print("Инициализация базы данных")
    print("=" * 70)
    print(f"Путь к БД: {DB_PATH}")
    print()
    
    # Проверка сетевого пути
    try:
        from client_config import MODE
        if MODE == 'network':
            print("→ Режим: Сетевая база данных")
            check_result = check_network_path(DB_PATH)
            
            if not check_result['accessible']:
                print(f"✗ Ошибка: {check_result['error']}")
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
                print("  4. Попробуйте открыть папку через Проводник")
                print()
                input("Нажмите Enter для выхода...")
                sys.exit(1)
            
            print(f"✓ Сетевая папка доступна")
            print(f"  - Запись разрешена: {'Да' if check_result['writable'] else 'НЕТ!'}")
            
            if not check_result['writable']:
                print()
                print("✗ ОШИБКА: Нет прав на запись в сетевую папку!")
                print("  Обратитесь к администратору для предоставления прав.")
                print()
                input("Нажмите Enter для выхода...")
                sys.exit(1)
            
            if check_result['db_exists']:
                print(f"  - База данных найдена ({check_result['db_size'] / (1024*1024):.2f} МБ)")
            else:
                print(f"  - База данных будет создана (первый запуск)")
            print()
    except ImportError:
        pass
    
    # ========================================================================
    # ШАГ 1: Проверяем существование БД
    # ========================================================================
    if database_exists():
        print("✓ Файл базы данных найден")
        
        # ====================================================================
        # ШАГ 2: Проверяем целостность
        # ====================================================================
        validation = validate_database()
        if validation['valid']:
            print(f"✓ База данных валидна")
            print(f"  - Версия БД: {validation['version']}")
            print(f"  - Таблиц: {validation['tables_count']}")
            print(f"  - Целостность: {validation['integrity']}")
            print()
            
            # ==================================================================
            # ШАГ 3: Проверяем версию и применяем миграции
            # ==================================================================
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
            
            # Инициализируем пул соединений
            get_pool()
            return
        else:
            # ==================================================================
            # ШАГ 2.1: БД повреждена
            # ==================================================================
            print(f"✗ База данных повреждена: {validation['error']}")
            print()
            print("→ Создаётся резервная копия повреждённой БД...")
            backup_path = backup_database()
            if backup_path:
                print(f"✓ Резервная копия создана: {backup_path}")
                print()
                print("→ Создаётся новая база данных...")
                # Удаляем повреждённую БД
                try:
                    os.remove(DB_PATH)
                    # Удаляем также файлы WAL и SHM
                    for ext in ['-wal', '-shm', '-journal']:
                        wal_file = DB_PATH + ext
                        if os.path.exists(wal_file):
                            os.remove(wal_file)
                except Exception as e:
                    print(f"✗ Не удалось удалить повреждённую БД: {e}")
                    print("  Попробуйте закрыть все экземпляры программы и повторить")
                    raise
            else:
                print("✗ Не удалось создать резервную копию")
                print("→ Продолжаем с созданием новой БД...")
    else:
        # ======================================================================
        # ШАГ 1.1: БД не существует — первый запуск
        # ======================================================================
        print("→ База данных не найдена (первый запуск)")
        print("→ Создаётся новая база данных...")
        print()
    
    # =========================================================================
    # ШАГ 4: Создание новой БД
    # =========================================================================
    _create_new_database()
    
    print()
    print("=" * 70)
    print("✓ База данных успешно создана и инициализирована")
    print("=" * 70)
    print()


def _create_new_database():
    """Создать новую базу данных со всеми таблицами и индексами"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # ====================================================================
        # ТАБЛИЦА НАСТРОЕК ПРИЛОЖЕНИЯ (должна быть первой)
        # ====================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Сохраняем версию БД
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, value)
            VALUES ('db_version', ?)
        ''', (CURRENT_DB_VERSION,))
        
        # Сохраняем дату создания
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
        
        # [НОВОЕ] Таблица для истории реализаций из резерва
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
        
        # [НОВОЕ] Индексы для таблицы истории реализаций из резерва
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reserve_sales_history_reserve ON reserve_sales_history(reserve_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reserve_sales_history_date ON reserve_sales_history(sale_date)')
        
        conn.commit()
        cursor.execute('ANALYZE')
    except Exception as e:
        conn.rollback()
        print(f"✗ Ошибка создания БД: {e}")
        raise
    finally:
        return_connection(conn)


def _apply_migrations(from_version: str):
    """
    Применить миграции от указанной версии до текущей.
    Args:
         from_version: версия БД, от которой нужно мигрировать
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # ====================================================================
        # МИГРАЦИЯ 1: Добавление таблицы app_settings (если её нет)
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
        # МИГРАЦИЯ 2: Добавление поля equipment_name в sales (если нужно)
        # ====================================================================
        if compare_version(from_version, '1.0.0') < 0:
            try:
                cursor.execute('ALTER TABLE sales ADD COLUMN equipment_name TEXT')
                print("  → Миграция 2: Добавлено поле equipment_name в sales")
            except sqlite3.OperationalError:
                pass  # Поле уже есть
        
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
        # БУДУЩИЕ МИГРАЦИИ добавляются здесь
        # ====================================================================
        
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
        
        # Получаем версию БД
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
        _connection_pool.close_all()
        _connection_pool = None