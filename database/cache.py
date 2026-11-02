"""
Кэш запросов для ускорения повторяющихся операций.
Использует ТОЛЬКО стандартные библиотеки Python.
"""
import time
import threading
import hashlib
import json


class QueryCache:
    """Кэш для результатов запросов к базе данных"""
    
    def __init__(self, max_size=500, default_ttl=300):
        self.cache = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        def cleanup_loop():
            while True:
                try:
                    time.sleep(60)
                    self._cleanup_expired()
                except Exception as e:
                    print(f"Ошибка в потоке очистки кэша: {e}")
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def _cleanup_expired(self):
        current_time = time.time()
        with self.lock:
            expired_keys = [
                key for key, (value, timestamp, ttl) in self.cache.items()
                if current_time - timestamp > ttl
            ]
            for key in expired_keys:
                del self.cache[key]
    
    def _make_key(self, query, params=None):
        key_data = f"{query}|{json.dumps(params or [], default=str, ensure_ascii=False)}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, query, params=None):
        key = self._make_key(query, params)
        with self.lock:
            if key in self.cache:
                value, timestamp, ttl = self.cache[key]
                if time.time() - timestamp < ttl:
                    self.hits += 1
                    return value
                else:
                    del self.cache[key]
            self.misses += 1
            return None
    
    def set(self, query, value, params=None, ttl=None):
        key = self._make_key(query, params)
        actual_ttl = ttl if ttl is not None else self.default_ttl
        with self.lock:
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            self.cache[key] = (value, time.time(), actual_ttl)
    
    def _evict_oldest(self):
        if not self.cache:
            return
        sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
        count_to_remove = max(1, len(sorted_items) // 10)
        for i in range(count_to_remove):
            del self.cache[sorted_items[i][0]]
    
    def invalidate(self, pattern=None):
        with self.lock:
            if pattern is None:
                self.cache.clear()
            else:
                keys_to_delete = [
                    key for key in self.cache.keys()
                    if pattern.lower() in key.lower()
                ]
                for key in keys_to_delete:
                    del self.cache[key]
    
    def invalidate_table(self, table_name):
        self.invalidate(table_name)
    
    def get_stats(self):
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2)
            }
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0


query_cache = QueryCache(max_size=500, default_ttl=300)