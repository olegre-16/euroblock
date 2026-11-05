"""
Репозитории для работы с таблицами базы данных.
Каждая группа функций отвечает за одну таблицу.
[ИЗМЕНЕНО]
- CementReceiptsRepository: добавлены алиасы, delete_receipt возвращает кортеж,
  сортировка через substr()
- ReservedProductsRepository: добавлены алиасы, метод update(), новая таблица
  reserve_realizations для связи резерв→реализация
- SalesRepository: добавлен метод add_with_id() для возврата ID записи
"""
import sqlite3
from database.connection import get_connection, return_connection


class DictionaryRepository:
    """Универсальный репозиторий для простых справочников"""
    def __init__(self, table_name):
        self.table_name = table_name
    
    def get_all(self):
        """Получить все записи (только название, отсортировано по алфавиту)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT name FROM {self.table_name} ORDER BY name COLLATE NOCASE')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_id(self, name):
        """Получить id записи по названию"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT id FROM {self.table_name} WHERE name = ?', (name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def add(self, name):
        """Добавить запись. Возвращает (успех, сообщение)"""
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        name = name.strip()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'INSERT INTO {self.table_name} (name) VALUES (?)', (name,))
            conn.commit()
            return True, "Запись добавлена"
        except sqlite3.IntegrityError:
            return False, "Такая запись уже существует"
        finally:
            conn.close()
    
    def delete(self, name):
        """Удалить запись по названию"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM {self.table_name} WHERE name = ?', (name,))
        conn.commit()
        conn.close()


class ProductsRepository:
    """Специализированный репозиторий для продукции (с дополнительными полями)"""
    def __init__(self):
        self.table_name = 'products'
    
    def get_all(self):
        """
        Получить все записи: (name, volume_per_pallet, production_rate)
        Сортировка:
        1. Сначала записи БЕЗ "(брак)" — по алфавиту
        2. Затем записи С "(брак)" — по алфавиту
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT name, volume_per_pallet, production_rate 
            FROM {self.table_name} 
            ORDER BY 
                CASE WHEN name LIKE '%(брак)%' THEN 1 ELSE 0 END,
                name COLLATE NOCASE
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def add(self, name, volume_per_pallet=None, production_rate=None):
        """Добавить запись"""
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        name = name.strip()
        vol = self._parse_number(volume_per_pallet)
        rate = self._parse_number(production_rate)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'INSERT INTO {self.table_name} (name, volume_per_pallet, production_rate) VALUES (?, ?, ?)',
                (name, vol, rate)
            )
            conn.commit()
            return True, "Продукция добавлена"
        except sqlite3.IntegrityError:
            return False, "Такая продукция уже существует"
        finally:
            conn.close()
    
    def update(self, old_name, new_name, volume_per_pallet=None, production_rate=None):
        """Обновить запись"""
        if not new_name or not new_name.strip():
            return False, "Название не может быть пустым"
        new_name = new_name.strip()
        vol = self._parse_number(volume_per_pallet)
        rate = self._parse_number(production_rate)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'''UPDATE {self.table_name} 
                    SET name = ?, volume_per_pallet = ?, production_rate = ? 
                    WHERE name = ?''',
                (new_name, vol, rate, old_name)
            )
            conn.commit()
            return True, "Запись обновлена"
        except sqlite3.IntegrityError:
            return False, "Такая продукция уже существует"
        finally:
            conn.close()
    
    def delete(self, name):
        """Удалить запись по названию"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM {self.table_name} WHERE name = ?', (name,))
        conn.commit()
        conn.close()
    
    def _parse_number(self, value):
        """Преобразовать значение в число или None"""
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return None


class CementSilosRepository:
    """Специализированный репозиторий для силосов цемента (с полем capacity)"""
    def __init__(self):
        self.table_name = 'cement_silos'
    
    def get_all(self):
        """Получить все записи: (name, capacity), отсортировано по алфавиту"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT name, capacity 
            FROM {self.table_name} 
            ORDER BY name COLLATE NOCASE
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def add(self, name, capacity=None):
        """Добавить силос цемента с указанием вмещаемого объема"""
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        name = name.strip()
        cap = self._parse_number(capacity)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'INSERT INTO {self.table_name} (name, capacity) VALUES (?, ?)',
                (name, cap)
            )
            conn.commit()
            return True, "Силос цемента добавлен"
        except sqlite3.IntegrityError:
            return False, "Такой силос цемента уже существует"
        finally:
            conn.close()
    
    def update(self, old_name, new_name, capacity=None):
        """Обновить запись о силосе цемента"""
        if not new_name or not new_name.strip():
            return False, "Название не может быть пустым"
        new_name = new_name.strip()
        cap = self._parse_number(capacity)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'''UPDATE {self.table_name} 
                    SET name = ?, capacity = ? 
                    WHERE name = ?''',
                (new_name, cap, old_name)
            )
            conn.commit()
            return True, "Запись обновлена"
        except sqlite3.IntegrityError:
            return False, "Такой силос цемента уже существует"
        finally:
            conn.close()
    
    def delete(self, name):
        """Удалить запись по названию"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM {self.table_name} WHERE name = ?', (name,))
        conn.commit()
        conn.close()
    
    def _parse_number(self, value):
        """Преобразовать значение в число или None"""
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return None


# ============================================================================
# [ИЗМЕНЕНО] CementReceiptsRepository
# ============================================================================


class CementReceiptsRepository:
    """
    Репозиторий для работы с поступлениями цемента.
    [ИЗМЕНЕНО] 
    - Добавлены алиасы для совместимости с другими окнами (get_all, add, update, delete, get_by_id)
    - Методы add/update/delete теперь возвращают кортеж (success, message)
    - Сортировка дат через substr() для корректной работы с форматом ДД.ММ.ГГГГ
    - get_cement_report() теперь возвращает 6 значений с учётом корректировок
    """
    def __init__(self):
        self.table_name = 'cement_receipts'
    
    # ========================================================================
    # [ИЗМЕНЕНО] Корректная сортировка дат через substr()
    # ========================================================================
    def get_all_receipts(self):
        """
        Получить все поступления, отсортированные по дате (убывание).
        [ИЗМЕНЕНО] Используется substr() для корректной сортировки дат в формате ДД.ММ.ГГГГ.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, receipt_date, silo_name, quantity_kg, supplier_name, is_correction
            FROM {self.table_name}
            ORDER BY 
                substr(receipt_date, 7, 4) || '-' || 
                substr(receipt_date, 4, 2) || '-' || 
                substr(receipt_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    # [НОВОЕ] Алиас для совместимости с другими окнами
    def get_all(self):
        """Алиас для get_all_receipts"""
        return self.get_all_receipts()
    
    # ========================================================================
    # [ИЗМЕНЕНО] add_receipt теперь возвращает кортеж (success, message)
    # ========================================================================
    def add_receipt(self, receipt_date, silo_name, quantity_kg, supplier_name=None, is_correction=False):
        """Добавить запись о поступлении"""
        if not receipt_date:
            return False, "Дата не указана"
        if not silo_name:
            return False, "Силос цемента не выбран"
        if quantity_kg is None:
            return False, "Количество не указано"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'''INSERT INTO {self.table_name} 
                    (receipt_date, silo_name, quantity_kg, supplier_name, is_correction) 
                    VALUES (?, ?, ?, ?, ?)''',
                (receipt_date, silo_name, quantity_kg, supplier_name, 1 if is_correction else 0)
            )
            conn.commit()
            return True, "Поступление добавлено"
        except Exception as e:
            return False, f"Ошибка добавления: {e}"
        finally:
            conn.close()
    
    # [НОВОЕ] Алиас для совместимости
    def add(self, *args, **kwargs):
        """Алиас для add_receipt"""
        return self.add_receipt(*args, **kwargs)
    
    # ========================================================================
    # [ИЗМЕНЕНО] update_receipt теперь возвращает кортеж (success, message)
    # ========================================================================
    def update_receipt(self, receipt_id, receipt_date, silo_name, quantity_kg, 
                       supplier_name=None, is_correction=False):
        """Обновить запись о поступлении"""
        if not receipt_date:
            return False, "Дата не указана"
        if not silo_name:
            return False, "Силос цемента не выбран"
        if quantity_kg is None:
            return False, "Количество не указано"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f'''UPDATE {self.table_name} 
                    SET receipt_date = ?, silo_name = ?, quantity_kg = ?, 
                        supplier_name = ?, is_correction = ?
                    WHERE id = ?''',
                (receipt_date, silo_name, quantity_kg, supplier_name, 
                 1 if is_correction else 0, receipt_id)
            )
            conn.commit()
            return True, "Запись обновлена"
        except Exception as e:
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    # [НОВОЕ] Алиас для совместимости
    def update(self, *args, **kwargs):
        """Алиас для update_receipt"""
        return self.update_receipt(*args, **kwargs)
    
    # ========================================================================
    # [ИЗМЕНЕНО] delete_receipt теперь возвращает кортеж (success, message)
    # ========================================================================
    def delete_receipt(self, receipt_id):
        """
        Удалить запись о поступлении.
        [ИЗМЕНЕНО] Теперь возвращает (success, message) и проверяет существование записи.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Проверяем, существует ли запись
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name} WHERE id = ?', (receipt_id,))
            count = cursor.fetchone()[0]
            if count == 0:
                return False, "Запись не найдена"
            
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (receipt_id,))
            conn.commit()
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    # [НОВОЕ] Алиас для совместимости с другими окнами
    def delete(self, *args, **kwargs):
        """Алиас для delete_receipt"""
        return self.delete_receipt(*args, **kwargs)
    
    # ========================================================================
    # Получение записи по ID
    # ========================================================================
    def get_receipt_by_id(self, receipt_id):
        """Получить запись по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, receipt_date, silo_name, quantity_kg, supplier_name, is_correction
            FROM {self.table_name} WHERE id = ?
        ''', (receipt_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    # [НОВОЕ] Алиас для совместимости с другими окнами
    def get_by_id(self, receipt_id):
        """Алиас для get_receipt_by_id"""
        return self.get_receipt_by_id(receipt_id)
    
    # ========================================================================
    # Баланс по силосам
    # ========================================================================
    def get_current_balance_by_silo(self):
        """
        Получить текущий баланс по каждому силосу.
        Баланс = (сумма поступлений) - (сумма расхода на производство)
        """
        conn = get_connection()
        cursor = conn.cursor()
        # Сумма поступлений по силосам
        cursor.execute('''
            SELECT silo_name, SUM(quantity_kg) as total
            FROM cement_receipts
            GROUP BY silo_name
        ''')
        receipts = {row[0]: row[1] for row in cursor.fetchall()}
        # Сумма расхода на производство по силосам
        cursor.execute('''
            SELECT silo_name, SUM(cement_kg) as total
            FROM production
            WHERE silo_name IS NOT NULL AND silo_name != '' 
                  AND cement_kg IS NOT NULL AND cement_kg > 0
            GROUP BY silo_name
        ''')
        production_consumption = {row[0]: row[1] for row in cursor.fetchall()}
        # Рассчитываем баланс
        all_silos = set(receipts.keys()) | set(production_consumption.keys())
        balance = {}
        for silo in all_silos:
            receipt_total = receipts.get(silo, 0) or 0
            consumption_total = production_consumption.get(silo, 0) or 0
            balance[silo] = receipt_total - consumption_total
        conn.close()
        return balance
    
    # ========================================================================
    # [ИЗМЕНЕНО] Полный отчёт по движению цемента (теперь с корректировками)
    # ========================================================================
    def get_cement_report(self):
        """
        Получить полный отчет по движению цемента.
        Объединяет данные из поступлений, расхода на производство и корректировок.
        
        [ИЗМЕНЕНО] Теперь возвращает 6 значений:
        [(date, silo_name, receipt_qty, consumption_qty, correction_qty, balance), ...]
        
        Где:
            - receipt_qty: поступления (is_correction=0)
            - consumption_qty: расход на производство
            - correction_qty: корректировки (is_correction=1)
            - balance: накопительный остаток = receipt - consumption + correction
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 1. Получаем поступления цемента (НЕ корректировки)
            cursor.execute('''
                SELECT receipt_date, silo_name, quantity_kg
                FROM cement_receipts
                WHERE silo_name IS NOT NULL AND silo_name != ''
                  AND (is_correction IS NULL OR is_correction = 0)
            ''')
            receipts = cursor.fetchall()
            
            # 2. Получаем корректировки
            cursor.execute('''
                SELECT receipt_date, silo_name, quantity_kg
                FROM cement_receipts
                WHERE silo_name IS NOT NULL AND silo_name != ''
                  AND is_correction = 1
            ''')
            corrections = cursor.fetchall()
            
            # 3. Получаем расходы на производство
            cursor.execute('''
                SELECT production_date, silo_name, cement_kg
                FROM production
                WHERE silo_name IS NOT NULL AND silo_name != '' 
                      AND cement_kg IS NOT NULL AND cement_kg > 0
            ''')
            consumptions = cursor.fetchall()
            
            # 4. Объединяем в единый список операций
            # Формат: (date, silo, receipt, consumption, correction)
            operations = []
            for date, silo, qty in receipts:
                operations.append((date, silo, qty or 0, 0, 0))
            for date, silo, qty in consumptions:
                operations.append((date, silo, 0, qty or 0, 0))
            for date, silo, qty in corrections:
                operations.append((date, silo, 0, 0, qty or 0))
            
            # 5. Сортируем по дате (возрастание) для правильного расчета остатка
            def date_to_comparable(d):
                try:
                    parts = d.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        return int(f"{year}{month.zfill(2)}{day.zfill(2)}")
                except (ValueError, AttributeError):
                    pass
                return 0
            
            operations.sort(key=lambda x: date_to_comparable(x[0]))
            
            # 6. Рассчитываем накопительный остаток по каждому силосу
            # balance = receipt - consumption + correction
            silo_balances = {}
            result_with_balance = []
            for date, silo, receipt, consumption, correction in operations:
                if silo not in silo_balances:
                    silo_balances[silo] = 0
                silo_balances[silo] = silo_balances[silo] + receipt - consumption + correction
                balance = silo_balances[silo]
                result_with_balance.append((date, silo, receipt, consumption, correction, balance))
            
            # 7. Сортируем по дате (убывание) для отображения
            result_with_balance.sort(key=lambda x: date_to_comparable(x[0]), reverse=True)
            return result_with_balance
        except Exception as e:
            print(f"Ошибка в get_cement_report: {e}")
            return []
        finally:
            conn.close()

        # ========================================================================
    # [НОВОЕ] Месячный отчёт с учётом расхода на производство и корректировок
    # ========================================================================
    def get_monthly_report_with_corrections(self, start_date, end_date):
        """
        Получить месячный отчёт по всем силосам с поступлениями, расходом и корректировками.
        
        Возвращает список кортежей:
            [(sort_key, month_str, silo_name, receipt, consumption, correction), ...]
        
        Где:
            - sort_key: ключ сортировки (ГГГГММ)
            - month_str: название месяца с годом ("Ноябрь 2026")
            - silo_name: название силоса
            - receipt: сумма поступлений за месяц (кг)
            - consumption: сумма расхода на производство за месяц (кг)
            - correction: сумма корректировок за месяц (кг)
        
        Отсортировано по убыванию месяца, затем по названию силоса.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            def to_comparable(date_str):
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}{month.zfill(2)}{day.zfill(2)}"
                return ''
            
            start_cmp = to_comparable(start_date)
            end_cmp = to_comparable(end_date)
            
            # 1. Поступления цемента (не корректировки)
            cursor.execute('''
                SELECT substr(receipt_date, 4, 2) as month_num,
                       substr(receipt_date, 7, 4) as year_num,
                       silo_name,
                       SUM(quantity_kg) as total
                FROM cement_receipts
                WHERE silo_name IS NOT NULL AND silo_name != ''
                  AND (is_correction IS NULL OR is_correction = 0)
                  AND substr(receipt_date, 7, 4) || substr(receipt_date, 4, 2) || substr(receipt_date, 1, 2) 
                      BETWEEN ? AND ?
                GROUP BY month_num, year_num, silo_name
            ''', (start_cmp, end_cmp))
            receipts = {}
            for month_num, year_num, silo, total in cursor.fetchall():
                receipts[(month_num, year_num, silo)] = total or 0
            
            # 2. Расход цемента на производство
            cursor.execute('''
                SELECT substr(production_date, 4, 2) as month_num,
                       substr(production_date, 7, 4) as year_num,
                       silo_name,
                       SUM(cement_kg) as total
                FROM production
                WHERE silo_name IS NOT NULL AND silo_name != ''
                  AND cement_kg IS NOT NULL AND cement_kg > 0
                  AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) 
                      BETWEEN ? AND ?
                GROUP BY month_num, year_num, silo_name
            ''', (start_cmp, end_cmp))
            consumptions = {}
            for month_num, year_num, silo, total in cursor.fetchall():
                consumptions[(month_num, year_num, silo)] = total or 0
            
            # 3. Корректировки
            cursor.execute('''
                SELECT substr(receipt_date, 4, 2) as month_num,
                       substr(receipt_date, 7, 4) as year_num,
                       silo_name,
                       SUM(quantity_kg) as total
                FROM cement_receipts
                WHERE silo_name IS NOT NULL AND silo_name != ''
                  AND is_correction = 1
                  AND substr(receipt_date, 7, 4) || substr(receipt_date, 4, 2) || substr(receipt_date, 1, 2) 
                      BETWEEN ? AND ?
                GROUP BY month_num, year_num, silo_name
            ''', (start_cmp, end_cmp))
            corrections = {}
            for month_num, year_num, silo, total in cursor.fetchall():
                corrections[(month_num, year_num, silo)] = total or 0
            
            # 4. Объединяем все ключи
            all_keys = set(receipts.keys()) | set(consumptions.keys()) | set(corrections.keys())
            
            month_names = {
                '01': 'Январь', '02': 'Февраль', '03': 'Март',
                '04': 'Апрель', '05': 'Май', '06': 'Июнь',
                '07': 'Июль', '08': 'Август', '09': 'Сентябрь',
                '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
            }
            
            result = []
            for month_num, year_num, silo in all_keys:
                month_str = f"{month_names.get(month_num, month_num)} {year_num}"
                sort_key = f"{year_num}{month_num}"
                receipt = receipts.get((month_num, year_num, silo), 0)
                consumption = consumptions.get((month_num, year_num, silo), 0)
                correction = corrections.get((month_num, year_num, silo), 0)
                result.append((sort_key, month_str, silo, receipt, consumption, correction))
            
            # 5. Сортируем: по убыванию месяца, затем по силосу
            result.sort(key=lambda x: (-int(x[0]), x[2].lower()))
            return result
        except Exception as e:
            print(f"Ошибка в get_monthly_report_with_corrections: {e}")
            return []
        finally:
            conn.close()
    
    # ========================================================================
    # [НОВОЕ] Дневной отчёт по конкретному силосу с расходом на производство
    # ========================================================================
    def get_silo_daily_report(self, silo_name, start_date, end_date):
        """
        Получить отчёт по конкретному силосу по дням с расходом на производство.
        
        Возвращает список кортежей:
            [(date, receipt_qty, consumption_qty, is_correction), ...]
        
        Где:
            - date: дата операции (ДД.ММ.ГГГГ)
            - receipt_qty: количество поступления (0 для расхода и корректировок)
            - consumption_qty: количество расхода на производство (0 для поступлений и корректировок)
            - is_correction: 0 — поступление/расход, 1 — корректировка
        
        Отсортировано по дате (возрастание), затем корректировки — ПОСЛЕ обычных операций в тот же день.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            def to_comparable(date_str):
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}{month.zfill(2)}{day.zfill(2)}"
                return ''
            
            start_cmp = to_comparable(start_date)
            end_cmp = to_comparable(end_date)
            
            # 1. Поступления и корректировки из cement_receipts
            cursor.execute('''
                SELECT receipt_date, quantity_kg, is_correction
                FROM cement_receipts
                WHERE silo_name = ?
                  AND substr(receipt_date, 7, 4) || substr(receipt_date, 4, 2) || substr(receipt_date, 1, 2) 
                      BETWEEN ? AND ?
            ''', (silo_name, start_cmp, end_cmp))
            receipts_rows = cursor.fetchall()
            
            # 2. Расход на производство по датам
            cursor.execute('''
                SELECT production_date, SUM(cement_kg) as total
                FROM production
                WHERE silo_name = ?
                  AND cement_kg IS NOT NULL AND cement_kg > 0
                  AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) 
                      BETWEEN ? AND ?
                GROUP BY production_date
            ''', (silo_name, start_cmp, end_cmp))
            consumptions = {row[0]: row[1] or 0 for row in cursor.fetchall()}
            
            # 3. Группируем поступления и корректировки по датам ОТДЕЛЬНО
            receipts_by_date = {}
            corrections_by_date = {}
            for date, qty, is_corr in receipts_rows:
                if is_corr == 1:
                    corrections_by_date[date] = corrections_by_date.get(date, 0) + (qty or 0)
                else:
                    receipts_by_date[date] = receipts_by_date.get(date, 0) + (qty or 0)
            
            # 4. Собираем ВСЕ операции в один список
            # Формат: (date, receipt_qty, consumption_qty, is_correction)
            operations = []
            
            # Обычные операции (поступления + расход)
            all_normal_dates = set(receipts_by_date.keys()) | set(consumptions.keys())
            for date in all_normal_dates:
                receipt = receipts_by_date.get(date, 0)
                consumption = consumptions.get(date, 0)
                operations.append((date, receipt, consumption, 0))
            
            # Корректировки — тоже в общий список
            for date, qty in corrections_by_date.items():
                operations.append((date, qty, 0, 1))
            
            # 5. Сортируем по дате (возрастание), корректировки — ПОСЛЕ обычных в тот же день
            def sort_key(op):
                date, receipt, consumption, is_corr = op
                return (to_comparable(date), is_corr)
            
            operations.sort(key=sort_key)
            
            return operations
        except Exception as e:
            print(f"Ошибка в get_silo_daily_report: {e}")
            return []
        finally:
            conn.close()
    
    # ========================================================================
    # Месячный отчёт по цементу
    # ========================================================================
    def get_cement_monthly_report(self, start_date, end_date, silo_name=None):
        """Получить месячный отчет по цементу за период."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            def to_comparable(date_str):
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}{month.zfill(2)}{day.zfill(2)}"
                return ''
            start_cmp = to_comparable(start_date)
            end_cmp = to_comparable(end_date)
            
            # 1. Поступления по месяцам и силосам
            if silo_name:
                cursor.execute('''
                    SELECT substr(receipt_date, 4, 2) as month_num,
                           substr(receipt_date, 7, 4) as year_num,
                           silo_name,
                           SUM(quantity_kg) as total
                    FROM cement_receipts
                    WHERE silo_name = ?
                      AND substr(receipt_date, 7, 4) || substr(receipt_date, 4, 2) || substr(receipt_date, 1, 2) 
                          BETWEEN ? AND ?
                    GROUP BY month_num, year_num, silo_name
                ''', (silo_name, start_cmp, end_cmp))
            else:
                cursor.execute('''
                    SELECT substr(receipt_date, 4, 2) as month_num,
                           substr(receipt_date, 7, 4) as year_num,
                           silo_name,
                           SUM(quantity_kg) as total
                    FROM cement_receipts
                    WHERE silo_name IS NOT NULL AND silo_name != ''
                      AND substr(receipt_date, 7, 4) || substr(receipt_date, 4, 2) || substr(receipt_date, 1, 2) 
                          BETWEEN ? AND ?
                    GROUP BY month_num, year_num, silo_name
                ''', (start_cmp, end_cmp))
            receipts = {}
            for month_num, year_num, silo, total in cursor.fetchall():
                receipts[(month_num, year_num, silo)] = total or 0
            
            # 2. Расход на производство по месяцам и силосам
            if silo_name:
                cursor.execute('''
                    SELECT substr(production_date, 4, 2) as month_num,
                           substr(production_date, 7, 4) as year_num,
                           silo_name,
                           SUM(cement_kg) as total
                    FROM production
                    WHERE silo_name = ?
                      AND silo_name IS NOT NULL AND silo_name != ''
                      AND cement_kg IS NOT NULL AND cement_kg > 0
                      AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) 
                          BETWEEN ? AND ?
                    GROUP BY month_num, year_num, silo_name
                ''', (silo_name, start_cmp, end_cmp))
            else:
                cursor.execute('''
                    SELECT substr(production_date, 4, 2) as month_num,
                           substr(production_date, 7, 4) as year_num,
                           silo_name,
                           SUM(cement_kg) as total
                    FROM production
                    WHERE silo_name IS NOT NULL AND silo_name != ''
                      AND cement_kg IS NOT NULL AND cement_kg > 0
                      AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) 
                          BETWEEN ? AND ?
                    GROUP BY month_num, year_num, silo_name
                ''', (start_cmp, end_cmp))
            consumptions = {}
            for month_num, year_num, silo, total in cursor.fetchall():
                consumptions[(month_num, year_num, silo)] = total or 0
            
            # 3. Объединяем все ключи
            all_keys = set(receipts.keys()) | set(consumptions.keys())
            
            # 4. Названия месяцев
            month_names = {
                '01': 'Январь', '02': 'Февраль', '03': 'Март',
                '04': 'Апрель', '05': 'Май', '06': 'Июнь',
                '07': 'Июль', '08': 'Август', '09': 'Сентябрь',
                '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
            }
            
            # 5. Формируем итоговый список
            result = []
            for month_num, year_num, silo in all_keys:
                month_str = f"{month_names.get(month_num, month_num)} {year_num}"
                sort_key = f"{year_num}{month_num}"
                receipt_total = receipts.get((month_num, year_num, silo), 0)
                consumption_total = consumptions.get((month_num, year_num, silo), 0)
                adjustment = 0
                result.append((sort_key, month_str, silo, receipt_total, consumption_total, adjustment))
            
            # 6. Сортируем: по убыванию месяца, затем по силосу
            result.sort(key=lambda x: (-int(x[0]), x[2].lower()))
            return result
        except Exception as e:
            print(f"Ошибка в get_cement_monthly_report: {e}")
            return []
        finally:
            conn.close()

class ProductionRepository:
    """Репозиторий для работы с производством продукции"""
    def __init__(self):
        self.table_name = 'production'
    
    def get_all(self):
        """Получить все записи, отсортированные по дате (убывание)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, production_date, equipment_name, silo_name, product_name, 
                   color_name, quantity_pallets, cement_kg, enriched_sand_kg, 
                   river_sand_kg, keramzit_kg, plasticizer_kg, water_kg, note
            FROM {self.table_name}
            ORDER BY 
                substr(production_date, 7, 4) || '-' || 
                substr(production_date, 4, 2) || '-' || 
                substr(production_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_daily_cement_totals(self):
        """Получить суммарный расход цемента по датам"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT production_date, SUM(cement_kg) as total
            FROM {self.table_name}
            GROUP BY production_date
        ''')
        result = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return result
    
    def get_by_id(self, production_id):
        """Получить запись по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, production_date, equipment_name, silo_name, product_name, 
                   color_name, quantity_pallets, cement_kg, enriched_sand_kg, 
                   river_sand_kg, keramzit_kg, plasticizer_kg, water_kg, note
            FROM {self.table_name} WHERE id = ?
        ''', (production_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_cement_consumption_by_date(self, date_str):
        """Получить расход цемента по силосам за конкретную дату."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT silo_name, SUM(cement_kg) as total
            FROM {self.table_name}
            WHERE production_date = ? 
                  AND silo_name IS NOT NULL AND silo_name != ''
                  AND cement_kg IS NOT NULL AND cement_kg > 0
            GROUP BY silo_name
            ORDER BY silo_name COLLATE NOCASE
        ''', (date_str,))
        result = cursor.fetchall()
        conn.close()
        return result
    
    def update_cement_consumption_by_date(self, date_str, silo_consumption):
        """Обновить расход цемента по силосам за конкретную дату."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT id, silo_name, cement_kg
                FROM {self.table_name}
                WHERE production_date = ?
            ''', (date_str,))
            records = cursor.fetchall()
            silo_records = {}
            for record_id, silo_name, cement_kg in records:
                if silo_name not in silo_records:
                    silo_records[silo_name] = []
                silo_records[silo_name].append((record_id, cement_kg))
            
            for silo_name, new_cement_kg in silo_consumption.items():
                new_value = self._parse_number(new_cement_kg)
                if new_value is None:
                    new_value = 0
                if silo_name in silo_records:
                    records_for_silo = silo_records[silo_name]
                    if len(records_for_silo) == 1:
                        cursor.execute(f'''
                            UPDATE {self.table_name}
                            SET cement_kg = ?
                            WHERE id = ?
                        ''', (new_value, records_for_silo[0][0]))
                    else:
                        cursor.execute(f'''
                            UPDATE {self.table_name}
                            SET cement_kg = ?
                            WHERE id = ?
                        ''', (new_value, records_for_silo[0][0]))
                        for i in range(1, len(records_for_silo)):
                            cursor.execute(f'''
                                UPDATE {self.table_name}
                                SET cement_kg = 0
                                WHERE id = ?
                            ''', (records_for_silo[i][0],))
                else:
                    cursor.execute(f'''
                        INSERT INTO {self.table_name}
                        (production_date, silo_name, cement_kg)
                        VALUES (?, ?, ?)
                    ''', (date_str, silo_name, new_value))
            
            for silo_name in silo_records:
                if silo_name not in silo_consumption:
                    for record_id, _ in silo_records[silo_name]:
                        cursor.execute(f'''
                            UPDATE {self.table_name}
                            SET cement_kg = 0
                            WHERE id = ?
                        ''', (record_id,))
            conn.commit()
            return True, "Расход цемента обновлён"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    def add(self, production_date, equipment_name, silo_name, product_name, 
            color_name, quantity_pallets, cement_kg, enriched_sand_kg, 
            river_sand_kg, keramzit_kg, plasticizer_kg, water_kg, note):
        """Добавить запись о производстве"""
        if not production_date:
            return False, "Дата не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (production_date, equipment_name, silo_name, product_name, color_name,
                 quantity_pallets, cement_kg, enriched_sand_kg, river_sand_kg,
                 keramzit_kg, plasticizer_kg, water_kg, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (production_date, equipment_name, silo_name, product_name, color_name,
                  self._parse_number(quantity_pallets),
                  self._parse_number(cement_kg),
                  self._parse_number(enriched_sand_kg),
                  self._parse_number(river_sand_kg),
                  self._parse_number(keramzit_kg),
                  self._parse_number(plasticizer_kg),
                  self._parse_number(water_kg),
                  note))
            conn.commit()
            return True, "Запись о производстве добавлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка добавления: {e}"
        finally:
            conn.close()
    
    def update(self, production_id, production_date, equipment_name, silo_name,
               product_name, color_name, quantity_pallets, cement_kg,
               enriched_sand_kg, river_sand_kg, keramzit_kg, plasticizer_kg,
               water_kg, note):
        """Обновить запись о производстве"""
        if not production_date:
            return False, "Дата не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE {self.table_name}
                SET production_date = ?, equipment_name = ?, silo_name = ?,
                    product_name = ?, color_name = ?, quantity_pallets = ?,
                    cement_kg = ?, enriched_sand_kg = ?, river_sand_kg = ?,
                    keramzit_kg = ?, plasticizer_kg = ?, water_kg = ?, note = ?
                WHERE id = ?
            ''', (production_date, equipment_name, silo_name, product_name, color_name,
                  self._parse_number(quantity_pallets),
                  self._parse_number(cement_kg),
                  self._parse_number(enriched_sand_kg),
                  self._parse_number(river_sand_kg),
                  self._parse_number(keramzit_kg),
                  self._parse_number(plasticizer_kg),
                  self._parse_number(water_kg),
                  note, production_id))
            conn.commit()
            return True, "Запись обновлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    def delete(self, production_id):
        """Удалить запись о производстве"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (production_id,))
            conn.commit()
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    def delete_by_date(self, date_str):
        """Удалить все записи за конкретную дату."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT COUNT(*) FROM {self.table_name}
                WHERE production_date = ?
            ''', (date_str,))
            count = cursor.fetchone()[0]
            if count == 0:
                return False, "Записей за этот день не найдено"
            cursor.execute(f'''
                DELETE FROM {self.table_name}
                WHERE production_date = ?
            ''', (date_str,))
            conn.commit()
            return True, f"Удалено записей за {date_str}: {count}"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    def get_production_report(self, start_date=None, end_date=None, equipment=None, product=None):
        """Получить данные для отчета по производству продукции."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = f'''
                SELECT id, production_date, equipment_name, product_name, color_name, quantity_pallets
                FROM {self.table_name}
                WHERE product_name IS NOT NULL AND product_name != ''
            '''
            params = []
            if start_date:
                try:
                    parts = start_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        start_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) >= ?
                        '''
                        params.append(start_cmp)
                except:
                    pass
            if end_date:
                try:
                    parts = end_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        end_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) <= ?
                        '''
                        params.append(end_cmp)
                except:
                    pass
            if equipment:
                query += ' AND equipment_name = ?'
                params.append(equipment)
            if product:
                query += ' AND product_name = ?'
                params.append(product)
            query += '''
                ORDER BY 
                    substr(production_date, 7, 4) || '-' || 
                    substr(production_date, 4, 2) || '-' || 
                    substr(production_date, 1, 2) DESC,
                    id DESC
            '''
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Ошибка в get_production_report: {e}")
            return []
        finally:
            conn.close()
    
    def get_inert_materials_report(self, start_date=None, end_date=None, equipment=None, product=None):
        """Получить данные для отчета по расходу инертных материалов."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = f'''
                SELECT id, production_date, equipment_name, product_name, color_name,
                       quantity_pallets, cement_kg, enriched_sand_kg,
                       river_sand_kg, keramzit_kg, plasticizer_kg, water_kg
                FROM {self.table_name}
                WHERE product_name IS NOT NULL AND product_name != ''
            '''
            params = []
            if start_date:
                try:
                    parts = start_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        start_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) >= ?
                        '''
                        params.append(start_cmp)
                except:
                    pass
            if end_date:
                try:
                    parts = end_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        end_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(production_date, 7, 4) || substr(production_date, 4, 2) || substr(production_date, 1, 2) <= ?
                        '''
                        params.append(end_cmp)
                except:
                    pass
            if equipment:
                query += ' AND equipment_name = ?'
                params.append(equipment)
            if product:
                query += ' AND product_name = ?'
                params.append(product)
            query += '''
                ORDER BY 
                    substr(production_date, 7, 4) || '-' || 
                    substr(production_date, 4, 2) || '-' || 
                    substr(production_date, 1, 2) DESC,
                    equipment_name, product_name
            '''
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.execute('SELECT name, volume_per_pallet FROM products')
            volume_map = {row[0]: (row[1] if row[1] else 1) for row in cursor.fetchall()}
            grouped = {}
            for row in rows:
                (prod_id, date, equip_name, prod_name, color_name,
                 quantity_pallets, cement, enriched_sand, river_sand,
                 keramzit, plasticizer, water) = row
                volume = volume_map.get(prod_name, 1)
                calc_qty = (quantity_pallets or 0) * volume
                key = (date, equip_name or '', prod_name)
                if key not in grouped:
                    grouped[key] = {
                        'date': date, 'equipment': equip_name or '',
                        'product': prod_name, 'quantity': 0,
                        'cement': 0, 'enriched_sand': 0, 'river_sand': 0,
                        'keramzit': 0, 'plasticizer': 0, 'water': 0
                    }
                grouped[key]['quantity'] += calc_qty
                grouped[key]['cement'] += cement or 0
                grouped[key]['enriched_sand'] += enriched_sand or 0
                grouped[key]['river_sand'] += river_sand or 0
                grouped[key]['keramzit'] += keramzit or 0
                grouped[key]['plasticizer'] += plasticizer or 0
                grouped[key]['water'] += water or 0
            result = []
            for key, data in grouped.items():
                qty = data['quantity']
                if qty > 0:
                    result.append({
                        'date': data['date'], 'equipment': data['equipment'],
                        'product': data['product'], 'quantity': qty,
                        'cement_per_unit': data['cement'] / qty,
                        'enriched_sand_per_unit': data['enriched_sand'] / qty,
                        'plasticizer_per_unit': data['plasticizer'] / qty,
                        'river_sand_per_unit': data['river_sand'] / qty,
                        'keramzit_per_unit': data['keramzit'] / qty,
                        'water_per_unit': data['water'] / qty
                    })
            def sort_key(item):
                try:
                    parts = item['date'].split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        date_num = int(f"{year}{month.zfill(2)}{day.zfill(2)}")
                    else:
                        date_num = 0
                except:
                    date_num = 0
                return (-date_num, item['product'].lower())
            result.sort(key=sort_key)
            return result
        except Exception as e:
            print(f"Ошибка в get_inert_materials_report: {e}")
            return []
        finally:
            conn.close()
    
    def get_inert_materials_summary(self, start_date=None, end_date=None):
        """Получить сводные данные для отчета по расходу инертных материалов."""
        detailed = self.get_inert_materials_report(start_date, end_date)
        if not detailed:
            return []
        by_product = {}
        for item in detailed:
            prod = item['product']
            if prod not in by_product:
                by_product[prod] = {
                    'quantities': [], 'cements': [], 'enriched_sands': [],
                    'plasticizers': [], 'river_sands': [], 'keramzits': [], 'waters': []
                }
            by_product[prod]['quantities'].append(item['quantity'])
            by_product[prod]['cements'].append(item['cement_per_unit'])
            by_product[prod]['enriched_sands'].append(item['enriched_sand_per_unit'])
            by_product[prod]['plasticizers'].append(item['plasticizer_per_unit'])
            by_product[prod]['river_sands'].append(item['river_sand_per_unit'])
            by_product[prod]['keramzits'].append(item['keramzit_per_unit'])
            by_product[prod]['waters'].append(item['water_per_unit'])
        result = []
        for prod, data in by_product.items():
            count = len(data['quantities'])
            def avg(lst):
                return sum(lst) / len(lst) if lst else 0
            result.append({
                'product': prod,
                'avg_quantity': avg(data['quantities']),
                'avg_cement': avg(data['cements']),
                'avg_enriched_sand': avg(data['enriched_sands']),
                'avg_plasticizer': avg(data['plasticizers']),
                'avg_river_sand': avg(data['river_sands']),
                'avg_keramzit': avg(data['keramzits']),
                'avg_water': avg(data['waters']),
                'count': count
            })
        result.sort(key=lambda x: x['product'].lower())
        return result
    
    def _parse_number(self, value):
        """Преобразовать значение в число или None"""
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return None


class WarehouseRepository:
    """Репозиторий для работы со складом (остатками продукции)"""
    def __init__(self):
        self.table_name = 'warehouse'
    
    def get_all(self):
        """Получить все остатки на складе."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT product_name, color_name, stock_qty, reserved_qty, 
                   (stock_qty - reserved_qty) as remaining_qty
            FROM {self.table_name}
            ORDER BY product_name COLLATE NOCASE, color_name COLLATE NOCASE
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def set_stock(self, product_name, color_name, new_qty, qty_before):
        """Устанавливает новое количество на складе."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT id FROM {self.table_name} 
                WHERE product_name = ? AND color_name = ?
            ''', (product_name, color_name))
            row = cursor.fetchone()
            new_qty = float(new_qty) if new_qty else 0.0
            difference = new_qty - qty_before
            if row:
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET stock_qty = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_name = ? AND color_name = ?
                ''', (new_qty, product_name, color_name))
            else:
                cursor.execute(f'''
                    INSERT INTO {self.table_name} (product_name, color_name, stock_qty, reserved_qty)
                    VALUES (?, ?, ?, 0)
                ''', (product_name, color_name, new_qty))
            conn.commit()
            return True, qty_before, difference
        except Exception as e:
            conn.rollback()
            return False, 0.0, str(e)
        finally:
            conn.close()
    
    def add_or_update_stock(self, product_name, color_name, quantity):
        """Добавить или обновить остаток на складе."""
        if not product_name or not color_name:
            return False, "Продукция и цвет обязательны"
        qty = self._parse_number(quantity)
        if qty is None:
            return False, "Некорректное количество"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT id, stock_qty FROM {self.table_name}
                WHERE product_name = ? AND color_name = ?
            ''', (product_name, color_name))
            row = cursor.fetchone()
            if row:
                record_id, current_stock = row
                new_stock = (current_stock or 0) + qty
                if new_stock < 0:
                    new_stock = 0
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET stock_qty = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_stock, record_id))
            else:
                if qty > 0:
                    cursor.execute(f'''
                        INSERT INTO {self.table_name} (product_name, color_name, stock_qty)
                        VALUES (?, ?, ?)
                    ''', (product_name, color_name, qty))
            conn.commit()
            return True, "Склад обновлён"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления склада: {e}"
        finally:
            conn.close()
    
    def set_reserved(self, product_name, color_name, reserved_qty):
        """Установить зарезервированное количество."""
        if not product_name or not color_name:
            return False, "Продукция и цвет обязательны"
        qty = self._parse_number(reserved_qty)
        if qty is None:
            return False, "Некорректное количество резерва"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT id, stock_qty FROM {self.table_name}
                WHERE product_name = ? AND color_name = ?
            ''', (product_name, color_name))
            row = cursor.fetchone()
            if row:
                record_id, current_stock = row
                max_reserve = current_stock or 0
                if qty > max_reserve:
                    qty = max_reserve
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET reserved_qty = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (qty, record_id))
                conn.commit()
                return True, "Резерв обновлён"
            else:
                return False, "Запись на складе не найдена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления резерва: {e}"
        finally:
            conn.close()
    
    def delete_entry(self, product_name, color_name):
        """Удалить запись со склада"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            DELETE FROM {self.table_name}
            WHERE product_name = ? AND color_name = ?
        ''', (product_name, color_name))
        conn.commit()
        conn.close()
    
    def _parse_number(self, value):
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return None


# ============================================================================
# [ИЗМЕНЕНО] ReservedProductsRepository — добавлены алиасы, метод update(),
# новая таблица reserve_realizations для связи резерв → реализация
# ============================================================================
class ReservedProductsRepository:
    """Репозиторий для работы с продукцией в резерве и её реализацией"""
    def __init__(self):
        self.table_name = 'reserved_products'
        self.sold_table_name = 'sold_from_reserve'
        # [НОВОЕ] Таблица связей резерв → реализация
        self.realization_table_name = 'reserve_realizations'
        self._realization_table_ready = False
    
    # ========================================================================
    # [НОВОЕ] ЛЕНИВОЕ СОЗДАНИЕ ТАБЛИЦЫ РЕАЛИЗАЦИЙ
    # ========================================================================
    def _ensure_realization_table(self):
        """Создать таблицу реализаций, если её ещё нет (миграция на лету)"""
        if self._realization_table_ready:
            return
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.realization_table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reserve_id INTEGER NOT NULL,
                    sale_date TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    sale_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute(f'''
                CREATE INDEX IF NOT EXISTS idx_reserve_realizations_reserve
                ON {self.realization_table_name}(reserve_id)
            ''')
            conn.commit()
            self._realization_table_ready = True
        except Exception as e:
            print(f"Ошибка создания таблицы реализаций: {e}")
        finally:
            conn.close()
    
    # ========================================================================
    # РЕЗЕРВЫ
    # ========================================================================
    def get_all_reserved(self):
        """Получить все записи о резервах, отсортированные по дате начала (убывание)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, start_date, end_date, product_name, color_name, quantity, customer_name
            FROM {self.table_name}
            ORDER BY 
                substr(start_date, 7, 4) || '-' || 
                substr(start_date, 4, 2) || '-' || 
                substr(start_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    # [НОВОЕ] Алиас для совместимости с другими окнами
    def get_all(self):
        """Алиас для get_all_reserved"""
        return self.get_all_reserved()
    
    def get_all_sold(self):
        """Получить все записи о реализованной продукции (старый механизм)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, start_date, end_date, sale_date, product_name, color_name, quantity, customer_name
            FROM {self.sold_table_name}
            ORDER BY 
                substr(sale_date, 7, 4) || '-' || 
                substr(sale_date, 4, 2) || '-' || 
                substr(sale_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_sold_sum(self):
        """Получить сумму всех проданных товаров (старый механизм)"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM {self.sold_table_name}
                GROUP BY product_name, color_name
            ''')
            result = {}
            for product, color, qty in cursor.fetchall():
                key = (product.strip() if product else '', color.strip() if color else '')
                result[key] = qty or 0
            return result
        except Exception:
            return {}
        finally:
            conn.close()
    
    def get_reserved_by_id(self, reserve_id):
        """Получить запись о резерве по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, start_date, end_date, product_name, color_name, quantity, customer_name
            FROM {self.table_name} WHERE id = ?
        ''', (reserve_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    # [НОВОЕ] Алиас для совместимости
    def get_by_id(self, reserve_id):
        """Алиас для get_reserved_by_id"""
        return self.get_reserved_by_id(reserve_id)
    
    def add_reserved(self, start_date, end_date, product_name, color_name, quantity, customer_name):
        """Добавить запись о резерве"""
        if not start_date:
            return False, "Дата начала резерва не указана"
        if not end_date:
            return False, "Дата конца резерва не указана"
        if not product_name:
            return False, "Продукция не выбрана"
        if quantity is None:
            return False, "Количество не указано"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (start_date, end_date, product_name, color_name, quantity, customer_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (start_date, end_date, product_name, color_name, quantity, customer_name))
            conn.commit()
            return True, "Резерв добавлен"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка добавления: {e}"
        finally:
            conn.close()
    
    # [НОВОЕ] Алиас для совместимости
    def add(self, *args, **kwargs):
        """Алиас для add_reserved"""
        return self.add_reserved(*args, **kwargs)
    
    # [НОВОЕ] Метод update для резервов (ранее отсутствовал!)
    def update(self, reserve_id, start_date, end_date, product_name, color_name, quantity, customer_name):
        """Обновить запись о резерве"""
        if not start_date:
            return False, "Дата начала резерва не указана"
        if not end_date:
            return False, "Дата конца резерва не указана"
        if not product_name:
            return False, "Продукция не выбрана"
        if quantity is None:
            return False, "Количество не указано"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE {self.table_name}
                SET start_date = ?, end_date = ?, product_name = ?,
                    color_name = ?, quantity = ?, customer_name = ?
                WHERE id = ?
            ''', (start_date, end_date, product_name, color_name, quantity, customer_name, reserve_id))
            conn.commit()
            return True, "Резерв обновлён"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    # [ИЗМЕНЕНО] Теперь возвращает кортеж (success, message)
    def delete_reserved(self, reserve_id):
        """Удалить запись о резерве вместе с её реализациями"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name} WHERE id = ?', (reserve_id,))
            if cursor.fetchone()[0] == 0:
                return False, "Запись не найдена"
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (reserve_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
        # [НОВОЕ] Чистим связи реализаций (сами продажи в журнале остаются)
        self.delete_realizations(reserve_id)
        return True, "Запись удалена"
    
    # [НОВОЕ] Алиас для совместимости
    def delete(self, *args, **kwargs):
        """Алиас для delete_reserved"""
        return self.delete_reserved(*args, **kwargs)
    
    # ========================================================================
    # [НОВОЕ] РЕАЛИЗАЦИИ РЕЗЕРВА
    # ========================================================================
    def get_realizations_map(self):
        """
        Получить все реализации по всем резервам.
        Returns:
            {reserve_id: [(sale_date, quantity), ...], ...}
            Список отсортирован по дате возрастания, затем по id.
        """
        self._ensure_realization_table()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT reserve_id, sale_date, quantity
                FROM {self.realization_table_name}
                ORDER BY 
                    substr(sale_date, 7, 4) || '-' || 
                    substr(sale_date, 4, 2) || '-' || 
                    substr(sale_date, 1, 2) ASC,
                    id ASC
            ''')
            result = {}
            for reserve_id, sale_date, quantity in cursor.fetchall():
                result.setdefault(reserve_id, []).append((sale_date, quantity or 0))
            return result
        except Exception as e:
            print(f"Ошибка получения реализаций: {e}")
            return {}
        finally:
            conn.close()
    
    def get_realized_total(self, reserve_id):
        """Получить суммарное реализованное количество по резерву"""
        self._ensure_realization_table()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT SUM(quantity) FROM {self.realization_table_name}
                WHERE reserve_id = ?
            ''', (reserve_id,))
            row = cursor.fetchone()
            return row[0] or 0 if row else 0
        except Exception:
            return 0
        finally:
            conn.close()
    
    def add_realization(self, reserve_id, sale_date, quantity, sale_id=None):
        """Записать факт реализации части (или всего) резерва"""
        self._ensure_realization_table()
        if not sale_date:
            return False, "Дата реализации не указана"
        if quantity is None:
            return False, "Количество не указано"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.realization_table_name}
                (reserve_id, sale_date, quantity, sale_id)
                VALUES (?, ?, ?, ?)
            ''', (reserve_id, sale_date, quantity, sale_id))
            conn.commit()
            return True, "Реализация записана"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка записи реализации: {e}"
        finally:
            conn.close()
    
    def delete_realizations(self, reserve_id):
        """Удалить все связи реализаций для резерва"""
        self._ensure_realization_table()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                DELETE FROM {self.realization_table_name} WHERE reserve_id = ?
            ''', (reserve_id,))
            conn.commit()
            return True, "Реализации удалены"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления реализаций: {e}"
        finally:
            conn.close()
    
    # ========================================================================
    # СТАРЫЙ МЕХАНИЗМ (sold_from_reserve) — сохранён для совместимости
    # ========================================================================
    def delete_sold(self, sold_id):
        """Удалить запись о реализованной продукции (старый механизм)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM {self.sold_table_name} WHERE id = ?', (sold_id,))
        conn.commit()
        conn.close()
    
    def move_to_sold(self, reserve_id, sale_date):
        """Переместить запись из резерва в реализованную продукцию (старый механизм)"""
        if not sale_date:
            return False, "Дата продажи не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT start_date, end_date, product_name, color_name, quantity, customer_name
                FROM {self.table_name} WHERE id = ?
            ''', (reserve_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Запись о резерве не найдена"
            start_date, end_date, product_name, color_name, quantity, customer_name = row
            cursor.execute(f'''
                INSERT INTO {self.sold_table_name}
                (start_date, end_date, sale_date, product_name, color_name, quantity, customer_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (start_date, end_date, sale_date, product_name, color_name, quantity, customer_name))
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (reserve_id,))
            conn.commit()
            return True, "Продукция реализована"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка реализации: {e}"
        finally:
            conn.close()


class AdjustmentRepository:
    """Репозиторий для истории корректировок остатков"""
    def __init__(self):
        self.table_name = 'adjustments'
    
    def log_adjustment(self, date_str, product_name, color_name, qty_before, qty_after, difference):
        """Записать корректировку в историю."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (adjustment_date, product_name, color_name, qty_before, qty_after, difference)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date_str, product_name, color_name, qty_before, qty_after, difference))
            conn.commit()
            return True, "Корректировка сохранена"
        except Exception as e:
            return False, f"Ошибка сохранения: {e}"
        finally:
            conn.close()
    
    def get_adjustments_sum(self):
        """Получить сумму всех корректировок"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT product_name, color_name, SUM(difference) as total
                FROM {self.table_name}
                GROUP BY product_name, color_name
            ''')
            result = {}
            for product, color, diff in cursor.fetchall():
                key = (product.strip() if product else '', color.strip() if color else '')
                result[key] = diff or 0
            return result
        except Exception:
            return {}
        finally:
            conn.close()


# ============================================================================
# [ИЗМЕНЕНО] SalesRepository — добавлен метод add_with_id()
# ============================================================================
class SalesRepository:
    """Репозиторий для работы с реализацией продукции"""
    def __init__(self):
        self.table_name = 'sales'
    
    def get_all(self):
        """Получить все продажи, отсортированные по дате (убывание)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, sale_date, product_name, color_name, quantity, price, equipment_name
            FROM {self.table_name}
            ORDER BY 
                substr(sale_date, 7, 4) || '-' || 
                substr(sale_date, 4, 2) || '-' || 
                substr(sale_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_by_id(self, sale_id):
        """Получить запись по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, sale_date, product_name, color_name, quantity, price, equipment_name
            FROM {self.table_name} WHERE id = ?
        ''', (sale_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    # [НОВОЕ] Добавление с возвратом ID записи
    def add_with_id(self, sale_date, product_name, color_name, quantity, price, equipment_name=None):
        """
        Добавить запись о продаже.
        Returns:
            (success, message, sale_id)  — sale_id = None при ошибке
        """
        if not sale_date:
            return False, "Дата не указана", None
        if not product_name:
            return False, "Продукция не выбрана", None
        if quantity is None:
            return False, "Количество не указано", None
        if price is None:
            return False, "Цена не указана", None
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (sale_date, product_name, color_name, quantity, price, equipment_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sale_date, product_name, color_name, quantity, price, equipment_name))
            conn.commit()
            return True, "Продажа добавлена", cursor.lastrowid
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка добавления: {e}", None
        finally:
            conn.close()
    
    def add(self, sale_date, product_name, color_name, quantity, price, equipment_name=None):
        """Добавить запись о продаже (совместимый интерфейс)"""
        success, message, _ = self.add_with_id(
            sale_date, product_name, color_name, quantity, price, equipment_name
        )
        return success, message
    
    def update(self, sale_id, sale_date, product_name, color_name, quantity, price, equipment_name=None):
        """Обновить запись о продаже"""
        if not sale_date:
            return False, "Дата не указана"
        if not product_name:
            return False, "Продукция не выбрана"
        if quantity is None:
            return False, "Количество не указано"
        if price is None:
            return False, "Цена не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE {self.table_name}
                SET sale_date = ?, product_name = ?, color_name = ?, quantity = ?, price = ?, equipment_name = ?
                WHERE id = ?
            ''', (sale_date, product_name, color_name, quantity, price, equipment_name, sale_id))
            conn.commit()
            return True, "Запись обновлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    def delete(self, sale_id):
        """Удалить запись о продаже"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (sale_id,))
            conn.commit()
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    def get_sales_sum(self):
        """Получить сумму всех прямых продаж по (продукция, цвет)"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM {self.table_name}
                GROUP BY product_name, color_name
            ''')
            result = {}
            for product, color, qty in cursor.fetchall():
                key = (product.strip() if product else '', color.strip() if color else '')
                result[key] = qty or 0
            return result
        except Exception:
            return {}
        finally:
            conn.close()
    
    def get_sales_report(self, start_date=None, end_date=None, equipment=None, product=None):
        """Получить данные для отчета по реализации."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = f'''
                SELECT id, sale_date, product_name, color_name, quantity, price, equipment_name
                FROM {self.table_name}
                WHERE 1=1
            '''
            params = []
            if start_date:
                try:
                    parts = start_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        start_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(sale_date, 7, 4) || substr(sale_date, 4, 2) || substr(sale_date, 1, 2) >= ?
                        '''
                        params.append(start_cmp)
                except:
                    pass
            if end_date:
                try:
                    parts = end_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        end_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(sale_date, 7, 4) || substr(sale_date, 4, 2) || substr(sale_date, 1, 2) <= ?
                        '''
                        params.append(end_cmp)
                except:
                    pass
            if equipment:
                query += ' AND equipment_name = ?'
                params.append(equipment)
            if product:
                query += ' AND product_name = ?'
                params.append(product)
            query += '''
                ORDER BY 
                    substr(sale_date, 7, 4) || '-' || 
                    substr(sale_date, 4, 2) || '-' || 
                    substr(sale_date, 1, 2) DESC,
                    id DESC
            '''
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Ошибка в get_sales_report: {e}")
            return []
        finally:
            conn.close()


class CashRepository:
    """Репозиторий для работы с кассовыми операциями"""
    def __init__(self):
        self.table_name = 'cash_operations'
    
    def get_all(self):
        """Получить все операции, отсортированные по дате (убывание)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, operation_date, income, expense
            FROM {self.table_name}
            ORDER BY 
                substr(operation_date, 7, 4) || '-' || 
                substr(operation_date, 4, 2) || '-' || 
                substr(operation_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_by_id(self, operation_id):
        """Получить запись по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, operation_date, income, expense
            FROM {self.table_name} WHERE id = ?
        ''', (operation_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def add(self, operation_date, income, expense):
        """Добавить кассовую операцию"""
        if not operation_date:
            return False, "Дата не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (operation_date, income, expense)
                VALUES (?, ?, ?)
            ''', (operation_date, income or 0, expense or 0))
            conn.commit()
            return True, "Операция добавлена"
        except Exception as e:
            return False, f"Ошибка добавления: {e}"
        finally:
            conn.close()
    
    def delete(self, operation_id):
        """Удалить кассовую операцию"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (operation_id,))
            conn.commit()
            return True, "Операция удалена"
        except Exception as e:
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    def clear_field(self, operation_id, field):
        """Обнулить конкретное поле (income или expense) в записи."""
        if field not in ('income', 'expense'):
            return False, "Некорректное имя поля"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT income, expense FROM {self.table_name} WHERE id = ?
            ''', (operation_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Запись не найдена"
            current_income, current_expense = row
            if field == 'income':
                new_income = 0
                new_expense = current_expense or 0
            else:
                new_income = current_income or 0
                new_expense = 0
            if new_income == 0 and new_expense == 0:
                cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (operation_id,))
                conn.commit()
                return True, "Запись удалена (оба значения были обнулены)"
            else:
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET income = ?, expense = ?
                    WHERE id = ?
                ''', (new_income, new_expense, operation_id))
                conn.commit()
                field_name = "приход" if field == 'income' else "расход"
                return True, f"Значение '{field_name}' обнулено"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    def get_daily_totals(self):
        """Получить итоги по дням."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT operation_date, 
                   SUM(income) as total_income, 
                   SUM(expense) as total_expense
            FROM {self.table_name}
            GROUP BY operation_date
        ''')
        result = {}
        for date, income, expense in cursor.fetchall():
            result[date] = {
                'income': income or 0,
                'expense': expense or 0
            }
        conn.close()
        return result
    
    def get_balance_up_to_date(self, target_date):
        """Получить накопленный остаток на указанную дату включительно."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            parts = target_date.split('.')
            if len(parts) == 3:
                day, month, year = parts
                comparable = f"{year}{month.zfill(2)}{day.zfill(2)}"
            else:
                conn.close()
                return 0
        except (ValueError, AttributeError):
            conn.close()
            return 0
        cursor.execute(f'''
            SELECT 
                SUM(income) - SUM(expense) as balance
            FROM {self.table_name}
            WHERE substr(operation_date, 7, 4) || '-' || 
                  substr(operation_date, 4, 2) || '-' || 
                  substr(operation_date, 1, 2) <= ?
        ''', (comparable,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0] is not None:
            return row[0]
        return 0


class GeneralExpensesRepository:
    """Репозиторий для работы с общими расходами"""
    def __init__(self):
        self.table_name = 'general_expenses'
    
    def get_all(self):
        """Получить все записи, отсортированные по дате (убывание)"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, expense_date, supplier_name, material_name, quantity, price,
                   payer_name, payment_type_name, purpose_name, comment
            FROM {self.table_name}
            ORDER BY 
                substr(expense_date, 7, 4) || '-' || 
                substr(expense_date, 4, 2) || '-' || 
                substr(expense_date, 1, 2) DESC,
                id DESC
        ''')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_by_id(self, expense_id):
        """Получить запись по ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, expense_date, supplier_name, material_name, quantity, price,
                   payer_name, payment_type_name, purpose_name, comment
            FROM {self.table_name} WHERE id = ?
        ''', (expense_id,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def add(self, expense_date, supplier_name, material_name, quantity, price,
            payer_name, payment_type_name, purpose_name, comment):
        """Добавить запись о расходе"""
        if not expense_date:
            return False, "Дата не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (expense_date, supplier_name, material_name, quantity, price,
                 payer_name, payment_type_name, purpose_name, comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (expense_date, supplier_name, material_name,
                  self._parse_number(quantity),
                  self._parse_number(price),
                  payer_name, payment_type_name, purpose_name, comment))
            conn.commit()
            return True, "Запись о расходе добавлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка добавления: {e}"
        finally:
            conn.close()
    
    def update(self, expense_id, expense_date, supplier_name, material_name,
               quantity, price, payer_name, payment_type_name, purpose_name, comment):
        """Обновить запись о расходе"""
        if not expense_date:
            return False, "Дата не указана"
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                UPDATE {self.table_name}
                SET expense_date = ?, supplier_name = ?, material_name = ?,
                    quantity = ?, price = ?, payer_name = ?,
                    payment_type_name = ?, purpose_name = ?, comment = ?
                WHERE id = ?
            ''', (expense_date, supplier_name, material_name,
                  self._parse_number(quantity),
                  self._parse_number(price),
                  payer_name, payment_type_name, purpose_name, comment,
                  expense_id))
            conn.commit()
            return True, "Запись обновлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            conn.close()
    
    def delete(self, expense_id):
        """Удалить запись о расходе"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (expense_id,))
            conn.commit()
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    def _parse_number(self, value):
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def get_expenses_report(self, start_date=None, end_date=None, filters=None):
        """Получить данные для отчета по расходам."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = f'''
                SELECT id, expense_date, supplier_name, material_name, quantity, price,
                       payer_name, payment_type_name, purpose_name, comment
                FROM {self.table_name}
                WHERE 1=1
            '''
            params = []
            if start_date:
                try:
                    parts = start_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        start_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(expense_date, 7, 4) || substr(expense_date, 4, 2) || substr(expense_date, 1, 2) >= ?
                        '''
                        params.append(start_cmp)
                except:
                    pass
            if end_date:
                try:
                    parts = end_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        end_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(expense_date, 7, 4) || substr(expense_date, 4, 2) || substr(expense_date, 1, 2) <= ?
                        '''
                        params.append(end_cmp)
                except:
                    pass
            if filters:
                field_mapping = {
                    'supplier': 'supplier_name',
                    'payer': 'payer_name',
                    'payment_type': 'payment_type_name',
                    'purpose': 'purpose_name',
                    'material': 'material_name',
                }
                for field_name, value in filters.items():
                    if value and field_name in field_mapping:
                        db_field = field_mapping[field_name]
                        query += f' AND {db_field} = ?'
                        params.append(value)
            query += '''
                ORDER BY 
                    substr(expense_date, 7, 4) || '-' || 
                    substr(expense_date, 4, 2) || '-' || 
                    substr(expense_date, 1, 2) DESC,
                    id DESC
            '''
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            print(f"Ошибка в get_expenses_report: {e}")
            return []
        finally:
            conn.close()


# ============================================================================
# Экземпляры репозиториев
# ============================================================================
payment_types_repo = DictionaryRepository('payment_types')
materials_repo = DictionaryRepository('materials')
purposes_repo = DictionaryRepository('purposes')
equipment_repo = DictionaryRepository('equipment')
payers_repo = DictionaryRepository('payers')
customers_repo = DictionaryRepository('customers')
suppliers_repo = DictionaryRepository('suppliers')
products_repo = ProductsRepository()
cement_silos_repo = CementSilosRepository()
colors_repo = DictionaryRepository('colors')
cement_receipts_repo = CementReceiptsRepository()
production_repo = ProductionRepository()
warehouse_repo = WarehouseRepository()
reserved_products_repo = ReservedProductsRepository()
adjustment_repo = AdjustmentRepository()
sales_repo = SalesRepository()
cash_repo = CashRepository()
general_expenses_repo = GeneralExpensesRepository()