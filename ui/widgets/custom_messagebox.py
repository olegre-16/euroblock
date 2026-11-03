"""
Кастомные messagebox с шрифтом основного текста программы.
Заменяют стандартный tkinter.messagebox для единообразия оформления.
[ИЗМЕНЕНО] Уменьшен hardcoded шрифт иконки.
"""
import tkinter as tk
from config.settings import COLORS, FONTS, SIZES


class CustomMessageBox:
    """Кастомные диалоги сообщений"""
    
    @staticmethod
    def _show_dialog(parent, title, message, buttons, icon_type, icon_color, bg_color):
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=bg_color)
        dialog.resizable(False, False)
        
        dialog.transient(parent)
        dialog.grab_set()
        
        result = [None]
        
        dialog.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        dialog_w = SIZES['messagebox_width']
        dialog_h = 200
        
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        
        dialog.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        
        icons = {
            'info': '✓',
            'warning': '⚠',
            'error': '✗',
            'question': '?'
        }
        
        # [ИЗМЕНЕНО] Уменьшен шрифт иконки с 36 до 34
        icon_label = tk.Label(
            dialog,
            text=icons.get(icon_type, '•'),
            font=('Arial', 34, 'bold'),  # было ('Arial', 36, 'bold')
            bg=bg_color,
            fg=icon_color
        )
        icon_label.pack(pady=(15, 5))
        
        title_label = tk.Label(
            dialog,
            text=title,
            font=FONTS['messagebox_title'],
            bg=bg_color,
            fg=COLORS['title_text']
        )
        title_label.pack(pady=(0, 5))
        
        msg_label = tk.Label(
            dialog,
            text=message,
            font=FONTS['messagebox_text'],
            bg=bg_color,
            fg=COLORS['title_text'],
            wraplength=SIZES['messagebox_width'] - 40,
            justify='center'
        )
        msg_label.pack(pady=(0, 15), padx=20)
        
        btn_frame = tk.Frame(dialog, bg=bg_color)
        btn_frame.pack(pady=(0, 15))
        
        def on_button(value):
            result[0] = value
            dialog.destroy()
        
        for text, value, btn_bg, btn_fg in buttons:
            btn = tk.Button(
                btn_frame,
                text=text,
                font=FONTS['menu'],
                bg=btn_bg,
                fg=btn_fg,
                relief=tk.FLAT,
                padx=15,
                pady=5,
                cursor='hand2',
                command=lambda v=value: on_button(v)
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        dialog.bind('<Escape>', lambda e: on_button(buttons[-1][1] if len(buttons) > 1 else buttons[0][1]))
        dialog.protocol("WM_DELETE_WINDOW", lambda: on_button(buttons[-1][1] if len(buttons) > 1 else buttons[0][1]))
        
        dialog.wait_window()
        return result[0]
    
    @staticmethod
    def showinfo(parent, title, message):
        buttons = [("OK", True, COLORS['button_primary'], COLORS['button_text'])]
        return CustomMessageBox._show_dialog(
            parent, title, message, buttons,
            'info', COLORS['msg_icon_info'], COLORS['msg_info_bg']
        )
    
    @staticmethod
    def showwarning(parent, title, message):
        buttons = [("OK", True, COLORS['button_primary'], COLORS['button_text'])]
        return CustomMessageBox._show_dialog(
            parent, title, message, buttons,
            'warning', COLORS['msg_icon_warning'], COLORS['msg_warning_bg']
        )
    
    @staticmethod
    def showerror(parent, title, message):
        buttons = [("OK", True, COLORS['button_exit'], COLORS['button_text'])]
        return CustomMessageBox._show_dialog(
            parent, title, message, buttons,
            'error', COLORS['msg_icon_error'], COLORS['msg_error_bg']
        )
    
    @staticmethod
    def askyesno(parent, title, message):
        buttons = [
            ("Да", True, COLORS['button_primary'], COLORS['button_text']),
            ("Нет", False, COLORS['button_settings'], COLORS['button_text'])
        ]
        return CustomMessageBox._show_dialog(
            parent, title, message, buttons,
            'question', COLORS['msg_icon_question'], COLORS['msg_question_bg']
        )
    
    @staticmethod
    def askokcancel(parent, title, message):
        buttons = [
            ("OK", True, COLORS['button_primary'], COLORS['button_text']),
            ("Отмена", False, COLORS['button_settings'], COLORS['button_text'])
        ]
        return CustomMessageBox._show_dialog(
            parent, title, message, buttons,
            'question', COLORS['msg_icon_question'], COLORS['msg_question_bg']
        )