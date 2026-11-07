"""
Конфигурация клиента для многопользовательской работы.
Все компьютеры равноправны — любой подключается к общей БД на сетевом диске.

Режимы работы:
  - 'local': локальная база данных (один пользователь)
  - 'network': база данных в сетевой папке (многопользовательский режим)

Настройка через:
  1. Файл network_config.ini рядом с программой (ПРИОРИТЕТ)
  2. Переменные окружения:
       set EUROBLOCK_MODE=network
       set EUROBLOCK_DB_PATH=\\SERVER\Share\euroblock.db
  3. Аргументы командной строки:
       python main.py --mode=network --db-path=\\SERVER\Share\euroblock.db
"""
import os
import sys
import configparser


# ============================================================================
# ОПРЕДЕЛЕНИЕ ПУТИ К КОНФИГУРАЦИИ
# ============================================================================
def _get_config_dir():
    """Получить папку с конфигурацией"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def _load_config_file() -> dict:
    """Загрузить конфигурацию из network_config.ini"""
    config = {
        'mode': 'local',
        'db_path': None,
        'busy_timeout': 30,
        'check_interval': 2
    }
    
    config_dir = _get_config_dir()
    config_file = os.path.join(config_dir, 'network_config.ini')
    
    if not os.path.exists(config_file):
        return config
    
    try:
        parser = configparser.ConfigParser()
        parser.read(config_file, encoding='utf-8')
        
        # Режим работы
        if parser.has_section('mode'):
            mode = parser.get('mode', 'mode', fallback='local').lower()
            if mode in ('local', 'network'):
                config['mode'] = mode
        
        # Настройки сетевого режима
        if parser.has_section('network'):
            config['db_path'] = parser.get('network', 'db_path', fallback=None)
            config['busy_timeout'] = parser.getint('network', 'busy_timeout', fallback=30)
            config['check_interval'] = parser.getint('network', 'check_interval', fallback=2)
        
        # Для обратной совместимости — проверяем раздел [local]
        if parser.has_section('local') and config['db_path'] is None:
            config['db_path'] = parser.get('local', 'db_path', fallback=None)
    except Exception as e:
        print(f"⚠ Ошибка чтения конфигурации: {e}")
    
    return config


# ============================================================================
# ОПРЕДЕЛЕНИЕ РЕЖИМА РАБОТЫ
# ============================================================================
_FILE_CONFIG = _load_config_file()


def get_mode() -> str:
    """Получить режим работы"""
    for arg in sys.argv:
        if arg.startswith('--mode='):
            return arg.split('=', 1)[1].lower()
    
    env_mode = os.environ.get('EUROBLOCK_MODE', '').lower()
    if env_mode in ('local', 'network'):
        return env_mode
    
    return _FILE_CONFIG['mode']


def get_db_path() -> str:
    """Получить путь к БД"""
    for arg in sys.argv:
        if arg.startswith('--db-path='):
            return arg.split('=', 1)[1]
    
    env_path = os.environ.get('EUROBLOCK_DB_PATH')
    if env_path:
        return env_path
    
    if _FILE_CONFIG['db_path']:
        return _FILE_CONFIG['db_path']
    
    config_dir = _get_config_dir()
    return os.path.join(config_dir, 'euroblock.db')


# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================
MODE = get_mode()
DB_PATH = get_db_path()
BUSY_TIMEOUT = _FILE_CONFIG['busy_timeout']
CHECK_INTERVAL = _FILE_CONFIG['check_interval']

# NETWORK_DB_PATH — для совместимости с другими модулями
NETWORK_DB_PATH = DB_PATH if MODE == 'network' else None


# ============================================================================
# ПРОВЕРКА ДОСТУПНОСТИ СЕТЕВОГО ПУТИ
# ============================================================================
def check_db_available() -> dict:
    """
    Проверить доступность базы данных.
    Работает для любого режима (локальный или сетевой).
    
    Returns:
        {
            'available': bool,
            'path': str,
            'db_exists': bool,
            'writable': bool,
            'error': str or None
        }
    """
    result = {
        'available': False,
        'path': DB_PATH,
        'db_exists': False,
        'writable': False,
        'error': None
    }
    
    try:
        db_dir = os.path.dirname(DB_PATH)
        
        # Проверяем доступность папки
        if not os.path.exists(db_dir):
            result['error'] = (
                f"Папка недоступна:\n{db_dir}\n\n"
                f"Возможные причины:\n"
                f"  - Сетевой компьютер выключен\n"
                f"  - Общий доступ не настроен\n"
                f"  - Нет сетевого соединения\n"
                f"  - Неверный путь в network_config.ini"
            )
            return result
        
        result['available'] = True
        
        # Проверяем существование БД
        if os.path.exists(DB_PATH):
            result['db_exists'] = True
        
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
# ИНФОРМАЦИЯ О РЕЖИМЕ
# ============================================================================
def print_mode_info():
    """Вывести информацию о текущем режиме работы"""
    print("=" * 70)
    print("РЕЖИМ РАБОТЫ ПРОГРАММЫ")
    print("=" * 70)
    print(f"Режим: {MODE}")
    print(f"Путь к БД: {DB_PATH}")
    
    if MODE == 'network':
        print("Тип: Многопользовательский режим (сетевая БД)")
        print(f"Таймаут ожидания: {BUSY_TIMEOUT} сек")
        print(f"Интервал проверки: {CHECK_INTERVAL} сек")
        
        check = check_db_available()
        if check['available']:
            print("Статус: ✓ База данных доступна")
            if check['db_exists']:
                print(f"  - База данных найдена")
            else:
                print(f"  - База данных будет создана (первый запуск)")
        else:
            print(f"Статус: ✗ {check['error']}")
    
    else:  # local
        print("Тип: Локальный режим (один пользователь)")
    
    print("=" * 70)


if __name__ == "__main__":
    print_mode_info()