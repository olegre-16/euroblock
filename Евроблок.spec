# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=['reportlab', 'reportlab.lib', 'reportlab.lib.pagesizes', 'reportlab.lib.colors', 'reportlab.lib.units', 'reportlab.platypus', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts', 'reportlab.lib.styles', 'config', 'config.settings', 'client_config', 'database', 'database.connection', 'database.repositories', 'database.cache', 'database.notifications', 'database.locking', 'ui', 'ui.main_window', 'ui.base_window', 'ui.settings_panel', 'ui.windows', 'ui.windows.cement_receipt_window', 'ui.windows.production_window', 'ui.windows.reserved_products_window', 'ui.windows.sales_window', 'ui.windows.cash_window', 'ui.windows.general_expenses_window', 'ui.windows.cement_report_window', 'ui.windows.expenses_report_window', 'ui.windows.sales_report_window', 'ui.windows.production_report_window', 'ui.windows.inert_materials_window', 'ui.windows.base_dictionary_window', 'ui.windows.payment_type_window', 'ui.windows.materials_window', 'ui.windows.purposes_window', 'ui.windows.equipment_window', 'ui.windows.payers_window', 'ui.windows.customers_window', 'ui.windows.suppliers_window', 'ui.windows.products_window', 'ui.windows.cement_silos_window', 'ui.windows.colors_window', 'ui.windows.setup_wizard', 'ui.widgets', 'ui.widgets.date_entry', 'ui.widgets.combobox_autocomplete', 'ui.widgets.silo_canvas', 'ui.widgets.custom_messagebox', 'ui.widgets.progress_dialog', 'ui.widgets.paginated_treeview', 'utils', 'utils.resources', 'utils.performance_logger', 'utils.data_cache', 'utils.excel_reader', 'utils.pdf_utils', 'utils.async_operations'],
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
