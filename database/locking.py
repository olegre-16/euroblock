"""
Система блокировок записей для многопользовательской работы.
Использует ТОЛЬКО стандартные библиотеки Python.
"""
import os
import time
import json
import threading
import getpass
from typing import Optional


class RecordLock:
    """Система блокировок записей на основе файлов"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock_file = db_path + '.locks'
        self.user_id = f"{os.getpid()}_{int(time.time())}"
        self._lock = threading.Lock()
        self._local_locks = set()
    
    def acquire_lock(self, table_name: str, record_id, timeout: float = 10.0) -> bool:
        """Получить блокировку на запись"""
        lock_key = f"{table_name}:{record_id}"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                locks = self._read_locks()
                
                if lock_key in locks:
                    lock_info = locks[lock_key]
                    if lock_info.get('user_id') == self.user_id:
                        self._local_locks.add(lock_key)
                        return True
                    if time.time() - lock_info.get('timestamp', 0) > 60:
                        del locks[lock_key]
                        self._write_locks(locks)
                        continue
                    time.sleep(0.5)
                    continue
                
                locks[lock_key] = {
                    'user_id': self.user_id,
                    'timestamp': time.time(),
                    'user_name': self._get_user_name()
                }
                self._write_locks(locks)
                self._local_locks.add(lock_key)
                return True
        
        return False
    
    def release_lock(self, table_name: str, record_id):
        """Освободить блокировку"""
        lock_key = f"{table_name}:{record_id}"
        with self._lock:
            locks = self._read_locks()
            if lock_key in locks:
                lock_info = locks[lock_key]
                if lock_info.get('user_id') == self.user_id:
                    del locks[lock_key]
                    self._write_locks(locks)
            self._local_locks.discard(lock_key)
    
    def release_all_locks(self):
        """Освободить все блокировки этого клиента"""
        with self._lock:
            locks = self._read_locks()
            keys_to_remove = [
                key for key, info in locks.items()
                if info.get('user_id') == self.user_id
            ]
            for key in keys_to_remove:
                del locks[key]
            self._write_locks(locks)
            self._local_locks.clear()
    
    def is_locked(self, table_name: str, record_id) -> bool:
        """Проверить, заблокирована ли запись"""
        lock_key = f"{table_name}:{record_id}"
        with self._lock:
            locks = self._read_locks()
            if lock_key not in locks:
                return False
            lock_info = locks[lock_key]
            if lock_info.get('user_id') == self.user_id:
                return False
            if time.time() - lock_info.get('timestamp', 0) > 60:
                return False
            return True
    
    def get_lock_info(self, table_name: str, record_id) -> Optional[dict]:
        """Получить информацию о блокировке"""
        lock_key = f"{table_name}:{record_id}"
        with self._lock:
            locks = self._read_locks()
            return locks.get(lock_key)
    
    def _read_locks(self) -> dict:
        if not os.path.exists(self.lock_file):
            return {}
        try:
            with open(self.lock_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _write_locks(self, locks: dict):
        try:
            with open(self.lock_file, 'w', encoding='utf-8') as f:
                json.dump(locks, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Ошибка записи файла блокировок: {e}")
    
    def _get_user_name(self) -> str:
        try:
            return getpass.getuser()
        except:
            return 'unknown'
    
    def cleanup_stale_locks(self, max_age: float = 300.0):
        """Очистить устаревшие блокировки"""
        with self._lock:
            locks = self._read_locks()
            current_time = time.time()
            keys_to_remove = [
                key for key, info in locks.items()
                if current_time - info.get('timestamp', 0) > max_age
            ]
            for key in keys_to_remove:
                del locks[key]
            if keys_to_remove:
                self._write_locks(locks)


_lock_manager = None


def get_lock_manager(db_path: str) -> RecordLock:
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = RecordLock(db_path)
    return _lock_manager