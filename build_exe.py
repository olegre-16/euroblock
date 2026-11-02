"""
Скрипт для сборки EXE-файла программы "ООО Евроблок"
- Встраивает иконку в EXE
- Автоматически создаёт ярлык на рабочем столе
- Копирует папку assets рядом с EXE

Использование:
    python build_exe.py

После сборки:
    1. EXE-файл будет в папке dist/ с вашей иконкой
    2. Ярлык "Евроблок.lnk" будет создан на рабочем столе
    3. Папка assets/ скопируется рядом с EXE
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
    """
    Проверить наличие папки assets и файлов.
    
    Returns:
        tuple: (has_logo, has_icon)
    """
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
        # Скрытые импорты
        '--hidden-import=reportlab',
        '--hidden-import=reportlab.lib',
        '--hidden-import=reportlab.lib.pagesizes',
        '--hidden-import=reportlab.lib.colors',
        '--hidden-import=reportlab.lib.units',
        '--hidden-import=reportlab.platypus',
        '--hidden-import=reportlab.pdfbase',
        '--hidden-import=reportlab.pdfbase.ttfonts',
        '--hidden-import=reportlab.lib.styles',
        
        '--hidden-import=database',
        '--hidden-import=database.connection',
        '--hidden-import=database.repositories',
        '--hidden-import=database.cache',
        '--hidden-import=database.notifications',
        '--hidden-import=database.locking',
        
        '--hidden-import=ui',
        '--hidden-import=ui.main_window',
        '--hidden-import=ui.settings_panel',
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
        
        '--hidden-import=ui.widgets',
        '--hidden-import=ui.widgets.date_entry',
        '--hidden-import=ui.widgets.combobox_autocomplete',
        '--hidden-import=ui.widgets.silo_canvas',
        
        '--hidden-import=config',
        '--hidden-import=config.settings',
        
        '--hidden-import=utils',
        '--hidden-import=utils.resources',
        '--hidden-import=utils.performance_logger',
        '--hidden-import=utils.data_cache',
        
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
            
            # Создаём ярлык на рабочем столе
            create_shortcut(exe_path)
            
            print()
            print("=" * 70)
            print("ГОТОВО!")
            print("=" * 70)
            print()
            print("✓ EXE-файл создан с вашей иконкой")
            print("✓ Папка assets/ скопирована рядом с EXE")
            print("✓ Ярлык создан на рабочем столе")
            print()
            print("Проверьте:")
            print("  1. Откройте папку dist/")
            print("  2. Убедитесь, что Евроблок.exe имеет вашу иконку")
            print("  3. Проверьте ярлык на рабочем столе")
            print("  4. Запустите программу")
            print()
            print("Для многопользовательской работы:")
            print("  1. Скопируйте папку dist/ на сервер")
            print("  2. Создайте общий доступ")
            print("  3. На клиентских ПК создайте ярлыки")
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
    """
    Создать ярлык на рабочем столе.
    Иконка берётся из EXE (встроена при сборке).
    
    Args:
        exe_path: путь к EXE-файлу
    """
    desktop = get_desktop_path()
    shortcut_path = os.path.join(desktop, 'Евроблок.lnk')
    
    # Иконка встроена в EXE, используем её
    icon_location = f"{exe_path},0"
    
    # Экранируем обратные слеши для PowerShell
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

БЫСТРЫЙ СТАРТ:

1. Запустите Евроблок.exe двойным кликом.

2. При первом запуске:
   - Автоматически установится библиотека reportlab (нужен интернет)
   - Создастся база данных euroblock.db в той же папке

3. Ярлык для запуска находится на рабочем столе.

================================================================================

СТРУКТУРА ПАПОК:

C:\\Euroblock\\
├── Евроблок.exe          ← программа (с вашей иконкой)
├── euroblock.db          ← база данных (создаётся автоматически)
── README.txt            ← этот файл
└── assets\\
    ├── logo.png          ← логотип компании (отображается в программе)
    └── icon.ico          ← иконка программы (встроена в EXE)

================================================================================

МНОГОПОЛЬЗОВАТЕЛЬСКАЯ РАБОТА:

1. Скопируйте папку с программой на сервер
2. Создайте общий доступ с правами на чтение/запись
3. На клиентских ПК создайте ярлыки на общую папку
4. Все пользователи работают с одной базой данных

================================================================================

ТРЕБОВАНИЯ:

- Windows 7/8/10/11
- Интернет (только для первичной установки reportlab)
- Свободное место: минимум 100 МБ

================================================================================

РЕШЕНИЕ ПРОБЛЕМ:

ПРОБЛЕМА: Не устанавливается reportlab
РЕШЕНИЕ: Запустите от имени администратора или: pip install reportlab

ПРОБЛЕМА: Логотип не отображается
РЕШЕНИЕ: Проверьте, что assets/logo.png находится рядом с EXE

ПРОБЛЕМА: База данных повреждена
РЕШЕНИЕ: Программа создаст бэкап в папке backups/ и новую БД

ПРОБЛЕМА: Иконка не отображается
РЕШЕНИЕ: 
  1. Перезапустите Проводник (Ctrl+Shift+Esc → Проводник → Перезапустить)
  2. Или очистите кэш иконок: ie4uinit.exe -show

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
        print()
    else:
        print()
        print("✗ Сборка не удалась или отменена.")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)