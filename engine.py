import math

class CompartmentEngine:
    @staticmethod
    def evaluate_automatic(length: float, width: float, 
                           h_center: float, h_left: float, h_right: float, 
                           env_key: str, num_exits: int) -> dict:
        
        if length <= 0 or width <= 0 or h_center <= 0:
            return {"error": "Dimensões em planta e altura central devem ser superiores a 0."}

        area = length * width
        tol = 0.05  # tolerância de 5cm para igualdade de cotas

        # Dedução automática do tipo de teto e ângulo
        diff_sides = abs(h_left - h_right)
        avg_walls = (h_left + h_right) / 2.0

        if diff_sides <= tol and abs(h_center - avg_walls) <= tol:
            roof_type_desc = "Teto Plano / Horizontal"
            slope_deg = 0.0
            is_gabled = False
            effective_h_for_rules = h_center
        elif diff_sides <= tol and h_center > avg_walls:
            h_beirado = avg_walls
            span_half = width / 2.0
            slope_deg = math.degrees(math.atan((h_center - h_beirado) / span_half))
            roof_type_desc = f"Teto de Duas Águas (Simétrico) - Ângulo {round(slope_deg, 1)}º"
            is_gabled = True
            effective_h_for_rules = h_center
        else:
            max_h = max(h_center, h_left, h_right)
            min_h = min(h_left, h_right, h_center if h_center < avg_walls else avg_walls)
            slope_deg = math.degrees(math.atan(abs(h_left - h_right) / width))
            roof_type_desc = f"Teto Inclinado / Assimétrico - Ângulo efetivo {round(slope_deg, 1)}º"
            is_gabled = slope_deg > 20.0
            effective_h_for_rules = max_h

        # Majoração EN 54-14 se inclinação > 20º (+1% por grau até 25% max)
        pitch_factor = min(1.25, 1.0 + max(0.0, (slope_deg - 20.0)) * 0.01) if slope_deg > 20.0 else 1.0

        # Enquadramento Legal Botoneiras (Art. 119.º RT-SCIE / EN 54-11)
        diag = math.hypot(length, width)
        total_mcp = max(num_exits, math.ceil(diag / 30.0))
        mcp_info = {
            "qtd": total_mcp,
            "regra": f"{total_mcp} un. (1 por saída ({num_exits} indicadas), percurso máx. <= 30 m a ~1,2 m do solo)."
        }

        viable_list = []
        h_max_ref = effective_h_for_rules
        ridge_note = "OBRIGATÓRIO: Linha central de detetores na cumeeira/vértice (<= 0,15 m a 0,6 m do ponto mais alto)." if is_gabled else "Teto plano / sem cumeeira central."

        # 1. Ótico Pontual
        if h_max_ref <= 12.0 and env_key in ["normal", "data_center"]:
            r_max = (7.5 if h_max_ref <= 6.0 else 6.5) * pitch_factor
            a_max = (80.0 if h_max_ref <= 6.0 else 60.0) * pitch_factor
            nx, ny, qty, dx, dy, wx, wy = CompartmentEngine._grid_calc(length, width, r_max, a_max, area)
            viable_list.append({
                "tecnologia": "Detetores Óticos Pontuais de Fumo (EN 54-7)",
                "viabilidade": "ALTA (Ambientes limpos, H <= 12m)",
                "qtd": qty,
                "distribuicao": f"Grelha {nx}x{ny} un. {'+ fiada central de cumeeira' if is_gabled else ''}.",
                "primeiro_ponto": f"1.º a {wx} m fundo, {wy} m lateral.",
                "espacamento": f"Passo: {dx} m x {dy} m.",
                "regras_geometria": f"Afastamento paredes >= 0,5 m. {ridge_note}"
            })

        # 2. Térmico Pontual
        if h_max_ref <= 9.0:
            r_th = (4.4 if h_max_ref <= 6.0 else 3.5) * pitch_factor
            a_th = 30.0 * pitch_factor
            nx, ny, qty, dx, dy, wx, wy = CompartmentEngine._grid_calc(length, width, r_th, a_th, area)
            viable_list.append({
                "tecnologia": "Detetores Térmicos / Termovelocimétricos (EN 54-5)",
                "viabilidade": "ALTA (Poeiras, vapores, humidade)",
                "qtd": qty,
                "distribuicao": f"Grelha {nx}x{ny} un. {'+ fiada térmica cumeeira' if is_gabled else ''}.",
                "primeiro_ponto": f"1.º a {wx} m fundo, {wy} m lateral.",
                "espacamento": f"Passo: {dx} m x {dy} m.",
                "regras_geometria": f"Afastamento paredes >= 0,5 m. {ridge_note}"
            })

        # 3. Multicritério
        if h_max_ref <= 12.0:
            r_mc = 7.5 * pitch_factor
            a_mc = 60.0 * pitch_factor
            nx, ny, qty, dx, dy, wx, wy = CompartmentEngine._grid_calc(length, width, r_mc, a_mc, area)
            viable_list.append({
                "tecnologia": "Detetores Multissensoriais Ótico-Térmicos",
                "viabilidade": "MUITO ALTA (Versátil anti-falso alarme)",
                "qtd": qty,
                "distribuicao": f"Grelha {nx}x{ny} un.",
                "primeiro_ponto": f"1.º a {wx} m fundo, {wy} m lateral.",
                "espacamento": f"Passo: {dx} m x {dy} m.",
                "regras_geometria": f"Afastamento paredes >= 0,5 m. {ridge_note}"
            })

        # 4. Barreira Linear (Beam)
        if h_max_ref >= 4.0 and h_max_ref <= 25.0 and max(length, width) >= 8.0:
            beams_needed = max(1, math.ceil(min(length, width) / 12.4))
            viable_list.append({
                "tecnologia": "Barreiras Lineares Óticas de Fumo (Beam - EN 54-12)",
                "viabilidade": "ALTA (Grandes volumes / tetos altos 4m-25m)",
                "qtd": beams_needed,
                "distribuicao": f"{beams_needed} feixe(s) longitudinal(ais) ao longo de {max(length, width)} m.",
                "primeiro_ponto": "Transmissor/Recetor em paredes opostas de topo.",
                "espacamento": "Largura efetiva de 15 m por feixe (7,5 m para cada lado).",
                "regras_geometria": f"Nos 10% superiores do pé-direito. {ridge_note}"
            })

        # 5. Aspiração ASD
        if h_max_ref <= 25.0:
            furos_calc = max(1, math.ceil(area / 40.0))
            viable_list.append({
                "tecnologia": "Sistema de Aspiração de Fumos (ASD Classe A/B - EN 54-20)",
                "viabilidade": "MUITO ALTA / CRÍTICA (Data centers, grandes alturas/acesso difícil)",
                "qtd": 1,
                "distribuicao": f"1 Central + rede capilar ({furos_calc} furos estimados).",
                "primeiro_ponto": "1.º furo a <= 4,5 m da parede de fundo/cumeeira.",
                "espacamento": "Orifícios a cada 6,0 m - 9,0 m na tubagem.",
                "regras_geometria": f"Tubagem ao longo do teto/cumeeira. {ridge_note} Manutenção ao solo."
            })

        return {
            "area": round(area, 2),
            "roof_classification": roof_type_desc,
            "slope_deg": round(slope_deg, 1),
            "pitch_factor": round(pitch_factor, 2),
            "is_gabled": is_gabled,
            "mcp": mcp_info,
            "viable_options": viable_list
        }

    @staticmethod
    def _grid_calc(l, w, r_max, a_max, area):
        d_side = r_max * math.sqrt(2.0)
        nx = max(1, math.ceil(l / d_side))
        ny = max(1, math.ceil(w / d_side))
        min_area_qty = math.ceil(area / a_max)
        while (nx * ny) < min_area_qty:
            if (l / nx) >= (w / ny): nx += 1
            else: ny += 1
        qty = nx * ny
        dx = round(l / nx, 2)
        dy = round(w / ny, 2)
        return nx, ny, qty, dx, dy, round(dx/2, 2), round(dy/2, 2)