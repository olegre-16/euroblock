"""
Конфигурация клиента для подключения к серверу.
Использует ТОЛЬКО стандартные библиотеки Python (urllib).

Режимы работы:
- 'local': работа с локальной базой данных (по умолчанию)
- 'server': работа через сервер (многопользовательский режим)

Настройка через переменные окружения:
    set EUROBLOCK_MODE=server
    set EUROBLOCK_SERVER=http://192.168.1.100:5000

Или через аргументы командной строки:
    python main.py --mode=server --server=http://192.168.1.100:5000
"""
import os
import sys
import json
import urllib.request
import urllib.error


# ============================================================================
# ОПРЕДЕЛЕНИЕ РЕЖИМА РАБОТЫ
# ============================================================================

def get_mode() -> str:
    """Получить режим работы из переменных окружения или аргументов"""
    if '--mode=server' in sys.argv:
        return 'server'
    if '--mode=local' in sys.argv:
        return 'local'
    mode = os.environ.get('EUROBLOCK_MODE', 'local')
    return mode.lower()


def get_server_url() -> str:
    """Получить URL сервера"""
    for arg in sys.argv:
        if arg.startswith('--server='):
            return arg.split('=', 1)[1]
    return os.environ.get('EUROBLOCK_SERVER', 'http://localhost:5000')


MODE = get_mode()
SERVER_URL = get_server_url() if MODE == 'server' else None


# ============================================================================
# КЛИЕНТ ДЛЯ РАБОТЫ С СЕРВЕРОМ (на urllib)
# ============================================================================

class ServerClient:
    """Клиент для работы с сервером в многопользовательском режиме"""
    
    def __init__(self, server_url: str, timeout: int = 30):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
    
    def _make_request(self, endpoint: str, data: dict = None, method: str = 'POST') -> dict:
        """Выполнить HTTP запрос к серверу"""
        url = f"{self.server_url}{endpoint}"
        
        if data is not None:
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=json_data,
                method=method,
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
        """Выполнить SELECT-запрос"""
        result = self._make_request('/api/query', {'query': sql, 'params': params or []})
        if not result.get('success'):
            raise Exception(f"Ошибка запроса: {result.get('error')}")
        return result.get('data', [])
    
    def execute(self, sql: str, params: list = None) -> int:
        """Выполнить INSERT/UPDATE/DELETE"""
        result = self._make_request('/api/execute', {'query': sql, 'params': params or []})
        if not result.get('success'):
            raise Exception(f"Ошибка выполнения: {result.get('error')}")
        return result.get('last_id')
    
    def execute_many(self, queries: list) -> list:
        """Выполнить несколько запросов в одной транзакции"""
        result = self._make_request('/api/execute_many', {'queries': queries})
        if not result.get('success'):
            raise Exception(f"Ошибка транзакции: {result.get('error')}")
        return result.get('results', [])
    
    def health_check(self) -> bool:
        """Проверить работоспособность сервера"""
        try:
            result = self._make_request('/api/health', method='GET')
            return result.get('status') == 'ok'
        except:
            return False
    
    def get_info(self) -> dict:
        """Получить информацию о сервере и БД"""
        result = self._make_request('/api/info', method='GET')
        if not result.get('success'):
            raise Exception(f"Ошибка: {result.get('error')}")
        return result.get('info', {})


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
    print("=" * 60)
    print("Режим работы программы")
    print("=" * 60)
    print(f"Режим: {MODE}")
    
    if MODE == 'server':
        print(f"Сервер: {SERVER_URL}")
        try:
            client = get_server_client()
            if client.health_check():
                print("Статус: ✓ Сервер доступен")
            else:
                print("Статус: ✗ Сервер недоступен")
        except Exception as e:
            print(f"Статус: ✗ Ошибка подключения: {e}")
    else:
        print("Режим: Локальная база данных")
    
    print("=" * 60)


if __name__ == "__main__":
    print_mode_info()