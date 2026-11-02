"""
Скрипт для регулярного обслуживания базы данных.
Использует ТОЛЬКО стандартные библиотеки Python (threading.Timer).

Запуск:
    python maintenance.py daily      - ежедневное обслуживание
    python maintenance.py weekly     - еженедельное обслуживание
    python maintenance.py scheduler  - запуск планировщика
    python maintenance.py backup     - создать резервную копию
"""
import os
import sys
import time
import shutil
import logging
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import (
    get_connection, return_connection, optimize_database, 
    get_database_info, DB_PATH
)
from database.locking import get_lock_manager

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintenance.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# ФУНКЦИИ ОБСЛУЖИВАНИЯ
# ============================================================================

def daily_maintenance():
    """Ежедневное обслуживание базы данных"""
    logger.info("=" * 60)
    logger.info("Начало ежедневного обслуживания")
    logger.info("=" * 60)
    
    try:
        logger.info("Оптимизация базы данных...")
        optimize_database()
        logger.info("✓ База данных оптимизирована")
        
        info = get_database_info()
        logger.info(f"Размер БД: {info['size_mb']} МБ")
        
        if info['size_mb'] > 100:
            logger.warning(f"⚠ Размер БД превышает 100 МБ ({info['size_mb']} МБ)")
        
        disk_usage = check_disk_space()
        logger.info(f"Свободно на диске: {disk_usage['free_gb']:.2f} ГБ")
        
        if disk_usage['free_gb'] < 1:
            logger.error("⚠ Критически мало места на диске!")
        
        cleanup_notification_files()
        cleanup_stale_locks()
        
        logger.info("✓ Ежедневное обслуживание завершено успешно")
    except Exception as e:
        logger.error(f"✗ Ошибка при обслуживании: {e}")
        raise


def weekly_maintenance():
    """Еженедельное обслуживание"""
    logger.info("=" * 60)
    logger.info("Начало еженедельного обслуживания")
    logger.info("=" * 60)
    
    try:
        daily_maintenance()
        check_database_integrity()
        create_backup()
        logger.info("✓ Еженедельное обслуживание завершено успешно")
    except Exception as e:
        logger.error(f"✗ Ошибка при обслуживании: {e}")
        raise


def check_database_integrity():
    """Проверить целостность базы данных"""
    logger.info("Проверка целостности базы данных...")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        if result[0] == 'ok':
            logger.info("✓ База данных целостна")
        else:
            logger.error(f"✗ Обнаружены проблемы с целостностью: {result[0]}")
    finally:
        return_connection(conn)


def check_disk_space() -> dict:
    """Проверить свободное место на диске"""
    try:
        total, used, free = shutil.disk_usage(os.path.dirname(DB_PATH))
        return {
            'total_gb': total / (1024**3),
            'used_gb': used / (1024**3),
            'free_gb': free / (1024**3),
            'percent_used': (used / total) * 100
        }
    except Exception as e:
        logger.error(f"Ошибка проверки дискового пространства: {e}")
        return {'free_gb': 0}


def cleanup_notification_files():
    """Очистить старые файлы уведомлений"""
    notification_file = DB_PATH + '.notifications'
    if os.path.exists(notification_file):
        try:
            if os.path.getsize(notification_file) > 1024 * 1024:
                os.remove(notification_file)
                logger.info("✓ Файл уведомлений очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки файла уведомлений: {e}")


def cleanup_stale_locks():
    """Очистить устаревшие блокировки"""
    try:
        lock_manager = get_lock_manager(DB_PATH)
        lock_manager.cleanup_stale_locks(max_age=300)
        logger.info("✓ Устаревшие блокировки очищены")
    except Exception as e:
        logger.error(f"Ошибка очистки блокировок: {e}")


def create_backup():
    """Создать резервную копию базы данных"""
    if not os.path.exists(DB_PATH):
        logger.warning("База данных не существует, резервная копия не создана")
        return
    
    try:
        backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'euroblock_backup_{timestamp}.db')
        
        shutil.copy2(DB_PATH, backup_file)
        logger.info(f"✓ Резервная копия создана: {backup_file}")
        
        cleanup_old_backups(backup_dir, keep_last=7)
    except Exception as e:
        logger.error(f"Ошибка создания резервной копии: {e}")


def cleanup_old_backups(backup_dir: str, keep_last: int = 7):
    """Удалить старые резервные копии"""
    try:
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.startswith('euroblock_backup_') and filename.endswith('.db'):
                filepath = os.path.join(backup_dir, filename)
                backups.append((filepath, os.path.getmtime(filepath)))
        
        backups.sort(key=lambda x: x[1], reverse=True)
        
        for filepath, _ in backups[keep_last:]:
            os.remove(filepath)
            logger.info(f"Удалён старый бэкап: {os.path.basename(filepath)}")
    except Exception as e:
        logger.error(f"Ошибка очистки старых бэкапов: {e}")


# ============================================================================
# ПЛАНИРОВЩИК ЗАДАЧ (на threading.Timer)
# ============================================================================

class SimpleScheduler:
    """
    Простой планировщик задач на основе threading.Timer.
    Не требует внешних библиотек.
    """
    
    def __init__(self):
        self.tasks = []
        self._running = False
        self._thread = None
    
    def add_daily(self, time_str: str, task):
        """
        Добавить ежедневную задачу.
        
        Args:
            time_str: время выполнения в формате "HH:MM"
            task: функция для выполнения
        """
        self.tasks.append({
            'type': 'daily',
            'time': time_str,
            'task': task,
            'last_run': None
        })
    
    def add_weekly(self, day_of_week: int, time_str: str, task):
        """
        Добавить еженедельную задачу.
        
        Args:
            day_of_week: день недели (0=понедельник, 6=воскресенье)
            time_str: время выполнения в формате "HH:MM"
            task: функция для выполнения
        """
        self.tasks.append({
            'type': 'weekly',
            'day': day_of_week,
            'time': time_str,
            'task': task,
            'last_run': None
        })
    
    def start(self):
        """Запустить планировщик"""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("✓ Планировщик запущен")
    
    def stop(self):
        """Остановить планировщик"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run_loop(self):
        """Основной цикл планировщика"""
        while self._running:
            try:
                now = datetime.now()
                
                for task_info in self.tasks:
                    if self._should_run_task(task_info, now):
                        try:
                            logger.info(f"Запуск задачи: {task_info['task'].__name__}")
                            task_info['task']()
                            task_info['last_run'] = now
                        except Exception as e:
                            logger.error(f"Ошибка выполнения задачи: {e}")
                
                time.sleep(30)  # Проверяем каждые 30 секунд
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                time.sleep(60)
    
    def _should_run_task(self, task_info: dict, now: datetime) -> bool:
        """Проверить, нужно ли запускать задачу"""
        time_str = task_info['time']
        try:
            hour, minute = map(int, time_str.split(':'))
        except:
            return False
        
        last_run = task_info['last_run']
        
        if task_info['type'] == 'daily':
            # Проверяем, что сегодня ещё не запускали в это время
            if now.hour == hour and now.minute == minute:
                if last_run is None or last_run.date() < now.date():
                    return True
            return False
        
        elif task_info['type'] == 'weekly':
            # Проверяем день недели и время
            if now.weekday() == task_info['day'] and now.hour == hour and now.minute == minute:
                if last_run is None or (now - last_run).days >= 7:
                    return True
            return False
        
        return False


def run_scheduler():
    """Запустить планировщик задач обслуживания"""
    logger.info("Запуск планировщика задач обслуживания...")
    
    scheduler = SimpleScheduler()
    
    # Ежедневное обслуживание в 3:00
    scheduler.add_daily("03:00", daily_maintenance)
    logger.info("  - Ежедневное обслуживание: 03:00")
    
    # Еженедельное обслуживание в воскресенье в 4:00
    scheduler.add_weekly(6, "04:00", weekly_maintenance)  # 6 = воскресенье
    logger.info("  - Еженедельное обслуживание: воскресенье 04:00")
    
    scheduler.start()
    
    # Основной цикл
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Планировщик остановлен пользователем")
        scheduler.stop()


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Обслуживание базы данных')
    parser.add_argument('command', choices=['daily', 'weekly', 'scheduler', 'backup'],
                       help='Команда для выполнения')
    
    args = parser.parse_args()
    
    if args.command == 'daily':
        daily_maintenance()
    elif args.command == 'weekly':
        weekly_maintenance()
    elif args.command == 'scheduler':
        run_scheduler()
    elif args.command == 'backup':
        create_backup()