"""
Скрипт для сборки EXE-файла программы "ООО Евроблок"
Поддержка многопользовательского режима через сетевую папку.

Использование:
    python build_exe.py

После сборки:
    1. EXE-файл будет в папке dist/
    2. Ярлык "Евроблок.lnk" будет создан на рабочем столе
    3. Папка assets/ скопируется рядом с EXE
    4. Будет создан шаблон network_config.ini
"""
import subprocess
import sys
import os
import shutil
import ctypes


# ============================================================================
# ОЧИСТКА ПРЕДЫДУЩИХ СБОРОК
# ============================================================================
def clean_build():
    """Удалить предыдущие сборки"""
    print("Очистка предыдущих сборок...")
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Удалена папка: {dir_name}")
    
    for file in os.listdir('.'):
        if file.endswith('.spec'):
            os.remove(file)
            print(f"✓ Удалён файл: {file}")
    
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            shutil.rmtree(pycache_path)
    
    print("✓ Очистка завершена")
    print()


# ============================================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# ============================================================================
def check_pyinstaller():
    """Проверить наличие PyInstaller"""
    print("Проверка зависимостей...")
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller версии {PyInstaller.__version__}")
        return True
    except ImportError:
        print("  ✗ PyInstaller не установлен!")
        print()
        print("Установите его командой:")
        print("  pip install pyinstaller")
        print()
        return False


def check_assets():
    """Проверить наличие папки assets и файлов"""
    assets_path = os.path.join('.', 'assets')
    if not os.path.exists(assets_path):
        print(f"  ⚠ Папка assets не найдена")
        print(f"  → Создаём пустую папку assets/")
        os.makedirs(assets_path, exist_ok=True)
        print()
        print("  ВАЖНО: Для встраивания иконки в EXE:")
        print("  1. Конвертируйте logo.png в icon.ico")
        print("  2. Поместите icon.ico в папку assets/")
        print("  3. Онлайн-конвертер: https://convertio.co/png-ico/")
        print()
        return False, False
    
    logo_path = os.path.join(assets_path, 'logo.png')
    icon_path = os.path.join(assets_path, 'icon.ico')
    
    has_logo = os.path.exists(logo_path)
    has_icon = os.path.exists(icon_path)
    
    if has_logo:
        print(f"  ✓ Найден логотип: logo.png")
    else:
        print(f"  ⚠ Логотип logo.png не найден")
    
    if has_icon:
        print(f"  ✓ Найдена иконка: icon.ico")
        print(f"     Иконка будет ВСТРОЕНА в EXE-файл!")
    else:
        print(f"  ✗ Иконка icon.ico НЕ найдена")
        print()
        print("  БЕЗ ИКОНКИ EXE будет со стандартной иконкой Python!")
        print()
        print("  Для встраивания иконки:")
        print("  1. Конвертируйте logo.png в icon.ico")
        print("     Онлайн-конвертер: https://convertio.co/png-ico/")
        print("  2. Поместите icon.ico в папку assets/")
        print("  3. Запустите сборку заново: python build_exe.py")
        print()
        response = input("  Продолжить сборку БЕЗ иконки? (y/n): ").strip().lower()
        if response != 'y':
            return False, False
    
    return has_logo, has_icon


# ============================================================================
# СБОРКА EXE
# ============================================================================
def build_exe():
    """Собрать EXE-файл с встроенной иконкой"""
    print("=" * 70)
    print("Сборка EXE-файла программы ООО Евроблок")
    print("=" * 70)
    print()
    
    if not check_pyinstaller():
        return False
    
    has_logo, has_icon = check_assets()
    
    if not has_icon:
        print()
        print("✗ Сборка отменена: иконка icon.ico не найдена")
        print()
        print("Создайте файл assets/icon.ico и запустите сборку заново.")
        return False
    
    print()
    
    # Формируем параметры
    assets_option = []
    icon_option = []
    
    if has_logo:
        assets_option = ['--add-data', f'assets{os.pathsep}assets']
        print("✓ Папка assets будет включена в сборку")
    
    if has_icon:
        icon_option = ['--icon', 'assets/icon.ico']
        print("✓ Иконка icon.ico будет ВСТРОЕНА в EXE-файл")
    
    print()
    
    # Параметры сборки
    command = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',           # Один EXE-файл
        '--windowed',          # Без консольного окна
        '--name=Евроблок',     # Имя EXE-файла
        '--noconfirm',         # Не спрашивать подтверждение
        '--clean',             # Очистить временные файлы
    ] + icon_option + assets_option + [
        # ====================================================================
        # СКРЫТЫЕ ИМПОРТЫ — все модули проекта
        # ====================================================================
        # Зависимости
        '--hidden-import=reportlab',
        '--hidden-import=reportlab.lib',
        '--hidden-import=reportlab.lib.pagesizes',
        '--hidden-import=reportlab.lib.colors',
        '--hidden-import=reportlab.lib.units',
        '--hidden-import=reportlab.platypus',
        '--hidden-import=reportlab.pdfbase',
        '--hidden-import=reportlab.pdfbase.ttfonts',
        '--hidden-import=reportlab.lib.styles',
        
        # Конфигурация
        '--hidden-import=config',
        '--hidden-import=config.settings',
        '--hidden-import=client_config',
        
        # База данных
        '--hidden-import=database',
        '--hidden-import=database.connection',
        '--hidden-import=database.repositories',
        '--hidden-import=database.cache',
        '--hidden-import=database.notifications',
        '--hidden-import=database.locking',
        
        # UI - главное окно и настройки
        '--hidden-import=ui',
        '--hidden-import=ui.main_window',
        '--hidden-import=ui.base_window',
        '--hidden-import=ui.settings_panel',
        
        # UI - окна разделов
        '--hidden-import=ui.windows',
        '--hidden-import=ui.windows.cement_receipt_window',
        '--hidden-import=ui.windows.production_window',
        '--hidden-import=ui.windows.reserved_products_window',
        '--hidden-import=ui.windows.sales_window',
        '--hidden-import=ui.windows.cash_window',
        '--hidden-import=ui.windows.general_expenses_window',
        '--hidden-import=ui.windows.cement_report_window',
        '--hidden-import=ui.windows.expenses_report_window',
        '--hidden-import=ui.windows.sales_report_window',
        '--hidden-import=ui.windows.production_report_window',
        '--hidden-import=ui.windows.inert_materials_window',
        
        # UI - окна настроек (справочники)
        '--hidden-import=ui.windows.base_dictionary_window',
        '--hidden-import=ui.windows.payment_type_window',
        '--hidden-import=ui.windows.materials_window',
        '--hidden-import=ui.windows.purposes_window',
        '--hidden-import=ui.windows.equipment_window',
        '--hidden-import=ui.windows.payers_window',
        '--hidden-import=ui.windows.customers_window',
        '--hidden-import=ui.windows.suppliers_window',
        '--hidden-import=ui.windows.products_window',
        '--hidden-import=ui.windows.cement_silos_window',
        '--hidden-import=ui.windows.colors_window',
        
        # [НОВОЕ] Мастер настройки
        '--hidden-import=ui.windows.setup_wizard',
        
        # UI - виджеты
        '--hidden-import=ui.widgets',
        '--hidden-import=ui.widgets.date_entry',
        '--hidden-import=ui.widgets.combobox_autocomplete',
        '--hidden-import=ui.widgets.silo_canvas',
        '--hidden-import=ui.widgets.custom_messagebox',
        '--hidden-import=ui.widgets.progress_dialog',
        '--hidden-import=ui.widgets.paginated_treeview',
        
        # Утилиты
        '--hidden-import=utils',
        '--hidden-import=utils.resources',
        '--hidden-import=utils.performance_logger',
        '--hidden-import=utils.data_cache',
        '--hidden-import=utils.excel_reader',
        '--hidden-import=utils.pdf_utils',
        '--hidden-import=utils.async_operations',
        
        # Точка входа
        'main.py'
    ]
    
    print("Запуск сборки...")
    print()
    
    try:
        subprocess.run(command, check=True)
        
        print()
        print("=" * 70)
        print("✓ Сборка успешно завершена!")
        print("=" * 70)
        print()
        
        exe_path = os.path.join('dist', 'Евроблок.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"EXE-файл: {exe_path}")
            print(f"Размер: {size_mb:.2f} МБ")
            
            # Копируем папку assets рядом с EXE
            if has_logo:
                copy_assets_to_dist()
            
            # Создаём шаблон network_config.ini
            create_network_config_template()
            
            # Создаём ярлык на рабочем столе
            create_shortcut(exe_path)
            
            print()
            print("=" * 70)
            print("ГОТОВО!")
            print("=" * 70)
            print()
            print("✓ EXE-файл создан с вашей иконкой")
            print("✓ Папка assets/ скопирована рядом с EXE")
            print("✓ Создан шаблон network_config.ini")
            print("✓ Ярлык создан на рабочем столе")
            print()
            print("=" * 70)
            print("СЛЕДУЮЩИЕ ШАГИ ДЛЯ МНОГОПОЛЬЗОВАТЕЛЬСКОЙ РАБОТЫ:")
            print("=" * 70)
            print()
            print("1. Скопируйте ВСЮ папку dist/ на основной компьютер")
            print("   (например, в C:\\Euroblock\\)")
            print()
            print("2. Создайте общий доступ к папке:")
            print("   - Правой кнопкой на папку → Свойства → Доступ")
            print("   - Расширенная настройка → Открыть общий доступ")
            print("   - Разрешения → Добавить пользователей с правами 'Изменение'")
            print()
            print("3. На основном компьютере запустите Евроблок.exe")
            print("   → Появится мастер настройки")
            print("   → Выберите 'Да, это основной компьютер'")
            print("   → Запишите данные для подключения (IP, путь)")
            print()
            print("4. На клиентских компьютерах:")
            print("   - Скопируйте ТОЛЬКО Евроблок.exe и папку assets/")
            print("   - Запустите программу")
            print("   → Выберите 'Нет, это клиентский компьютер'")
            print("   → Введите путь к БД (из шага 3)")
            print()
            print("5. Готово! Все компьютеры работают с одной БД")
            print()
            
            return True
    
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 70)
        print("✗ Ошибка сборки!")
        print("=" * 70)
        print(f"Код ошибки: {e.returncode}")
        return False


# ============================================================================
# КОПИРОВАНИЕ ASSETS
# ============================================================================
def copy_assets_to_dist():
    """Скопировать папку assets в dist/"""
    src = os.path.join('.', 'assets')
    dst = os.path.join('dist', 'assets')
    
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"✓ Папка assets/ скопирована в dist/")


# ============================================================================
# [НОВОЕ] СОЗДАНИЕ ШАБЛОНА network_config.ini
# ============================================================================
def create_network_config_template():
    """Создать шаблон файла конфигурации в папке dist/"""
    dist_dir = 'dist'
    if not os.path.exists(dist_dir):
        return
    
    config_path = os.path.join(dist_dir, 'network_config.ini.template')
    
    template_content = """# ============================================================================
# ШАБЛОН КОНФИГУРАЦИИ МНОГОПОЛЬЗОВАТЕЛЬСКОГО РЕЖИМА
# ============================================================================
# Этот файл нужно скопировать как 'network_config.ini' и настроить.
# 
# ПРИ ПЕРВОМ ЗАПУСКЕ программа автоматически создаст правильный
# network_config.ini через мастер настройки. Этот шаблон нужен
# только для ручной настройки.
# ============================================================================

# Режим работы программы:
#   local   - локальная база данных (основной компьютер)
#   network - база данных в сетевой папке (клиентский компьютер)
#   server  - через HTTP-сервер (устаревший режим)

[mode]
mode = local

# ============================================================================
# Настройки для основного компьютера (mode = local)
# ============================================================================
[local]
# Путь к локальной базе данных (обычно рядом с EXE)
db_path = C:\\Euroblock\\euroblock.db
is_main = true

# ============================================================================
# Настройки для клиентского компьютера (mode = network)
# ============================================================================
[network]
# Путь к базе данных на основном компьютере
# Примеры:
#   \\\\OFFICE-PC\\Euroblock\\euroblock.db
#   \\\\192.168.1.100\\Общая\\Euroblock\\euroblock.db
#   Z:\\Euroblock\\euroblock.db  (если диск Z: подключен как сетевой)
db_path = \\\\ИМЯ_КОМПЬЮТЕРА\\Общая_папка\\euroblock.db

# Таймаут ожидания при блокировке БД (в секундах)
# Увеличьте при медленной сети
busy_timeout = 30

# Интервал проверки изменений БД от других клиентов (в секундах)
check_interval = 2

# Этот компьютер НЕ является основным
is_main = false

# ============================================================================
# Настройки для серверного режима (mode = server) - устаревший
# ============================================================================
[server]
url = http://192.168.1.100:5000
timeout = 30
"""
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        print(f"✓ Создан шаблон конфигурации: {config_path}")
    except Exception as e:
        print(f"⚠ Не удалось создать шаблон конфигурации: {e}")


# ============================================================================
# СОЗДАНИЕ ЯРЛЫКА
# ============================================================================
def get_desktop_path():
    """Получить путь к рабочему столу текущего пользователя"""
    try:
        CSIDL_DESKTOPDIRECTORY = 0x0010
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf)
        return buf.value
    except:
        return os.path.join(os.path.expanduser('~'), 'Desktop')


def create_shortcut(exe_path: str):
    """Создать ярлык на рабочем столе"""
    desktop = get_desktop_path()
    shortcut_path = os.path.join(desktop, 'Евроблок.lnk')
    
    icon_location = f"{exe_path},0"
    
    exe_path_ps = exe_path.replace('\\', '\\\\')
    shortcut_path_ps = shortcut_path.replace('\\', '\\\\')
    icon_location_ps = icon_location.replace('\\', '\\\\')
    
    ps_command = f'''
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path_ps}")
$Shortcut.TargetPath = "{exe_path_ps}"
$Shortcut.WorkingDirectory = "{os.path.dirname(exe_path_ps)}"
$Shortcut.IconLocation = "{icon_location_ps}"
$Shortcut.Description = "ООО Евроблок - производство и финансы"
$Shortcut.Save()
'''
    
    try:
        subprocess.run(
            ['powershell', '-Command', ps_command],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Ярлык создан: {shortcut_path}")
        print(f"  Иконка: из EXE-файла (встроена)")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Не удалось создать ярлык: {e}")
        print(f"  Создайте ярлык вручную:")
        print(f"  1. Правой кнопкой на Евроблок.exe")
        print(f"  2. Отправить → Рабочий стол (создать ярлык)")
    except FileNotFoundError:
        print(f"⚠ PowerShell не найден. Создайте ярлык вручную.")


# ============================================================================
# СОЗДАНИЕ README
# ============================================================================
def create_readme():
    """Создать файл README.txt в папке dist"""
    dist_dir = 'dist'
    if not os.path.exists(dist_dir):
        return
    
    readme_path = os.path.join(dist_dir, 'README.txt')
    
    readme_content = """
================================================================================
ПРОГРАММА "ООО ЕВРОБЛОК" - ПРОИЗВОДСТВО И ФИНАНСЫ
================================================================================

БЫСТРЫЙ СТАРТ (однопользовательский режим):
--------------------------------------------
1. Запустите Евроблок.exe двойным кликом
2. При первом запуске появится мастер настройки
3. Выберите "Да, это основной компьютер"
4. Готово! Программа создаст базу данных автоматически.

Ярлык для запуска находится на рабочем столе.

================================================================================
МНОГОПОЛЬЗОВАТЕЛЬСКАЯ РАБОТА (несколько компьютеров):
================================================================================

ШАГ 1. Подготовка основного компьютера:
----------------------------------------
1. Скопируйте всю папку dist/ на основной компьютер
   (например, в C:\\Euroblock\\)
   
2. Создайте общий доступ к папке:
   - Правой кнопкой на папку → Свойства → Доступ
   - Расширенная настройка → Открыть общий доступ
   - Разрешения → Добавить пользователей с правами "Изменение"
   
3. Запустите Евроблок.exe
   - Появится мастер настройки
   - Выберите "Да, это основной компьютер"
   - Запишите данные для подключения:
     * Имя компьютера: OFFICE-PC
     * IP-адрес: 192.168.1.100
     * Путь для клиентов: \\\\OFFICE-PC\\Euroblock\\euroblock.db

ШАГ 2. Настройка клиентских компьютеров:
-----------------------------------------
1. На каждом клиентском компьютере скопируйте:
   - Евроблок.exe
   - Папку assets/
   
2. Запустите Евроблок.exe
   - Появится мастер настройки
   - Выберите "Нет, это клиентский компьютер"
   - Введите путь к БД (из шага 1):
     \\\\OFFICE-PC\\Euroblock\\euroblock.db
   
3. Нажмите "Подключиться"
   - Готово! Программа автоматически подключится к основной БД

ШАГ 3. Создание ярлыков:
-------------------------
На каждом клиентском компьютере создайте ярлык на Евроблок.exe.
При последующих запусках подключение происходит автоматически.

================================================================================
СТРУКТУРА ПАПОК:
================================================================================

Основной компьютер:
C:\\Euroblock\\
├── Евроблок.exe              ← программа
├── euroblock.db              ← база данных (создаётся автоматически)
├── network_config.ini        ← настройки (создаётся мастером)
├── .first_run_done           ← маркер первого запуска
├── README.txt                ← этот файл
└── assets\\
    ├── logo.png              ← логотип компании
    └── icon.ico              ← иконка программы

Клиентский компьютер:
C:\\Euroblock\\
├── Евроблок.exe              ← программа
├── network_config.ini        ← настройки (создаётся мастером)
├── .first_run_done           ← маркер первого запуска
└── assets\\
    ├── logo.png              ← логотип компании
    └── icon.ico              ← иконка программы

================================================================================
ТРЕБОВАНИЯ:
================================================================================
- Windows 7/8/10/11
- Локальная сеть (все компьютеры в одной сети)
- Свободное место: минимум 100 МБ на каждом компьютере
- Сетевая папка с правами чтения/записи для всех пользователей
- Рекомендуется: гигабитная сеть (100 Мбит/с минимум)

================================================================================
РЕШЕНИЕ ПРОБЛЕМ:
================================================================================

ПРОБЛЕМА: Основной компьютер недоступен
РЕШЕНИЕ:
  1. Проверьте, что основной компьютер включён
  2. Проверьте доступность сетевой папки через Проводник
  3. Проверьте права доступа к сетевой папке
  4. Проверьте сетевое соединение (ping OFFICE-PC)

ПРОБЛЕМА: Ошибка "Нет прав на запись"
РЕШЕНИЕ:
  1. Обратитесь к администратору
  2. Проверьте права доступа к сетевой папке
  3. Убедитесь, что у пользователя есть права "Изменение"

ПРОБЛЕМА: Нужно перенастроить подключение
РЕШЕНИЕ:
  1. Удалите файлы network_config.ini и .first_run_done
  2. Перезапустите программу
  3. Мастер настройки запустится снова

ПРОБЛЕМА: База данных повреждена
РЕШЕНИЕ:
  1. Программа создаст бэкап в папке backups/
  2. Создастся новая БД
  3. Данные из бэкапа можно восстановить вручную

ПРОБЛЕМА: Логотип не отображается
РЕШЕНИЕ:
  1. Проверьте, что assets/logo.png находится рядом с EXE
  2. Проверьте права доступа к папке assets/

ПРОБЛЕМА: Иконка не отображается
РЕШЕНИЕ:
  1. Перезапустите Проводник (Ctrl+Shift+Esc → Проводник → Перезапустить)
  2. Или очистите кэш иконок: ie4uinit.exe -show

================================================================================
ВАЖНЫЕ ЗАМЕЧАНИЯ:
================================================================================

1. НЕ ВЫКЛЮЧАЙТЕ основной компьютер во время работы!
   Все клиентские компьютеры потеряют доступ к БД.

2. РЕГУЛЯРНО ДЕЛАЙТЕ резервные копии БД:
   - Папка backups/ создаётся автоматически
   - Или вручную копируйте euroblock.db

3. Используйте ПРОВОДНОЕ подключение (не Wi-Fi) для стабильности.

4. Ограничение SQLite: НЕ БОЛЕЕ 5-10 одновременных пользователей.

5. При обрыве сети данные НЕ ТЕРЯЮТСЯ, но программа покажет ошибку.

================================================================================
КОНТАКТЫ РАЗРАБОТЧИКА:
================================================================================
При возникновении проблем обратитесь к разработчику.
================================================================================
"""
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✓ Создан файл README.txt в папке dist/")


# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================
if __name__ == "__main__":
    clean_build()
    success = build_exe()
    
    if success:
        create_readme()
        
        print()
        print("✓ Всё готово!")
        print()
        print("Следующие шаги:")
        print("  1. Проверьте EXE-файл в папке dist/")
        print("  2. Убедитесь, что иконка отображается")
        print("  3. Проверьте ярлык на рабочем столе")
        print("  4. Запустите программу для проверки")
        print("  5. Скопируйте папку dist/ на основной компьютер")
        print("  6. Настройте общий доступ к папке")
        print("  7. Запустите мастер настройки на основном компьютере")
        print("  8. Настройте клиентские компьютеры")
        print()
    else:
        print()
        print("✗ Сборка не удалась или отменена.")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)