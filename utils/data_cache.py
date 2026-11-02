"""
Кэш данных в памяти для ускорения работы с часто используемыми данными.
"""
import time
import threading
from typing import Any, Optional


class DataCache:
    """
    Кэш для хранения данных в памяти.
    Поддерживает TTL и автоматическую инвалидацию.
    """
    
    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: время жизни записи по умолчанию (в секундах)
        """
        self.cache = {}
        self.timestamps = {}
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        with self.lock:
            if key in self.cache:
                if time.time() - self.timestamps[key] < self.default_ttl:
                    return self.cache[key]
                else:
                    # Запись устарела
                    del self.cache[key]
                    del self.timestamps[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Сохранить значение в кэш"""
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def invalidate(self, key_pattern: str = None):
        """
        Инвалидировать записи в кэше.
        
        Args:
            key_pattern: если None — очистить весь кэш,
                        иначе — удалить записи, содержащие pattern
        """
        with self.lock:
            if key_pattern is None:
                self.cache.clear()
                self.timestamps.clear()
            else:
                keys_to_delete = [
                    k for k in self.cache.keys()
                    if key_pattern.lower() in k.lower()
                ]
                for key in keys_to_delete:
                    del self.cache[key]
                    del self.timestamps[key]
    
    def cleanup_expired(self):
        """Удалить устаревшие записи"""
        current_time = time.time()
        with self.lock:
            expired_keys = [
                key for key, timestamp in self.timestamps.items()
                if current_time - timestamp >= self.default_ttl
            ]
            for key in expired_keys:
                del self.cache[key]
                del self.timestamps[key]
    
    def size(self) -> int:
        """Получить размер кэша"""
        with self.lock:
            return len(self.cache)
    
    def clear(self):
        """Полностью очистить кэш"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()


# Глобальный кэш данных
data_cache = DataCache(default_ttl=300)