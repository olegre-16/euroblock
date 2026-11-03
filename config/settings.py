"""
Настройки оформления программы "ООО Евроблок"
[ИЗМЕНЕНО] Все шрифты уменьшены на 2 пункта.
Уменьшены отступы полей и кнопок.
"""

# ============================================================================
# ЦВЕТА
# ============================================================================
COLORS = {
    'background': '#f0f0f0',
    'panel_bg': '#ffffff',
    'title_text': '#2c3e50',
    'subtitle_text': '#7f8c8d',
    'button_primary': '#3498db',
    'button_primary_hover': '#2980b9',
    'button_settings': '#95a5a6',
    'button_settings_hover': '#7f8c8d',
    'button_exit': '#e74c3c',
    'button_exit_hover': '#c0392b',
    'button_import': '#a8d8a8',
    'button_import_hover': '#7bc97b',
    'button_text': '#ffffff',
    'button_disabled': '#bdc3c7',
    'work_area_text': '#95a5a6',
    'table_heading_bg': '#2471a3',
    'table_heading_fg': '#000000',
    'table_heading_hover': '#1a5276',
    'correction_bg': '#ffd6d6',
    'correction_bg_selected': '#ffb3b3',
    'silo_fill': '#5dade2',
    'silo_fill_warning': '#f39c12',
    'silo_fill_critical': '#e74c3c',
    'silo_border': '#2c3e50',
    'silo_empty': '#ecf0f1',
    'calendar_today': '#e8e8e8',
    'calendar_today_fg': '#2c3e50',
    'calendar_selected': '#2980b9',
    'calendar_weekend': '#e74c3c',
    # Цвета для кастомных messagebox
    'msg_icon_info': '#27ae60',
    'msg_icon_warning': '#f39c12',
    'msg_icon_error': '#e74c3c',
    'msg_icon_question': '#3498db',
    'msg_info_bg': '#ffffff',
    'msg_warning_bg': '#fff9e6',
    'msg_error_bg': '#fdecea',
    'msg_question_bg': '#e8f4fd',
}

# ============================================================================
# ШРИФТЫ (все уменьшены на 2 пункта)
# ============================================================================
FONTS = {
    'title': ('Arial', 22, 'bold'),           # было 24
    'subtitle': ('Arial', 12),                # было 14
    'menu': ('Arial', 9),                     # было 11
    'field': ('Arial', 9),                    # было 11
    'work_area': ('Arial', 9),                # было 11
    'section_title': ('Arial', 16, 'bold'),   # было 18
    'table_heading': ('Arial', 9, 'bold'),    # было 11
    'table_cell': ('Arial', 9),               # было 11
    'silo_label': ('Arial', 9, 'bold'),       # было 11
    'silo_value': ('Arial', 9, 'bold'),       # было 11
    'calendar_day': ('Arial', 9),             # было 11
    'calendar_header': ('Arial', 9, 'bold'),  # было 11
    'hint': ('Arial', 8),                     # было 10
    'messagebox_title': ('Arial', 12, 'bold'),  # было 14
    'messagebox_text': ('Arial', 10),           # было 12
}

# ============================================================================
# ОТСТУПЫ (уменьшены)
# ============================================================================
PADDING = {
    'main': 20,
    'button_x': 8,              # было 10
    'button_y': 4,              # было 6
    'button_spacing': 3,
    'exit_spacing_top': 15,
    'title_subtitle': 5,
}

# ============================================================================
# РАЗМЕРЫ (уменьшены)
# ============================================================================
SIZES = {
    'button_width_extra': 0,
    'panel_border': 1,
    'silo_width': 80,
    'silo_height': 150,
    'silo_spacing': 20,
    'silo_top_margin': 30,
    'field_ipady': 2,           # было 4
    'messagebox_width': 380,
}