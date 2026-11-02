"""
Сервер для многопользовательской работы с программой ООО Евроблок.
Использует ТОЛЬКО стандартные библиотеки Python (http.server).

Запуск:
    python server.py

Клиенты подключаются по адресу:
    http://IP_СЕРВЕРА:5000
"""
import os
import sys
import json
import sqlite3
import threading
import logging
import socket
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import DB_PATH, init_database, get_database_info

# ============================================================================
# НАСТРОЙКИ
# ============================================================================

SERVER_PORT = 5000
db_lock = threading.Lock()

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# ФУНКЦИИ РАБОТЫ С БД
# ============================================================================

def get_connection():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn


# ============================================================================
# HTTP ОБРАБОТЧИК
# ============================================================================

class EuroblockHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для API сервера"""
    
    def log_message(self, format, *args):
        """Переопределяем логирование"""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def _send_json_response(self, data, status=200):
        """Отправить JSON-ответ"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _read_json_body(self):
        """Прочитать JSON из тела запроса"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return None
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))
    
    def do_OPTIONS(self):
        """Обработка OPTIONS запроса (CORS preflight)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            if path == '/api/health':
                self._handle_health()
            elif path == '/api/info':
                self._handle_info()
            else:
                self._send_json_response({'success': False, 'error': 'Not found'}, 404)
        except Exception as e:
            logger.error(f"Ошибка обработки GET {path}: {e}")
            self._send_json_response({'success': False, 'error': str(e)}, 500)
    
    def do_POST(self):
        """Обработка POST запросов"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            if path == '/api/query':
                self._handle_query()
            elif path == '/api/execute':
                self._handle_execute()
            elif path == '/api/execute_many':
                self._handle_execute_many()
            else:
                self._send_json_response({'success': False, 'error': 'Not found'}, 404)
        except Exception as e:
            logger.error(f"Ошибка обработки POST {path}: {e}")
            self._send_json_response({'success': False, 'error': str(e)}, 500)
    
    def _handle_health(self):
        """Проверка работоспособности сервера"""
        self._send_json_response({
            'status': 'ok',
            'database': os.path.exists(DB_PATH),
            'timestamp': time.time()
        })
    
    def _handle_info(self):
        """Получить информацию о сервере и БД"""
        info = get_database_info()
        self._send_json_response({
            'success': True,
            'info': info
        })
    
    def _handle_query(self):
        """Выполнить SELECT-запрос"""
        data = self._read_json_body()
        
        if not data or 'query' not in data:
            self._send_json_response({'success': False, 'error': 'Missing query'}, 400)
            return
        
        query = data['query']
        params = data.get('params', [])
        
        with db_lock:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
                conn.close()
                self._send_json_response({'success': True, 'data': result})
            except Exception as e:
                logger.error(f"Ошибка выполнения запроса: {e}")
                self._send_json_response({'success': False, 'error': str(e)}, 500)
    
    def _handle_execute(self):
        """Выполнить INSERT/UPDATE/DELETE"""
        data = self._read_json_body()
        
        if not data or 'query' not in data:
            self._send_json_response({'success': False, 'error': 'Missing query'}, 400)
            return
        
        query = data['query']
        params = data.get('params', [])
        
        with db_lock:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                last_id = cursor.lastrowid
                conn.close()
                self._send_json_response({'success': True, 'last_id': last_id})
            except Exception as e:
                logger.error(f"Ошибка выполнения команды: {e}")
                self._send_json_response({'success': False, 'error': str(e)}, 500)
    
    def _handle_execute_many(self):
        """Выполнить несколько запросов в одной транзакции"""
        data = self._read_json_body()
        
        if not data or 'queries' not in data:
            self._send_json_response({'success': False, 'error': 'Missing queries'}, 400)
            return
        
        queries = data['queries']
        
        with db_lock:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                results = []
                for q in queries:
                    cursor.execute(q['query'], q.get('params', []))
                    results.append({
                        'last_id': cursor.lastrowid,
                        'rowcount': cursor.rowcount
                    })
                conn.commit()
                conn.close()
                self._send_json_response({'success': True, 'results': results})
            except Exception as e:
                logger.error(f"Ошибка выполнения транзакции: {e}")
                self._send_json_response({'success': False, 'error': str(e)}, 500)


# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

def get_local_ip():
    """Получить локальный IP-адрес"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Сервер ООО Евроблок")
    logger.info("=" * 60)
    logger.info(f"База данных: {DB_PATH}")
    logger.info(f"Порт: {SERVER_PORT}")
    logger.info("")
    
    # Инициализируем БД
    init_database()
    
    # Получаем IP
    ip_address = get_local_ip()
    
    logger.info("Сервер запущен!")
    logger.info("")
    logger.info("Клиенты могут подключаться по адресам:")
    logger.info(f"  http://{ip_address}:{SERVER_PORT}")
    logger.info(f"  http://localhost:{SERVER_PORT}")
    logger.info("")
    logger.info("Для остановки нажмите Ctrl+C")
    logger.info("=" * 60)
    
    # Запускаем сервер
    server = HTTPServer(('0.0.0.0', SERVER_PORT), EuroblockHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nСервер остановлен пользователем")
        server.server_close()