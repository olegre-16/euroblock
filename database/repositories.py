"""
Репозитории для работы с таблицами базы данных.
[ИЗМЕНЕНО] Добавлены методы пагинации (LIMIT/OFFSET) и оптимизированы SQL-запросы.
"""
import sqlite3
from database.connection import get_connection, return_connection
from database.cache import query_cache


def _invalidate_table_cache(table_name: str):
    """Инвалидировать кэш таблицы после изменений"""
    try:
        query_cache.invalidate(table_name)
    except Exception as e:
        print(f"⚠ Ошибка инвалидации кэша для {table_name}: {e}")


# ============================================================================
# УНИВЕРСАЛЬНЫЙ СПРАВОЧНИК
# ============================================================================
class DictionaryRepository:
    def __init__(self, table_name):
        self.table_name = table_name
    
    def get_all(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT name FROM {self.table_name} ORDER BY name COLLATE NOCASE')
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    def get_id(self, name):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT id FROM {self.table_name} WHERE name = ?', (name,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            return_connection(conn)
    
    def add(self, name):
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        name = name.strip()
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'INSERT INTO {self.table_name} (name) VALUES (?)', (name,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись добавлена"
        except sqlite3.IntegrityError:
            return False, "Такая запись уже существует"
        finally:
            return_connection(conn)
    
    def delete(self, name):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE name = ?', (name,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
        finally:
            return_connection(conn)


# ============================================================================
# ПРОДУКЦИЯ
# ============================================================================
class ProductsRepository:
    def __init__(self):
        self.table_name = 'products'
    
    def get_all(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT name, volume_per_pallet, production_rate 
                FROM {self.table_name} 
                ORDER BY 
                    CASE WHEN name LIKE '%(брак)%' THEN 1 ELSE 0 END,
                    name COLLATE NOCASE
            ''')
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    def add(self, name, volume_per_pallet=None, production_rate=None):
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        name = name.strip()
        vol = self._parse_number(volume_per_pallet)
        rate = self._parse_number(production_rate)
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f'INSERT INTO {self.table_name} (name, volume_per_pallet, production_rate) VALUES (?, ?, ?)',
                (name, vol, rate)
            )
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Продукция добавлена"
        except sqlite3.IntegrityError:
            return False, "Такая продукция уже существует"
        finally:
            return_connection(conn)
    
    def update(self, old_name, new_name, volume_per_pallet=None, production_rate=None):
        if not new_name or not new_name.strip():
            return False, "Название не может быть пустым"
        new_name = new_name.strip()
        vol = self._parse_number(volume_per_pallet)
        rate = self._parse_number(production_rate)
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f'''UPDATE {self.table_name} 
                    SET name = ?, volume_per_pallet = ?, production_rate = ? 
                    WHERE name = ?''',
                (new_name, vol, rate, old_name)
            )
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись обновлена"
        except sqlite3.IntegrityError:
            return False, "Такая продукция уже существует"
        finally:
            return_connection(conn)
    
    def delete(self, name):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE name = ?', (name,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
        finally:
            return_connection(conn)
    
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
# СИЛОСЫ ЦЕМЕНТА
# ============================================================================
class CementSilosRepository:
    def __init__(self):
        self.table_name = 'cement_silos'
    
    def get_all(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT name, capacity 
                FROM {self.table_name} 
                ORDER BY name COLLATE NOCASE
            ''')
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    def add(self, name, capacity=None):
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        name = name.strip()
        cap = self._parse_number(capacity)
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f'INSERT INTO {self.table_name} (name, capacity) VALUES (?, ?)',
                (name, cap)
            )
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Силос цемента добавлен"
        except sqlite3.IntegrityError:
            return False, "Такой силос цемента уже существует"
        finally:
            return_connection(conn)
    
    def update(self, old_name, new_name, capacity=None):
        if not new_name or not new_name.strip():
            return False, "Название не может быть пустым"
        new_name = new_name.strip()
        cap = self._parse_number(capacity)
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f'''UPDATE {self.table_name} 
                    SET name = ?, capacity = ? 
                    WHERE name = ?''',
                (new_name, cap, old_name)
            )
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись обновлена"
        except sqlite3.IntegrityError:
            return False, "Такой силос цемента уже существует"
        finally:
            return_connection(conn)
    
    def delete(self, name):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE name = ?', (name,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
        finally:
            return_connection(conn)
    
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
# ПОСТУПЛЕНИЯ ЦЕМЕНТА
# ============================================================================
class CementReceiptsRepository:
    """Репозиторий для работы с поступлениями цемента"""
    def __init__(self):
        self.table_name = 'cement_receipts'
    
    # [ИЗМЕНЕНО] Корректная сортировка дат через substr()
    def get_all_receipts(self):
        """Получить все поступления, отсортированные по дате (убывание)"""
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
    
    # [ИЗМЕНЕНО] Теперь возвращает (True, "Запись удалена") или (False, "Ошибка...")
    def delete_receipt(self, receipt_id):
        """Удалить запись о поступлении"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
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
    
    # [НОВОЕ] Алиас для совместимости
    def delete(self, *args, **kwargs):
        """Алиас для delete_receipt"""
        return self.delete_receipt(*args, **kwargs)
    
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
    
    # [НОВОЕ] Алиас для совместимости
    def get_by_id(self, receipt_id):
        """Алиас для get_receipt_by_id"""
        return self.get_receipt_by_id(receipt_id)
    
    def get_current_balance_by_silo(self):
        """Получить текущий баланс по каждому силосу."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT silo_name, SUM(quantity_kg) as total
            FROM cement_receipts
            GROUP BY silo_name
        ''')
        receipts = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute('''
            SELECT silo_name, SUM(cement_kg) as total
            FROM production
            WHERE silo_name IS NOT NULL AND silo_name != '' 
                  AND cement_kg IS NOT NULL AND cement_kg > 0
            GROUP BY silo_name
        ''')
        production_consumption = {row[0]: row[1] for row in cursor.fetchall()}
        all_silos = set(receipts.keys()) | set(production_consumption.keys())
        balance = {}
        for silo in all_silos:
            receipt_total = receipts.get(silo, 0) or 0
            consumption_total = production_consumption.get(silo, 0) or 0
            balance[silo] = receipt_total - consumption_total
        conn.close()
        return balance
    
    # ... остальные методы (get_cement_report, get_cement_monthly_report) оставляем БЕЗ ИЗМЕНЕНИЙ ...
    def get_cement_report(self):
        """Получить полный отчет по движению цемента."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT receipt_date, silo_name, quantity_kg
                FROM cement_receipts
                WHERE silo_name IS NOT NULL AND silo_name != ''
            ''')
            receipts = cursor.fetchall()
            cursor.execute('''
                SELECT production_date, silo_name, cement_kg
                FROM production
                WHERE silo_name IS NOT NULL AND silo_name != '' 
                      AND cement_kg IS NOT NULL AND cement_kg > 0
            ''')
            consumptions = cursor.fetchall()
            operations = []
            for date, silo, qty in receipts:
                operations.append((date, silo, qty or 0, 0))
            for date, silo, qty in consumptions:
                operations.append((date, silo, 0, qty or 0))
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
            silo_balances = {}
            result_with_balance = []
            for date, silo, receipt, consumption in operations:
                if silo not in silo_balances:
                    silo_balances[silo] = 0
                silo_balances[silo] = silo_balances[silo] + receipt - consumption
                balance = silo_balances[silo]
                result_with_balance.append((date, silo, receipt, consumption, balance))
            result_with_balance.sort(key=lambda x: date_to_comparable(x[0]), reverse=True)
            return result_with_balance
        except Exception as e:
            return []
        finally:
            conn.close()
    
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
            all_keys = set(receipts.keys()) | set(consumptions.keys())
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
                receipt_total = receipts.get((month_num, year_num, silo), 0)
                consumption_total = consumptions.get((month_num, year_num, silo), 0)
                adjustment = 0
                result.append((sort_key, month_str, silo, receipt_total, consumption_total, adjustment))
            result.sort(key=lambda x: (-int(x[0]), x[2].lower()))
            return result
        except Exception as e:
            print(f"Ошибка в get_cement_monthly_report: {e}")
            return []
        finally:
            conn.close()

            
# ============================================================================
# ПРОИЗВОДСТВО
# ============================================================================
class ProductionRepository:
    def __init__(self):
        self.table_name = 'production'
    
    def get_all(self):
        conn = get_connection()
        try:
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
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    # [НОВОЕ] Пагинация
    def get_all_paged(self, page=0, page_size=100):
        """Получить записи производства постранично"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name}')
            total = cursor.fetchone()[0]
            offset = page * page_size
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
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            return cursor.fetchall(), total
        finally:
            return_connection(conn)
    
    def get_daily_cement_totals(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT production_date, SUM(cement_kg) as total
                FROM {self.table_name}
                GROUP BY production_date
            ''')
            return {row[0]: row[1] for row in cursor.fetchall()}
        finally:
            return_connection(conn)
    
    def get_by_id(self, production_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, production_date, equipment_name, silo_name, product_name, 
                       color_name, quantity_pallets, cement_kg, enriched_sand_kg, 
                       river_sand_kg, keramzit_kg, plasticizer_kg, water_kg, note
                FROM {self.table_name} WHERE id = ?
            ''', (production_id,))
            return cursor.fetchone()
        finally:
            return_connection(conn)
    
    def get_cement_consumption_by_date(self, date_str):
        conn = get_connection()
        try:
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
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    def update_cement_consumption_by_date(self, date_str, silo_consumption):
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
                new_value = self._parse_number(new_cement_kg) or 0
                if silo_name in silo_records:
                    records_for_silo = silo_records[silo_name]
                    cursor.execute(f'''
                        UPDATE {self.table_name} SET cement_kg = ? WHERE id = ?
                    ''', (new_value, records_for_silo[0][0]))
                    for i in range(1, len(records_for_silo)):
                        cursor.execute(f'''
                            UPDATE {self.table_name} SET cement_kg = 0 WHERE id = ?
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
                            UPDATE {self.table_name} SET cement_kg = 0 WHERE id = ?
                        ''', (record_id,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Расход цемента обновлён"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            return_connection(conn)
    
    def add(self, production_date, equipment_name, silo_name, product_name, 
            color_name, quantity_pallets, cement_kg, enriched_sand_kg, 
            river_sand_kg, keramzit_kg, plasticizer_kg, water_kg, note):
        if not production_date:
            return False, "Дата не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            _invalidate_table_cache(self.table_name)
            return True, "Запись о производстве добавлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка добавления: {e}"
        finally:
            return_connection(conn)
    
    def update(self, production_id, production_date, equipment_name, silo_name,
               product_name, color_name, quantity_pallets, cement_kg,
               enriched_sand_kg, river_sand_kg, keramzit_kg, plasticizer_kg,
               water_kg, note):
        if not production_date:
            return False, "Дата не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            _invalidate_table_cache(self.table_name)
            return True, "Запись обновлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            return_connection(conn)
    
    def delete(self, production_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (production_id,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            return_connection(conn)
    
    def delete_by_date(self, date_str):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name} WHERE production_date = ?', (date_str,))
            count = cursor.fetchone()[0]
            if count == 0:
                return False, "Записей за этот день не найдено"
            cursor.execute(f'DELETE FROM {self.table_name} WHERE production_date = ?', (date_str,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, f"Удалено записей за {date_str}: {count}"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            return_connection(conn)
    
    def get_production_report(self, start_date=None, end_date=None, equipment=None, product=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка в get_production_report: {e}")
            return []
        finally:
            return_connection(conn)
    
    # [ОПТИМИЗИРОВАНО] Группировка перенесена в SQL
    def get_inert_materials_report(self, start_date=None, end_date=None, equipment=None, product=None):
        """
        Отчет по расходу инертных материалов.
        [ОПТИМИЗИРОВАНО] Группировка выполняется в SQL через JOIN + GROUP BY,
        а не в Python. Это значительно ускоряет работу на больших объемах.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            # Базовый запрос с JOIN на products для получения volume_per_pallet
            query = '''
                SELECT p.production_date, p.equipment_name, p.product_name,
                       SUM(p.quantity_pallets * COALESCE(pr.volume_per_pallet, 1)) as total_qty,
                       SUM(p.cement_kg) as total_cement,
                       SUM(p.enriched_sand_kg) as total_enriched_sand,
                       SUM(p.river_sand_kg) as total_river_sand,
                       SUM(p.keramzit_kg) as total_keramzit,
                       SUM(p.plasticizer_kg) as total_plasticizer,
                       SUM(p.water_kg) as total_water
                FROM production p
                LEFT JOIN products pr ON p.product_name = pr.name
                WHERE p.product_name IS NOT NULL AND p.product_name != ''
            '''
            params = []
            
            if start_date:
                try:
                    parts = start_date.split('.')
                    if len(parts) == 3:
                        day, month, year = parts
                        start_cmp = f"{year}{month.zfill(2)}{day.zfill(2)}"
                        query += '''
                            AND substr(p.production_date, 7, 4) || substr(p.production_date, 4, 2) || substr(p.production_date, 1, 2) >= ?
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
                            AND substr(p.production_date, 7, 4) || substr(p.production_date, 4, 2) || substr(p.production_date, 1, 2) <= ?
                        '''
                        params.append(end_cmp)
                except:
                    pass
            
            if equipment:
                query += ' AND p.equipment_name = ?'
                params.append(equipment)
            if product:
                query += ' AND p.product_name = ?'
                params.append(product)
            
            query += '''
                GROUP BY p.production_date, p.equipment_name, p.product_name
                ORDER BY 
                    substr(p.production_date, 7, 4) || '-' || 
                    substr(p.production_date, 4, 2) || '-' || 
                    substr(p.production_date, 1, 2) DESC,
                    p.equipment_name, p.product_name
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Рассчитываем расход на единицу продукции
            result = []
            for row in rows:
                (date, equip_name, prod_name, qty,
                 cement, enriched_sand, river_sand,
                 keramzit, plasticizer, water) = row
                
                if qty and qty > 0:
                    result.append({
                        'date': date,
                        'equipment': equip_name or '',
                        'product': prod_name,
                        'quantity': qty,
                        'cement_per_unit': (cement or 0) / qty,
                        'enriched_sand_per_unit': (enriched_sand or 0) / qty,
                        'plasticizer_per_unit': (plasticizer or 0) / qty,
                        'river_sand_per_unit': (river_sand or 0) / qty,
                        'keramzit_per_unit': (keramzit or 0) / qty,
                        'water_per_unit': (water or 0) / qty
                    })
            
            return result
        except Exception as e:
            print(f"Ошибка в get_inert_materials_report: {e}")
            return []
        finally:
            return_connection(conn)
    
    def get_inert_materials_summary(self, start_date=None, end_date=None):
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
        if value is None or value == '':
            return None
        try:
            if isinstance(value, str):
                value = value.replace(',', '.').strip()
            return float(value)
        except (ValueError, TypeError):
            return None


# ============================================================================
# СКЛАД — [ОПТИМИЗИРОВАНО] Новый метод для быстрой загрузки сводки
# ============================================================================
class WarehouseRepository:
    def __init__(self):
        self.table_name = 'warehouse'
    
    def get_all(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT product_name, color_name, stock_qty, reserved_qty, 
                       (stock_qty - reserved_qty) as remaining_qty
                FROM {self.table_name}
                ORDER BY product_name COLLATE NOCASE, color_name COLLATE NOCASE
            ''')
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    # [НОВОЕ] Оптимизированный метод для главной страницы
    def get_warehouse_summary(self):
        """
        Получить полную сводку склада одним запросом.
        Объединяет данные из warehouse, production, adjustments, sales, reserved.
        Это в разы быстрее, чем делать 5+ отдельных запросов.
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Получаем volume_per_pallet из products
            cursor.execute('SELECT name, volume_per_pallet FROM products')
            volume_map = {row[0]: (row[1] if row[1] else 1) for row in cursor.fetchall()}
            
            # 2. Считаем произведенное количество с учетом volume_per_pallet
            cursor.execute('''
                SELECT product_name, color_name,
                       SUM(quantity_pallets) as total_pallets
                FROM production
                WHERE product_name IS NOT NULL AND product_name != ''
                GROUP BY product_name, color_name
            ''')
            production_data = {}
            for prod, color, pallets in cursor.fetchall():
                key = (prod.strip(), (color or '').strip())
                volume = volume_map.get(prod, 1)
                production_data[key] = (pallets or 0) * volume
            
            # 3. Корректировки
            cursor.execute('''
                SELECT product_name, color_name, SUM(difference) as total
                FROM adjustments
                GROUP BY product_name, color_name
            ''')
            adjustments = {(p.strip(), (c or '').strip()): t 
                          for p, c, t in cursor.fetchall()}
            
            # 4. Продано из резерва
            cursor.execute('''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM sold_from_reserve
                GROUP BY product_name, color_name
            ''')
            sold_reserve = {(p.strip(), (c or '').strip()): t 
                           for p, c, t in cursor.fetchall()}
            
            # 5. Прямые продажи
            cursor.execute('''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM sales
                GROUP BY product_name, color_name
            ''')
            direct_sales = {(p.strip(), (c or '').strip()): t 
                           for p, c, t in cursor.fetchall()}
            
            # 6. Резервы
            cursor.execute('''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM reserved_products
                GROUP BY product_name, color_name
            ''')
            reserved = {(p.strip(), (c or '').strip()): t 
                       for p, c, t in cursor.fetchall()}
            
            # 7. Собираем все ключи
            all_keys = (set(production_data.keys()) | set(adjustments.keys()) | 
                       set(sold_reserve.keys()) | set(direct_sales.keys()) | 
                       set(reserved.keys()))
            
            # 8. Рассчитываем итоги
            result = []
            for key in all_keys:
                product, color = key
                stock_qty = production_data.get(key, 0) + adjustments.get(key, 0)
                stock_qty -= sold_reserve.get(key, 0)
                stock_qty -= direct_sales.get(key, 0)
                reserved_qty = reserved.get(key, 0)
                remaining_qty = stock_qty - reserved_qty
                
                has_activity = (key in sold_reserve or key in direct_sales or 
                              key in adjustments)
                
                if stock_qty == 0 and reserved_qty == 0 and not has_activity:
                    continue
                
                result.append({
                    'product': product,
                    'color': color,
                    'stock_qty': stock_qty,
                    'reserved_qty': reserved_qty,
                    'remaining_qty': remaining_qty
                })
            
            # Сортировка: сначала без "(брак)", потом с "(брак)"
            def sort_key(item):
                has_brak = 1 if '(брак)' in item['product'] else 0
                return (has_brak, item['product'].lower(), item['color'].lower())
            
            result.sort(key=sort_key)
            return result
        except Exception as e:
            print(f"Ошибка в get_warehouse_summary: {e}")
            return []
        finally:
            return_connection(conn)
    
    def set_stock(self, product_name, color_name, new_qty, qty_before):
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            _invalidate_table_cache(self.table_name)
            return True, qty_before, difference
        except Exception as e:
            conn.rollback()
            return False, 0.0, str(e)
        finally:
            return_connection(conn)
    
    def add_or_update_stock(self, product_name, color_name, quantity):
        if not product_name or not color_name:
            return False, "Продукция и цвет обязательны"
        qty = self._parse_number(quantity)
        if qty is None:
            return False, "Некорректное количество"
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, stock_qty FROM {self.table_name}
                WHERE product_name = ? AND color_name = ?
            ''', (product_name, color_name))
            row = cursor.fetchone()
            if row:
                record_id, current_stock = row
                new_stock = max(0, (current_stock or 0) + qty)
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
            _invalidate_table_cache(self.table_name)
            return True, "Склад обновлён"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления склада: {e}"
        finally:
            return_connection(conn)
    
    def set_reserved(self, product_name, color_name, reserved_qty):
        if not product_name or not color_name:
            return False, "Продукция и цвет обязательны"
        qty = self._parse_number(reserved_qty)
        if qty is None:
            return False, "Некорректное количество резерва"
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, stock_qty FROM {self.table_name}
                WHERE product_name = ? AND color_name = ?
            ''', (product_name, color_name))
            row = cursor.fetchone()
            if row:
                record_id, current_stock = row
                max_reserve = current_stock or 0
                qty = min(qty, max_reserve)
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET reserved_qty = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (qty, record_id))
                conn.commit()
                _invalidate_table_cache(self.table_name)
                return True, "Резерв обновлён"
            else:
                return False, "Запись на складе не найдена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления резерва: {e}"
        finally:
            return_connection(conn)
    
    def delete_entry(self, product_name, color_name):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                DELETE FROM {self.table_name}
                WHERE product_name = ? AND color_name = ?
            ''', (product_name, color_name))
            conn.commit()
            _invalidate_table_cache(self.table_name)
        finally:
            return_connection(conn)
    
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
# РЕЗЕРВ ПРОДУКЦИИ
# ============================================================================
class ReservedProductsRepository:
    """Репозиторий для работы с продукцией в резерве"""
    def __init__(self):
        self.table_name = 'reserved_products'
        self.sold_table_name = 'sold_from_reserve'
    
    def get_all_reserved(self):
        """Получить все записи о резервах"""
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
        """Получить все записи о реализованной продукции"""
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
        """Получить сумму всех проданных товаров"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM {self.sold_table_name}
                GROUP BY product_name, color_name
            ''')
            result = {}
            for row in cursor.fetchall():
                product, color, qty = row
                key = (product.strip() if product else '', color.strip() if color else '')
                result[key] = qty or 0
            return result
        except Exception as e:
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
    
    def delete_reserved(self, reserve_id):
        """Удалить запись о резерве"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name} WHERE id = ?', (reserve_id,))
            count = cursor.fetchone()[0]
            if count == 0:
                return False, "Запись не найдена"
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (reserve_id,))
            conn.commit()
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            conn.close()
    
    # [НОВОЕ] Алиас для совместимости
    def delete(self, *args, **kwargs):
        """Алиас для delete_reserved"""
        return self.delete_reserved(*args, **kwargs)
    
    def delete_sold(self, sold_id):
        """Удалить запись о реализованной продукции"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM {self.sold_table_name} WHERE id = ?', (sold_id,))
        conn.commit()
        conn.close()
    
    def move_to_sold(self, reserve_id, sale_date):
        """Переместить запись из резерва в реализованную продукцию."""
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

# ============================================================================
# КОРРЕКТИРОВКИ
# ============================================================================
class AdjustmentRepository:
    def __init__(self):
        self.table_name = 'adjustments'
    
    def log_adjustment(self, date_str, product_name, color_name, qty_before, qty_after, difference):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (adjustment_date, product_name, color_name, qty_before, qty_after, difference)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date_str, product_name, color_name, qty_before, qty_after, difference))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Корректировка сохранена"
        except Exception as e:
            return False, f"Ошибка сохранения: {e}"
        finally:
            return_connection(conn)
    
    def get_adjustments_sum(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT product_name, color_name, SUM(difference) as total
                FROM {self.table_name}
                GROUP BY product_name, color_name
            ''')
            result = {}
            for row in cursor.fetchall():
                product, color, diff = row
                key = (product.strip() if product else '', color.strip() if color else '')
                result[key] = diff or 0
            return result
        except Exception:
            return {}
        finally:
            return_connection(conn)


# ============================================================================
# ПРОДАЖИ
# ============================================================================
class SalesRepository:
    def __init__(self):
        self.table_name = 'sales'
    
    def get_all(self):
        conn = get_connection()
        try:
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
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    # [НОВОЕ] Пагинация
    def get_all_paged(self, page=0, page_size=100):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name}')
            total = cursor.fetchone()[0]
            offset = page * page_size
            cursor.execute(f'''
                SELECT id, sale_date, product_name, color_name, quantity, price, equipment_name
                FROM {self.table_name}
                ORDER BY 
                    substr(sale_date, 7, 4) || '-' || 
                    substr(sale_date, 4, 2) || '-' || 
                    substr(sale_date, 1, 2) DESC,
                    id DESC
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            return cursor.fetchall(), total
        finally:
            return_connection(conn)
    
    def get_by_id(self, sale_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, sale_date, product_name, color_name, quantity, price, equipment_name
                FROM {self.table_name} WHERE id = ?
            ''', (sale_id,))
            return cursor.fetchone()
        finally:
            return_connection(conn)
    
    def add(self, sale_date, product_name, color_name, quantity, price, equipment_name=None):
        if not sale_date:
            return False, "Дата не указана"
        if not product_name:
            return False, "Продукция не выбрана"
        if quantity is None:
            return False, "Количество не указано"
        if price is None:
            return False, "Цена не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (sale_date, product_name, color_name, quantity, price, equipment_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (sale_date, product_name, color_name, quantity, price, equipment_name))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Продажа добавлена"
        except Exception as e:
            return False, f"Ошибка добавления: {e}"
        finally:
            return_connection(conn)
    
    def update(self, sale_id, sale_date, product_name, color_name, quantity, price, equipment_name=None):
        if not sale_date:
            return False, "Дата не указана"
        if not product_name:
            return False, "Продукция не выбрана"
        if quantity is None:
            return False, "Количество не указано"
        if price is None:
            return False, "Цена не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE {self.table_name}
                SET sale_date = ?, product_name = ?, color_name = ?, quantity = ?, price = ?, equipment_name = ?
                WHERE id = ?
            ''', (sale_date, product_name, color_name, quantity, price, equipment_name, sale_id))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись обновлена"
        except Exception as e:
            return False, f"Ошибка обновления: {e}"
        finally:
            return_connection(conn)
    
    def delete(self, sale_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (sale_id,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись удалена"
        except Exception as e:
            return False, f"Ошибка удаления: {e}"
        finally:
            return_connection(conn)
    
    def get_sales_sum(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT product_name, color_name, SUM(quantity) as total
                FROM {self.table_name}
                GROUP BY product_name, color_name
            ''')
            result = {}
            for row in cursor.fetchall():
                product, color, qty = row
                key = (product.strip() if product else '', color.strip() if color else '')
                result[key] = qty or 0
            return result
        except Exception:
            return {}
        finally:
            return_connection(conn)
    
    def get_sales_report(self, start_date=None, end_date=None, equipment=None, product=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка в get_sales_report: {e}")
            return []
        finally:
            return_connection(conn)


# ============================================================================
# КАССА
# ============================================================================
class CashRepository:
    def __init__(self):
        self.table_name = 'cash_operations'
    
    def get_all(self):
        conn = get_connection()
        try:
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
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    # [НОВОЕ] Пагинация
    def get_all_paged(self, page=0, page_size=100):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name}')
            total = cursor.fetchone()[0]
            offset = page * page_size
            cursor.execute(f'''
                SELECT id, operation_date, income, expense
                FROM {self.table_name}
                ORDER BY 
                    substr(operation_date, 7, 4) || '-' || 
                    substr(operation_date, 4, 2) || '-' || 
                    substr(operation_date, 1, 2) DESC,
                    id DESC
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            return cursor.fetchall(), total
        finally:
            return_connection(conn)
    
    def get_by_id(self, operation_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, operation_date, income, expense
                FROM {self.table_name} WHERE id = ?
            ''', (operation_id,))
            return cursor.fetchone()
        finally:
            return_connection(conn)
    
    def add(self, operation_date, income, expense):
        if not operation_date:
            return False, "Дата не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT INTO {self.table_name} 
                (operation_date, income, expense)
                VALUES (?, ?, ?)
            ''', (operation_date, income or 0, expense or 0))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Операция добавлена"
        except Exception as e:
            return False, f"Ошибка добавления: {e}"
        finally:
            return_connection(conn)
    
    def delete(self, operation_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (operation_id,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Операция удалена"
        except Exception as e:
            return False, f"Ошибка удаления: {e}"
        finally:
            return_connection(conn)
    
    def clear_field(self, operation_id, field):
        if field not in ('income', 'expense'):
            return False, "Некорректное имя поля"
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT income, expense FROM {self.table_name} WHERE id = ?
            ''', (operation_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Запись не найдена"
            current_income, current_expense = row
            if field == 'income':
                new_income, new_expense = 0, current_expense or 0
            else:
                new_income, new_expense = current_income or 0, 0
            if new_income == 0 and new_expense == 0:
                cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (operation_id,))
                conn.commit()
                _invalidate_table_cache(self.table_name)
                return True, "Запись удалена (оба значения были обнулены)"
            else:
                cursor.execute(f'''
                    UPDATE {self.table_name}
                    SET income = ?, expense = ?
                    WHERE id = ?
                ''', (new_income, new_expense, operation_id))
                conn.commit()
                _invalidate_table_cache(self.table_name)
                field_name = "приход" if field == 'income' else "расход"
                return True, f"Значение '{field_name}' обнулено"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            return_connection(conn)
    
    def get_daily_totals(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT operation_date, 
                       SUM(income) as total_income, 
                       SUM(expense) as total_expense
                FROM {self.table_name}
                GROUP BY operation_date
            ''')
            result = {}
            for row in cursor.fetchall():
                date, income, expense = row
                result[date] = {'income': income or 0, 'expense': expense or 0}
            return result
        finally:
            return_connection(conn)
    
    def get_balance_up_to_date(self, target_date):
        conn = get_connection()
        try:
            parts = target_date.split('.')
            if len(parts) == 3:
                day, month, year = parts
                comparable = f"{year}{month.zfill(2)}{day.zfill(2)}"
            else:
                return 0
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT SUM(income) - SUM(expense) as balance
                FROM {self.table_name}
                WHERE substr(operation_date, 7, 4) || '-' || 
                      substr(operation_date, 4, 2) || '-' || 
                      substr(operation_date, 1, 2) <= ?
            ''', (comparable,))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        except Exception:
            return 0
        finally:
            return_connection(conn)


# ============================================================================
# ОБЩИЕ РАСХОДЫ
# ============================================================================
class GeneralExpensesRepository:
    def __init__(self):
        self.table_name = 'general_expenses'
    
    def get_all(self):
        conn = get_connection()
        try:
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
            return cursor.fetchall()
        finally:
            return_connection(conn)
    
    # [НОВОЕ] Пагинация
    def get_all_paged(self, page=0, page_size=100):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM {self.table_name}')
            total = cursor.fetchone()[0]
            offset = page * page_size
            cursor.execute(f'''
                SELECT id, expense_date, supplier_name, material_name, quantity, price,
                       payer_name, payment_type_name, purpose_name, comment
                FROM {self.table_name}
                ORDER BY 
                    substr(expense_date, 7, 4) || '-' || 
                    substr(expense_date, 4, 2) || '-' || 
                    substr(expense_date, 1, 2) DESC,
                    id DESC
                LIMIT ? OFFSET ?
            ''', (page_size, offset))
            return cursor.fetchall(), total
        finally:
            return_connection(conn)
    
    def get_by_id(self, expense_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT id, expense_date, supplier_name, material_name, quantity, price,
                       payer_name, payment_type_name, purpose_name, comment
                FROM {self.table_name} WHERE id = ?
            ''', (expense_id,))
            return cursor.fetchone()
        finally:
            return_connection(conn)
    
    def add(self, expense_date, supplier_name, material_name, quantity, price,
            payer_name, payment_type_name, purpose_name, comment):
        if not expense_date:
            return False, "Дата не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            _invalidate_table_cache(self.table_name)
            return True, "Запись о расходе добавлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка добавления: {e}"
        finally:
            return_connection(conn)
    
    def update(self, expense_id, expense_date, supplier_name, material_name,
               quantity, price, payer_name, payment_type_name, purpose_name, comment):
        if not expense_date:
            return False, "Дата не указана"
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            _invalidate_table_cache(self.table_name)
            return True, "Запись обновлена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка обновления: {e}"
        finally:
            return_connection(conn)
    
    def delete(self, expense_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE id = ?', (expense_id,))
            conn.commit()
            _invalidate_table_cache(self.table_name)
            return True, "Запись удалена"
        except Exception as e:
            conn.rollback()
            return False, f"Ошибка удаления: {e}"
        finally:
            return_connection(conn)
    
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
        conn = get_connection()
        try:
            cursor = conn.cursor()
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
            return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка в get_expenses_report: {e}")
            return []
        finally:
            return_connection(conn)


# ============================================================================
# ЭКЗЕМПЛЯРЫ РЕПОЗИТОРИЕВ
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