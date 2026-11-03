"""
Виджет визуализации силосов цемента.
Силоса отображаются "вверх ногами" — крыша (конус) внизу, корпус сверху.
Заполнение идёт от дна (крыши) вверх.
[ИЗМЕНЕНО] Уменьшен hardcoded шрифт для вместимости.
"""
import tkinter as tk
from config.settings import COLORS, FONTS, SIZES


class SiloCanvas(tk.Canvas):
    """Canvas для отображения силосов цемента"""
    def __init__(self, parent, silos_data, balances, **kwargs):
        self.silos_data = silos_data
        self.balances = balances
        self.silo_width = SIZES['silo_width']
        self.silo_height = SIZES['silo_height']
        self.silo_spacing = SIZES['silo_spacing']
        self.top_margin = SIZES['silo_top_margin']
        
        num_silos = len(silos_data)
        if num_silos == 0:
            width = 400
        else:
            width = num_silos * (self.silo_width + self.silo_spacing) + self.silo_spacing
        
        height = self.top_margin + self.silo_height + 60
        
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS['panel_bg'],
            highlightthickness=0,
            **kwargs
        )
        
        self._draw_silos()
    
    def update_data(self, silos_data, balances):
        self.silos_data = silos_data
        self.balances = balances
        self.delete('all')
        
        num_silos = len(silos_data)
        if num_silos == 0:
            width = 400
        else:
            width = num_silos * (self.silo_width + self.silo_spacing) + self.silo_spacing
        
        self.config(width=width)
        self._draw_silos()
    
    def _draw_silos(self):
        if not self.silos_data:
            self.create_text(
                200, (self.top_margin + self.silo_height) // 2,
                text="Силоса не настроены. Добавьте их в Настройках.",
                font=FONTS['work_area'],
                fill=COLORS['work_area_text']
            )
            return
        
        x_offset = self.silo_spacing
        y_top = self.top_margin
        
        for name, capacity_tn in self.silos_data:
            self._draw_single_silo(x_offset, y_top, name, capacity_tn)
            x_offset += self.silo_width + self.silo_spacing
    
    def _draw_single_silo(self, x, y, name, capacity_tn):
        w = self.silo_width
        h = self.silo_height
        
        current_kg = self.balances.get(name, 0)
        
        if capacity_tn is None or capacity_tn <= 0:
            max_kg = 1
            capacity_display = "не указан"
        else:
            max_kg = capacity_tn * 1000
            capacity_display = f"{self._format_number(capacity_tn)} т"
        
        fill_ratio = current_kg / max_kg if max_kg > 0 else 0
        
        if fill_ratio < 0:
            fill_ratio = 0
        if fill_ratio > 1.2:
            fill_ratio = 1.2
        
        if fill_ratio > 1.0:
            fill_color = COLORS['silo_fill_critical']
        elif fill_ratio > 0.8:
            fill_color = COLORS['silo_fill_warning']
        else:
            fill_color = COLORS['silo_fill']
        
        roof_height = 25
        body_top = y
        body_bottom = y + h - roof_height
        roof_top = body_bottom
        roof_bottom = y + h
        
        self.create_rectangle(
            x, body_top, x + w, body_bottom,
            fill=COLORS['silo_empty'],
            outline=COLORS['silo_border'],
            width=2
        )
        
        roof_points = [
            x, roof_top,
            x + w, roof_top,
            x + w // 2, roof_bottom
        ]
        self.create_polygon(
            roof_points,
            fill=COLORS['silo_empty'],
            outline=COLORS['silo_border'],
            width=2
        )
        
        if current_kg > 0 and max_kg > 0:
            body_height = body_bottom - body_top
            fill_height = min(body_height, body_height * min(fill_ratio, 1.0))
            fill_top = body_bottom - fill_height
            
            self.create_rectangle(
                x + 2, fill_top, x + w - 2, body_bottom - 1,
                fill=fill_color,
                outline=''
            )
            
            if fill_ratio > 1.0:
                overflow_height = min(15, (fill_ratio - 1.0) * body_height)
                self.create_rectangle(
                    x + 2, body_top, x + w - 2, body_top + overflow_height,
                    fill=COLORS['silo_fill_critical'],
                    outline=''
                )
        
        self.create_text(
            x + w // 2, y - 8,
            text=name,
            font=FONTS['silo_label'],
            fill=COLORS['title_text'],
            anchor='s'
        )
        
        current_display = self._format_kg(current_kg)
        self.create_text(
            x + w // 2, y + h + 10,
            text=f"{current_display}",
            font=FONTS['silo_value'],
            fill=COLORS['title_text'],
            anchor='n'
        )
        
        # [ИЗМЕНЕНО] Уменьшен шрифт с 9 до 7
        self.create_text(
            x + w // 2, y + h + 28,
            text=f"макс: {capacity_display}",
            font=('Arial', 7),  # было ('Arial', 9)
            fill=COLORS['work_area_text'],
            anchor='n'
        )
    
    def _format_kg(self, kg):
        if kg is None:
            return "0 кг"
        return f"{self._format_number(kg)} кг"
    
    def _format_number(self, value):
        if value is None:
            return "0"
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            else:
                return f"{num:g}"
        except (ValueError, TypeError):
            return str(value)