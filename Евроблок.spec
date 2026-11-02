# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['reportlab', 'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.colors', 'reportlab.lib.units', 'reportlab.platypus', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts', 'reportlab.lib.styles', 'database', 'database.connection', 'database.repositories', 'database.cache', 'database.notifications', 'database.locking', 'ui', 'ui.main_window', 'ui.settings_panel', 'ui.windows', 'ui.windows.cement_receipt_window', 'ui.windows.production_window', 'ui.windows.reserved_products_window', 'ui.windows.sales_window', 'ui.windows.cash_window', 'ui.windows.general_expenses_window', 'ui.windows.cement_report_window', 'ui.windows.expenses_report_window', 'ui.windows.sales_report_window', 'ui.windows.production_report_window', 'ui.windows.inert_materials_window', 'ui.widgets', 'ui.widgets.date_entry', 'ui.widgets.combobox_autocomplete', 'ui.widgets.silo_canvas', 'config', 'config.settings', 'utils', 'utils.resources', 'utils.performance_logger', 'utils.data_cache'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Евроблок',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)
