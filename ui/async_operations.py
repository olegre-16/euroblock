"""
Модуль для асинхронных операций в UI.
Позволяет выполнять длительные операции в отдельных потоках,
не блокируя интерфейс.
"""
import threading
import tkinter as tk
from queue import Queue, Empty
from typing import Callable, Any, Optional


class AsyncOperation:
    """
    Класс для выполнения асинхронных операций с обратным вызовом.
    
    Пример использования:
        async_op = AsyncOperation(parent_window)
        async_op.run_async(
            operation=long_running_function,
            callback=on_complete,
            error_callback=on_error,
            args=(arg1, arg2)
        )
    """
    
    def __init__(self, parent_window):
        """
        Args:
            parent_window: родительское окно Tkinter
        """
        self.parent = parent_window
        self.result_queue = Queue()
        self.current_thread = None
    
    def run_async(self, operation: Callable, callback: Callable,
                  error_callback: Optional[Callable] = None,
                  args: tuple = (), kwargs: dict = None):
        """
        Выполнить операцию асинхронно.
        
        Args:
            operation: функция для выполнения
            callback: функция обратного вызова при успехе
            error_callback: функция обратного вызова при ошибке
            args: аргументы для operation
            kwargs: именованные аргументы для operation
        """
        if kwargs is None:
            kwargs = {}
        
        def worker():
            try:
                result = operation(*args, **kwargs)
                self.result_queue.put(('success', result))
            except Exception as e:
                self.result_queue.put(('error', e))
        
        self.current_thread = threading.Thread(target=worker, daemon=True)
        self.current_thread.start()
        
        # Запускаем проверку результата
        self._check_result(callback, error_callback)
    
    def _check_result(self, callback: Callable, error_callback: Optional[Callable]):
        """Периодически проверяет результат в основном потоке"""
        try:
            status, data = self.result_queue.get_nowait()
            
            if status == 'success':
                if callback:
                    callback(data)
            else:  # error
                if error_callback:
                    error_callback(data)
                else:
                    # Если error_callback не указан, показываем ошибку
                    from tkinter import messagebox
                    messagebox.showerror("Ошибка", f"Произошла ошибка:\n{data}")
        except Empty:
            # Результат ещё не готов, проверяем позже
            self.parent.after(100, lambda: self._check_result(callback, error_callback))


class AsyncTaskManager:
    """
    Менеджер для управления несколькими асинхронными задачами.
    Позволяет отслеживать прогресс и отменять задачи.
    """
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.tasks = {}
        self.task_counter = 0
        self.lock = threading.Lock()
    
    def submit(self, operation: Callable, callback: Callable,
               error_callback: Optional[Callable] = None,
               args: tuple = (), kwargs: dict = None) -> int:
        """
        Отправить задачу на выполнение.
        
        Returns:
            ID задачи для отслеживания
        """
        with self.lock:
            self.task_counter += 1
            task_id = self.task_counter
        
        async_op = AsyncOperation(self.parent)
        
        def wrapped_callback(result):
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
            if callback:
                callback(result)
        
        def wrapped_error_callback(error):
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
            if error_callback:
                error_callback(error)
        
        with self.lock:
            self.tasks[task_id] = async_op
        
        async_op.run_async(operation, wrapped_callback, 
                          wrapped_error_callback, args, kwargs)
        
        return task_id
    
    def get_active_count(self) -> int:
        """Получить количество активных задач"""
        with self.lock:
            return len(self.tasks)
    
    def cancel_all(self):
        """Отменить все задачи (помечает их как отменённые)"""
        with self.lock:
            self.tasks.clear()


class PeriodicTask:
    """
    Класс для выполнения периодических задач.
    Полезно для автообновления данных, проверки изменений и т.д.
    """
    
    def __init__(self, parent_window, interval_ms: int, task: Callable):
        """
        Args:
            parent_window: родительское окно Tkinter
            interval_ms: интервал выполнения в миллисекундах
            task: функция для выполнения
        """
        self.parent = parent_window
        self.interval_ms = interval_ms
        self.task = task
        self.running = False
        self.task_id = None
    
    def start(self):
        """Запустить периодическое выполнение"""
        self.running = True
        self._execute()
    
    def stop(self):
        """Остановить выполнение"""
        self.running = False
        if self.task_id:
            self.parent.after_cancel(self.task_id)
            self.task_id = None
    
    def _execute(self):
        """Выполнить задачу и запланировать следующее выполнение"""
        if not self.running:
            return
        
        try:
            self.task()
        except Exception as e:
            print(f"Ошибка в периодической задаче: {e}")
        
        if self.running:
            self.task_id = self.parent.after(self.interval_ms, self._execute)


# ============================================================================
# УТИЛИТЫ ДЛЯ РАБОТЫ С ПОТОКАМИ
# ============================================================================

def run_in_thread(func: Callable, *args, **kwargs):
    """
    Выполнить функцию в отдельном потоке.
    Простая утилита для быстрого запуска.
    """
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


def run_on_main_thread(parent_window, func: Callable, *args, **kwargs):
    """
    Выполнить функцию в главном потоке Tkinter.
    Полезно для обновления UI из фонового потока.
    """
    parent_window.after(0, lambda: func(*args, **kwargs))


class ThreadSafeVar:
    """
    Потокобезопасная переменная для обмена данными между потоками.
    """
    
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def get(self):
        with self._lock:
            return self._value
    
    def set(self, value):
        with self._lock:
            self._value = value