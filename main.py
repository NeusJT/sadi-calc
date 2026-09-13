import math
import re
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.core.window import Window
from engine import CompartmentEngine

Window.size = (400, 760)

class CardLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup = True
        self.size_hint_y = None
        self.halign = 'left'
        self.valign = 'top'
        self.bind(width=self._update_text_size, texture_size=self._update_height)

    def _update_text_size(self, instance, value):
        self.text_size = (max(50, instance.width - 20), None)

    def _update_height(self, instance, value):
        if isinstance(value, (list, tuple)) and len(value) > 1:
            self.height = value[1] + 20
        else:
            self.height = 140


class SadiPreviewWidget(Widget):
    def __init__(self, room_l: float, room_w: float, qtd: int, distrib_str: str = "", espacamento_str: str = "", **kwargs):
        super().__init__(**kwargs)
        self.room_l = max(float(room_l or 1.0), 1.0)
        self.room_w = max(float(room_w or 1.0), 1.0)
        self.qtd = max(int(qtd or 0), 0)
        self.distrib_str = distrib_str
        self.espacamento_str = espacamento_str
        self.size_hint_y = None
        self.height = 200
        self.bind(pos=self.redraw, size=self.redraw)

    def _get_grid_dims(self):
        if self.distrib_str:
            match = re.search(r'(\d+)\s*[xX]\s*(\d+)', self.distrib_str)
            if match:
                c, r = int(match.group(1)), int(match.group(2))
                return c, r
        cols = max(1, round(math.sqrt(self.qtd * (self.room_l / self.room_w))))
        rows = max(1, math.ceil(self.qtd / cols))
        return cols, rows

    def _get_coverage_radius_meters(self):
        # Tenta extrair o passo/espaçamento em metros (ex: 8.33 m x 5.0 m)
        if self.espacamento_str:
            matches = re.findall(r'(\d+(?:\.\d+)?)', self.espacamento_str)
            if len(matches) >= 2:
                sx = float(matches[0])
                sy = float(matches[1])
                # Raio de cobertura efetivo aproximado da diagonal/passo da célula (EN 54)
                return max(sx, sy) * 0.707
        # Fallback padrão EN 54 (ex: raio óculo ~7.5m ou proporcional)
        return min(7.5, (self.room_l * self.room_w)**0.5 / 2.5)

    def redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            margin = 30
            avail_w = max(self.width - 2 * margin, 50)
            avail_h = max(self.height - 2 * margin, 50)
            
            scale = min(avail_w / self.room_l, avail_h / self.room_w)
            draw_w = self.room_l * scale
            draw_h = self.room_w * scale
            
            offset_x = self.x + (self.width - draw_w) / 2
            offset_y = self.y + (self.height - draw_h) / 2
            
            # Fundo subtil da sala
            Color(0.12, 0.14, 0.18, 1)
            Rectangle(pos=(offset_x, offset_y), size=(draw_w, draw_h))
            
            # Contorno do compartimento
            Color(0.4, 0.5, 0.6, 1)
            Line(rectangle=(offset_x, offset_y, draw_w, draw_h), width=1.5)
            
            if self.qtd > 0:
                cols, rows = self._get_grid_dims()
                cov_radius_m = self._get_coverage_radius_meters()
                cov_radius_px = cov_radius_m * scale
                
                step_x = draw_w / cols
                step_y = draw_h / rows
                
                count = 0
                points_coords = []
                for r in range(rows):
                    for c in range(cols):
                        if count >= self.qtd:
                            break
                        px = offset_x + step_x * (c + 0.5)
                        py = offset_y + step_y * (r + 0.5)
                        points_coords.append((px, py))
                        count += 1

                # 1. Desenhar a área de cobertura teórica (círculo semi-transparente + contorno suave)
                for (px, py) in points_coords:
                    # Preenchimento translúcido da área de cobertura
                    Color(0.18, 0.8, 0.44, 0.14)
                    Ellipse(pos=(px - cov_radius_px, py - cov_radius_px), size=(cov_radius_px * 2, cov_radius_px * 2))
                    
                    # Linha de contorno do raio de cobertura
                    Color(0.18, 0.8, 0.44, 0.35)
                    Line(circle=(px, py, cov_radius_px), width=1)

                # 2. Desenhar o centro do detetor por cima
                for (px, py) in points_coords:
                    Color(0.18, 0.9, 0.5, 1)
                    dot_size = 10
                    Ellipse(pos=(px - dot_size / 2, py - dot_size / 2), size=(dot_size, dot_size))


class ScreenInput(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main = BoxLayout(orientation='vertical', padding=12, spacing=8)
        
        main.add_widget(Label(
            text="[b]SADI v1.0[/b] — Dimensionamento SCIE/EN 54\n[size=11]Desenvolvido por Jhonny Tavares[/size]",
            markup=True, size_hint_y=None, height=52, color=(0.2, 0.6, 1.0, 1)
        ))

        scroll = ScrollView(size_hint=(1, 1))
        form = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None)
        form.bind(minimum_height=form.setter('height'))

        grid = GridLayout(cols=2, spacing=8, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        def add_field(label_text, default_val="0.0", filter_type="float"):
            grid.add_widget(Label(text=label_text, size_hint_y=None, height=38))
            ti = TextInput(text=default_val, multiline=False, input_filter=filter_type, size_hint_y=None, height=38)
            grid.add_widget(ti)
            return ti

        self.in_len = add_field("Comprimento (m):", default_val="25.0")
        self.in_wid = add_field("Largura (m):", default_val="10.0")
        self.in_hcenter = add_field("Alt. Centro / Pico (m):", default_val="8.55")
        self.in_hleft = add_field("Alt. Esquerda (m):", default_val="6.10")
        self.in_hright = add_field("Alt. Direita (m):", default_val="6.55")
        self.in_exits = add_field("N.º Saídas Fuga:", default_val="1", filter_type="int")

        form.add_widget(grid)

        form.add_widget(Label(text="Ambiente / Perturbações:", size_hint_y=None, height=24, halign='left'))
        self.spin_env = Spinner(
            text="Normal / Limpo",
            values=(
                "Normal / Limpo",
                "Fumos / Poeiras de Processo",
                "Vapores / Humidade Elevada",
                "Altas Temperaturas / Variações Rápidas",
                "Ambiente Crítico / Salas Técnicas / Data Centers"
            ),
            size_hint_y=None, height=40
        )
        form.add_widget(self.spin_env)

        btn_calc = Button(
            text="CALCULAR E DETETAR TETO AUTOMATICAMENTE",
            size_hint_y=None, height=50,
            background_color=(0.15, 0.65, 0.35, 1), bold=True
        )
        btn_calc.bind(on_release=self.run_eval)
        form.add_widget(btn_calc)

        self.lbl_err = Label(text="", color=(1, 0.3, 0.3, 1), size_hint_y=None, height=28)
        form.add_widget(self.lbl_err)

        scroll.add_widget(form)
        main.add_widget(scroll)
        self.add_widget(main)

    def _safe_float(self, text, default=0.0):
        try:
            return float(text.replace(',', '.')) if text and text.strip() else default
        except ValueError:
            return default

    def _safe_int(self, text, default=1):
        try:
            return int(text.strip()) if text and text.strip() else default
        except ValueError:
            return default

    def run_eval(self, instance):
        try:
            l = self._safe_float(self.in_len.text, 0.0)
            w = self._safe_float(self.in_wid.text, 0.0)
            hc = self._safe_float(self.in_hcenter.text, 0.0)
            hl = self._safe_float(self.in_hleft.text, 0.0)
            hr = self._safe_float(self.in_hright.text, 0.0)
            exits = self._safe_int(self.in_exits.text, 1)

            env_txt = self.spin_env.text
            env_key = "normal"
            if "Poeiras" in env_txt: env_key = "smoke_dust"
            elif "Humidade" in env_txt: env_key = "steam_humidity"
            elif "Altas" in env_txt: env_key = "high_temp"
            elif "Data Centers" in env_txt: env_key = "data_center"

            res = CompartmentEngine.evaluate_automatic(l, w, hc, hl, hr, env_key, exits)
            if isinstance(res, dict) and "error" in res:
                self.lbl_err.text = res["error"]
                return

            screen_res = self.manager.get_screen('results')
            screen_res.show_data(res, dim_l=l, dim_w=w)
            self.manager.transition = SlideTransition(direction='left')
            self.manager.current = 'results'
            self.lbl_err.text = ""
        except Exception as e:
            self.lbl_err.text = f"Erro no processamento: {str(e)}"


class ScreenResult(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        top_bar = BoxLayout(size_hint_y=None, height=42, spacing=10)
        btn_back = Button(text="< Voltar", size_hint_x=0.25, background_color=(0.4, 0.4, 0.4, 1))
        btn_back.bind(on_release=self.go_back)
        top_bar.add_widget(btn_back)
        top_bar.add_widget(Label(text="[b]Resultados de Viabilidade SADI[/b]", markup=True))
        layout.add_widget(top_bar)

        scroll = ScrollView(size_hint=(1, 1))
        self.box_content = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        self.box_content.bind(minimum_height=self.box_content.setter('height'))
        scroll.add_widget(self.box_content)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'inputs'

    def show_data(self, res: dict, dim_l: float = 25.0, dim_w: float = 10.0):
        self.box_content.clear_widgets()
        
        mcp_data = res.get('mcp') or {}
        summary = (
            f"[b]Área Calculada:[/b] {res.get('area', 0)} m²\n"
            f"[color=f39c12][b]Geometria Obtida:[/b] {res.get('roof_classification', 'N/A')}[/color]\n"
            f"[color=3498db][b]Botoneiras Manuais (EN 54-11):[/b] {mcp_data.get('regra', 'N/A')}[/color]"
        )
        self.box_content.add_widget(CardLabel(text=summary))

        room_l = res.get('dim_l', dim_l) or 25.0
        room_w = res.get('dim_w', dim_w) or 10.0

        for idx, opt in enumerate(res.get('viable_options', []), 1):
            distrib_txt = opt.get('distribuicao', '')
            espacamento_txt = opt.get('espacamento', '')
            card_txt = (
                f"[color=2ecc71][b]OPÇÃO VIÁVEL #{idx}: {opt.get('tecnologia', '').upper()}[/b][/color]\n"
                f"• [b]Viabilidade Técnica:[/b] {opt.get('viabilidade', '')}\n"
                f"• [b]Quantidade / Escopo:[/b] [size=15][b]{opt.get('qtd', 0)} un. / blocos[/b][/size]\n"
                f"• [b]Distribuição / Geometria:[/b] {distrib_txt}\n"
                f"• [b]Posição 1.º Ponto:[/b] {opt.get('primeiro_ponto', '')}\n"
                f"• [b]Passo / Espaçamento:[/b] {espacamento_txt}\n"
                f"• [b]Regras / Cumeeira:[/b] [i]{opt.get('regras_geometria', '')}[/i]"
            )
            self.box_content.add_widget(CardLabel(text=card_txt))
            self.box_content.add_widget(SadiPreviewWidget(
                room_l=room_l, 
                room_w=room_w, 
                qtd=opt.get('qtd', 0),
                distrib_str=distrib_txt,
                espacamento_str=espacamento_txt
            ))
        
        self.box_content.add_widget(Label(
            text="[size=10]SADI v1.0 — Jhonny Tavares[/size]",
            markup=True, size_hint_y=None, height=25, color=(0.5, 0.5, 0.5, 1)
        ))


class SadiAutoApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ScreenInput(name='inputs'))
        sm.add_widget(ScreenResult(name='results'))
        return sm


if __name__ == "__main__":
    SadiAutoApp().run()