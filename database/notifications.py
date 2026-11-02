"""
Система уведомлений об изменениях в базе данных.
Использует ТОЛЬКО стандартные библиотеки Python.
"""
import os
import time
import json
import threading
from typing import Callable, List, Dict, Any


class ChangeNotifier:
    """Система уведомлений об изменениях в БД через файлы"""
    
    def __init__(self, db_path: str, check_interval: float = 1.0):
        self.db_path = db_path
        self.notification_file = db_path + '.notifications'
        self.check_interval = check_interval
        self.last_check = time.time()
        self.listeners: List[Callable] = []
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self.client_id = f"{os.getpid()}_{int(time.time())}"
    
    def notify_change(self, table_name: str, operation: str, 
                     record_id: Any = None, user: str = None):
        """Уведомить об изменении в базе данных"""
        notification = {
            'timestamp': time.time(),
            'client_id': self.client_id,
            'user': user or 'unknown',
            'table': table_name,
            'operation': operation,
            'record_id': record_id
        }
        
        with self._lock:
            try:
                with open(self.notification_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(notification, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"Ошибка записи уведомления: {e}")
    
    def start_listening(self, callback: Callable[[Dict], None]):
        """Начать слушать изменения"""
        self.listeners.append(callback)
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
    
    def stop(self):
        """Остановить прослушивание"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
    
    def _listen_loop(self):
        while self._running:
            try:
                self._check_notifications()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Ошибка в цикле уведомлений: {e}")
                time.sleep(5)
    
    def _check_notifications(self):
        if not os.path.exists(self.notification_file):
            return
        
        try:
            with self._lock:
                with open(self.notification_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_notifications = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        notification = json.loads(line)
                        if notification.get('client_id') == self.client_id:
                            continue
                        if notification.get('timestamp', 0) <= self.last_check:
                            continue
                        new_notifications.append(notification)
                    except json.JSONDecodeError:
                        continue
                
                if len(lines) > 1000:
                    self._cleanup_notifications()
                
                if new_notifications:
                    self.last_check = max(n['timestamp'] for n in new_notifications)
                    for notification in new_notifications:
                        for listener in self.listeners:
                            try:
                                listener(notification)
                            except Exception as e:
                                print(f"Ошибка в обработчике уведомления: {e}")
        except Exception as e:
            print(f"Ошибка чтения уведомлений: {e}")
    
    def _cleanup_notifications(self):
        try:
            if not os.path.exists(self.notification_file):
                return
            with open(self.notification_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            with open(self.notification_file, 'w', encoding='utf-8') as f:
                f.writelines(recent_lines)
        except Exception as e:
            print(f"Ошибка очистки уведомлений: {e}")
    
    def clear_all(self):
        with self._lock:
            try:
                if os.path.exists(self.notification_file):
                    os.remove(self.notification_file)
            except Exception as e:
                print(f"Ошибка очистки файла уведомлений: {e}")


_notifier = None


def get_notifier(db_path: str) -> ChangeNotifier:
    global _notifier
    if _notifier is None:
        _notifier = ChangeNotifier(db_path)
    return _notifier