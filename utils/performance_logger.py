"""
Логирование производительности.
Позволяет отслеживать медленные операции и диагностировать проблемы.
"""
import time
import logging
import os
from functools import wraps
from typing import Callable


# ============================================================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================

def setup_performance_logger(log_file: str = 'performance.log', 
                            level: int = logging.INFO):
    """
    Настроить логгер производительности.
    
    Args:
        log_file: путь к файлу лога
        level: уровень логирования
    """
    logger = logging.getLogger('performance')
    logger.setLevel(level)
    
    # Удаляем старые обработчики
    logger.handlers.clear()
    
    # Создаём файловый обработчик
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setLevel(level)
    
    # Формат сообщений
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


# Глобальный логгер
_logger = None


def get_logger() -> logging.Logger:
    """Получить глобальный логгер производительности"""
    global _logger
    if _logger is None:
        _logger = setup_performance_logger()
    return _logger


# ============================================================================
# ДЕКОРАТОРЫ ДЛЯ ЛОГИРОВАНИЯ
# ============================================================================

def log_slow_operations(threshold: float = 1.0):
    """
    Декоратор для логирования медленных операций.
    
    Args:
        threshold: порог в секундах, после которого операция считается медленной
    
    Использование:
        @log_slow_operations(threshold=0.5)
        def my_function():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                if duration > threshold:
                    logger = get_logger()
                    logger.warning(
                        f"Медленная операция: {func.__module__}.{func.__name__} "
                        f"выполнялась {duration:.3f} сек"
                    )
        
        return wrapper
    return decorator


def log_all_operations(level: int = logging.DEBUG):
    """
    Декоратор для логирования всех операций.
    
    Args:
        level: уровень логирования
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            logger.log(level, f"Начало: {func.__module__}.{func.__name__}")
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.log(level, 
                          f"Завершено: {func.__module__}.{func.__name__} "
                          f"({duration:.3f} сек)")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Ошибка: {func.__module__}.{func.__name__} "
                    f"({duration:.3f} сек): {e}"
                )
                raise
        
        return wrapper
    return decorator


# ============================================================================
# КОНТЕКСТНЫЙ МЕНЕДЖЕР ДЛЯ ИЗМЕРЕНИЯ ВРЕМЕНИ
# ============================================================================

class Timer:
    """
    Контекстный менеджер для измерения времени выполнения блока кода.
    
    Использование:
        with Timer("Загрузка данных") as t:
            load_data()
        print(f"Время: {t.duration}")
    """
    
    def __init__(self, name: str = "Операция", log_threshold: float = None):
        """
        Args:
            name: имя операции для логирования
            log_threshold: если указано, логировать только если время превышает порог
        """
        self.name = name
        self.log_threshold = log_threshold
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        
        if self.log_threshold is None or self.duration > self.log_threshold:
            logger = get_logger()
            logger.info(f"{self.name}: {self.duration:.3f} сек")
        
        return False


# ============================================================================
# СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ
# ============================================================================

class PerformanceStats:
    """
    Сбор статистики производительности.
    """
    
    def __init__(self):
        self.operations = {}
        self._lock = __import__('threading').Lock()
    
    def record_operation(self, name: str, duration: float):
        """Записать время выполнения операции"""
        with self._lock:
            if name not in self.operations:
                self.operations[name] = {
                    'count': 0,
                    'total_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'times': []
                }
            
            stats = self.operations[name]
            stats['count'] += 1
            stats['total_time'] += duration
            stats['min_time'] = min(stats['min_time'], duration)
            stats['max_time'] = max(stats['max_time'], duration)
            
            # Храним только последние 100 значений
            stats['times'].append(duration)
            if len(stats['times']) > 100:
                stats['times'].pop(0)
    
    def get_stats(self, name: str) -> dict:
        """Получить статистику по операции"""
        with self._lock:
            if name not in self.operations:
                return None
            
            stats = self.operations[name]
            
            return {
                'count': stats['count'],
                'avg_time': stats['total_time'] / stats['count'],
                'min_time': stats['min_time'],
                'max_time': stats['max_time'],
                'total_time': stats['total_time'],
                'recent_avg': sum(stats['times'][-10:]) / min(10, len(stats['times']))
            }
    
    def get_all_stats(self) -> dict:
        """Получить статистику по всем операциям"""
        with self._lock:
            return {
                name: self.get_stats(name)
                for name in self.operations
            }
    
    def clear(self):
        """Очистить статистику"""
        with self._lock:
            self.operations.clear()


# Глобальная статистика
_stats = PerformanceStats()


def get_performance_stats() -> PerformanceStats:
    """Получить глобальную статистику производительности"""
    return _stats