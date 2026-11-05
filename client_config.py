"""
Конфигурация клиента для многопользовательской работы.
Поддерживает три режима:
  - 'local': локальная база данных (основной компьютер)
  - 'network': база данных в сетевой папке (клиентский компьютер)
  - 'server': через HTTP-сервер (устаревший режим)

Настройка через:
  1. Файл network_config.ini рядом с программой (ПРИОРИТЕТ)
  2. Переменные окружения
  3. Аргументы командной строки
"""
import os
import sys
import json
import configparser
import urllib.request
import urllib.error


# ============================================================================
# ОПРЕДЕЛЕНИЕ ПУТИ К КОНФИГУРАЦИИ
# ============================================================================
def _get_config_dir():
    """Получить папку с конфигурацией"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_config_file() -> dict:
    """Загрузить конфигурацию из network_config.ini"""
    config = {
        'mode': 'local',
        'db_path': None,
        'busy_timeout': 30,
        'check_interval': 2,
        'server_url': None,
        'server_timeout': 30,
        'is_main': False
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
            if mode in ('local', 'network', 'server'):
                config['mode'] = mode
        
        # Настройки локального режима
        if parser.has_section('local'):
            config['db_path'] = parser.get('local', 'db_path', fallback=None)
            config['is_main'] = parser.getboolean('local', 'is_main', fallback=False)
        
        # Настройки сетевого режима
        if parser.has_section('network'):
            config['db_path'] = parser.get('network', 'db_path', fallback=config['db_path'])
            config['busy_timeout'] = parser.getint('network', 'busy_timeout', fallback=30)
            config['check_interval'] = parser.getint('network', 'check_interval', fallback=2)
            config['is_main'] = parser.getboolean('network', 'is_main', fallback=False)
        
        # Настройки серверного режима
        if parser.has_section('server'):
            config['server_url'] = parser.get('server', 'url', fallback=None)
            config['server_timeout'] = parser.getint('server', 'timeout', fallback=30)
    except Exception as e:
        print(f"⚠ Ошибка чтения конфигурации: {e}")
    
    return config


# ============================================================================
# ОПРЕДЕЛЕНИЕ РЕЖИМА РАБОТЫ
# ============================================================================
_FILE_CONFIG = _load_config_file()


def get_mode() -> str:
    """Получить режим работы"""
    # 1. Аргументы командной строки
    for arg in sys.argv:
        if arg.startswith('--mode='):
            return arg.split('=', 1)[1].lower()
    
    # 2. Переменные окружения
    env_mode = os.environ.get('EUROBLOCK_MODE', '').lower()
    if env_mode in ('local', 'network', 'server'):
        return env_mode
    
    # 3. Файл конфигурации
    return _FILE_CONFIG['mode']


def get_db_path() -> str:
    """Получить путь к БД"""
    # 1. Аргументы командной строки
    for arg in sys.argv:
        if arg.startswith('--db-path='):
            return arg.split('=', 1)[1]
    
    # 2. Переменные окружения
    env_path = os.environ.get('EUROBLOCK_DB_PATH')
    if env_path:
        return env_path
    
    # 3. Файл конфигурации
    if _FILE_CONFIG['db_path']:
        return _FILE_CONFIG['db_path']
    
    # 4. Локальный путь по умолчанию
    config_dir = _get_config_dir()
    return os.path.join(config_dir, 'euroblock.db')


def is_main_computer() -> bool:
    """Проверить, является ли этот компьютер основным"""
    return _FILE_CONFIG.get('is_main', False)


def get_server_url() -> str:
    """Получить URL сервера"""
    for arg in sys.argv:
        if arg.startswith('--server='):
            return arg.split('=', 1)[1]
    return os.environ.get('EUROBLOCK_SERVER', 
                         _FILE_CONFIG['server_url'] or 'http://localhost:5000')


# Глобальные переменные
MODE = get_mode()
DB_PATH = get_db_path()
IS_MAIN = is_main_computer()
SERVER_URL = get_server_url() if MODE == 'server' else None
BUSY_TIMEOUT = _FILE_CONFIG['busy_timeout']
CHECK_INTERVAL = _FILE_CONFIG['check_interval']


# ============================================================================
# КЛИЕНТ ДЛЯ РАБОТЫ С СЕРВЕРОМ (устаревший)
# ============================================================================
class ServerClient:
    """Клиент для работы с сервером в многопользовательском режиме"""
    def __init__(self, server_url: str, timeout: int = 30):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
    
    def _make_request(self, endpoint: str, data: dict = None, method: str = 'POST') -> dict:
        url = f"{self.server_url}{endpoint}"
        if data is not None:
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(
                url, data=json_data, method=method,
                headers={'Content-Type': 'application/json; charset=utf-8'}
            )
        else:
            req = urllib.request.Request(url, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
                raise Exception(f"Ошибка сервера: {error_data.get('error', error_body)}")
            except json.JSONDecodeError:
                raise Exception(f"Ошибка сервера ({e.code}): {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Не удалось подключиться к серверу: {e.reason}")
        except Exception as e:
            raise Exception(f"Ошибка запроса: {e}")
    
    def query(self, sql: str, params: list = None) -> list:
        result = self._make_request('/api/query', {'query': sql, 'params': params or []})
        if not result.get('success'):
            raise Exception(f"Ошибка запроса: {result.get('error')}")
        return result.get('data', [])
    
    def execute(self, sql: str, params: list = None) -> int:
        result = self._make_request('/api/execute', {'query': sql, 'params': params or []})
        if not result.get('success'):
            raise Exception(f"Ошибка выполнения: {result.get('error')}")
        return result.get('last_id')
    
    def health_check(self) -> bool:
        try:
            result = self._make_request('/api/health', method='GET')
            return result.get('status') == 'ok'
        except:
            return False


# ============================================================================
# ПРОВЕРКА ДОСТУПНОСТИ ОСНОВНОГО КОМПЬЮТЕРА
# ============================================================================
def check_main_computer_available() -> dict:
    """
    Проверить доступность основного компьютера.
    
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
    
    # Если это основной компьютер — всегда доступен
    if IS_MAIN or MODE == 'local':
        result['available'] = True
        result['db_exists'] = os.path.exists(DB_PATH)
        result['writable'] = True
        return result
    
    # Для сетевого режима — проверяем путь
    if MODE == 'network':
        try:
            db_dir = os.path.dirname(DB_PATH)
            
            # Проверяем доступность папки
            if not os.path.exists(db_dir):
                result['error'] = f"Сетевая папка недоступна:\n{db_dir}\n\n" \
                                  f"Основной компьютер выключен или папка недоступна."
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
# ГЛОБАЛЬНЫЙ КЛИЕНТ
# ============================================================================
_server_client = None


def get_server_client() -> ServerClient:
    """Получить глобальный клиент для работы с сервером"""
    global _server_client
    if MODE != 'server':
        raise Exception("Клиент доступен только в режиме 'server'")
    if _server_client is None:
        _server_client = ServerClient(SERVER_URL)
    return _server_client


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
        print(f"Роль: {'Основной компьютер' if IS_MAIN else 'Клиентский компьютер'}")
        print(f"Таймаут ожидания: {BUSY_TIMEOUT} сек")
        print(f"Интервал проверки: {CHECK_INTERVAL} сек")
        
        # Проверяем доступность
        check = check_main_computer_available()
        if check['available']:
            print("Статус: ✓ Основной компьютер доступен")
            if check['db_exists']:
                print(f"  - База данных найдена")
            else:
                print(f"  - База данных будет создана (первый запуск)")
        else:
            print(f"Статус: ✗ {check['error']}")
    
    elif MODE == 'server':
        print(f"Сервер: {SERVER_URL}")
        try:
            client = get_server_client()
            if client.health_check():
                print("Статус: ✓ Сервер доступен")
            else:
                print("Статус: ✗ Сервер недоступен")
        except Exception as e:
            print(f"Статус: ✗ Ошибка подключения: {e}")
    
    else:  # local
        print("Роль: Локальный компьютер")
    
    print("=" * 70)


if __name__ == "__main__":
    print_mode_info()