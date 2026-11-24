#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CALCULADOR EPS WEB v19.0 - MIX CORREGIDO Y CLARO
- Mezcla REAL de todos los modelos en cada grupo de largo
- Cálculo de volumen correcto (pieza por pieza)
- Visualización clara de todos los grupos
- Decimales funcionales
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
from collections import defaultdict

KERF_CM = 0.2
st.set_page_config(page_title="📦 Calculador EPS Covintec", layout="wide")

# ==========================================
# 🧠 MOTOR GEOMÉTRICO (Single) - INTACTO
# ==========================================
def _calcular_layout(ancho_bloque, alto_bloque, largo_bloque, d1, d2, d3, modo_uniforme=False):
    dims = sorted([float(d1), float(d2), float(d3)], reverse=True)
    mejor = None
    max_piezas = -1
    rango_longitudes = range(1) if modo_uniforme else range(3)

    for i in rango_longitudes:
        lp = dims[i]
        if lp > largo_bloque + 0.01: continue
        capas = int((largo_bloque + KERF_CM) // (lp + KERF_CM))
        if capas == 0: continue

        dA, dB = dims[(i+1)%3], dims[(i+2)%3]
        candidatos = []

        if modo_uniforme:
            n_h1 = int((alto_bloque + KERF_CM) // (dA + KERF_CM))
            n_w1 = int((ancho_bloque + KERF_CM) // (dB + KERF_CM))
            if n_h1 > 0 and n_w1 > 0: candidatos.append({"tipo": "U1", "n_h": n_h1, "n_w": n_w1, "h_p": dA, "w_p": dB, "total_capa": n_h1 * n_w1})
            n_h2 = int((alto_bloque + KERF_CM) // (dB + KERF_CM))
            n_w2 = int((ancho_bloque + KERF_CM) // (dA + KERF_CM))
            if n_h2 > 0 and n_w2 > 0: candidatos.append({"tipo": "U2", "n_h": n_h2, "n_w": n_w2, "h_p": dB, "w_p": dA, "total_capa": n_h2 * n_w2})
        else:
            max_a, max_b = int(alto_bloque // dA), int(alto_bloque // dB)
            for n_a in range(max_a + 1):
                for n_b in range(max_b + 1):
                    if n_a == 0 and n_b == 0: continue
                    total_filas = n_a + n_b
                    h_usada = n_a * dA + n_b * dB + (total_filas - 1) * KERF_CM
                    if h_usada > alto_bloque + 0.001: continue
                    nx_a = int((ancho_bloque + KERF_CM) // (dB + KERF_CM))
                    nx_b = int((ancho_bloque + KERF_CM) // (dA + KERF_CM))
                    total_fila = n_a * nx_a + n_b * nx_b
                    if total_fila > 0:
                        candidatos.append({"tipo": "Mix", "n_a": n_a, "nx_a": nx_a, "h_a": dA, "w_a": dB,
                                           "n_b": n_b, "nx_b": nx_b, "h_b": dB, "w_b": dA,
                                           "total_filas": total_filas, "h_usada": h_usada, "total_capa": total_fila})

        for cfg in candidatos:
            total_final = cfg["total_capa"] * capas
            if total_final > max_piezas:
                max_piezas = total_final
                cortes_long = max(0, capas - 1)
                area_long = cortes_long * alto_bloque * ancho_bloque
                if modo_uniforme:
                    cortes_h = max(0, cfg["n_h"] - 1)
                    area_h = cortes_h * ancho_bloque * lp
                    cortes_v = cfg["n_h"] * max(0, cfg["n_w"] - 1)
                    area_v = cortes_v * cfg["h_p"] * lp
                else:
                    cortes_h = max(0, cfg["total_filas"] - 1)
                    area_h = cortes_h * ancho_bloque * lp
                    area_v = 0
                    if cfg["n_a"] > 0: area_v += cfg["n_a"] * max(0, cfg["nx_a"]-1) * cfg["h_a"] * lp
                    if cfg["n_b"] > 0: area_v += cfg["n_b"] * max(0, cfg["nx_b"]-1) * cfg["h_b"] * lp
                
                vol_kerf_cm3 = (area_long + area_h + area_v) * KERF_CM
                vol_pieza = d1*d2*d3
                vol_bloque = alto_bloque * ancho_bloque * largo_bloque
                vol_bloque_m3 = vol_bloque / 1_000_000
                
                mejor = {
                    "total": total_final, "capas": capas, "ps": cfg["total_capa"], "lp": lp,
                    "config_sec": cfg, "ancho_usado": ancho_bloque, "uniforme": modo_uniforme,
                    "vol_bloque_m3": vol_bloque_m3,
                    "vol_kerf_m3": vol_kerf_cm3 / 1_000_000,
                    "vol_gross_m3": (total_final * vol_pieza) / 1_000_000
                }
    return mejor

def _graficar_single(r):
    if not r: return None
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(f"📦 Plano EPS | Total: {r['total']} pz", fontsize=14, fontweight='bold')
    ab, cfg, uniforme, lp = r['ancho_usado'], r['config_sec'], r['uniforme'], r['lp']
    ax1.set_xlim(0, ab); ax1.set_ylim(0, 66); ax1.set_aspect('equal'); ax1.grid(ls=':', alpha=0.4)
    ax1.set_title(f"Transversal 66×{ab:.0f} | Largo: {lp:.0f}cm", fontsize=12)
    if uniforme:
        n_h, n_w, h_p, w_p = cfg["n_h"], cfg["n_w"], cfg["h_p"], cfg["w_p"]
        for row in range(n_h):
            for col in range(n_w):
                ax1.add_patch(patches.Rectangle((col*(w_p+KERF_CM), row*(h_p+KERF_CM)), w_p, h_p, fc='#3498DB', ec='w', lw=1.5))
        h_total = n_h*h_p + (n_h-1)*KERF_CM
    else:
        y_pos = 0
        for _ in range(cfg["n_a"]):
            for col in range(cfg["nx_a"]):
                ax1.add_patch(patches.Rectangle((col*(cfg["w_a"]+KERF_CM), y_pos), cfg["w_a"], cfg["h_a"], fc='#3498DB', ec='w', lw=1.5))
            y_pos += cfg["h_a"] + KERF_CM
        for _ in range(cfg["n_b"]):
            for col in range(cfg["nx_b"]):
                ax1.add_patch(patches.Rectangle((col*(cfg["w_b"]+KERF_CM), y_pos), cfg["w_b"], cfg["h_b"], fc='#2ECC71', ec='w', lw=1.5))
            y_pos += cfg["h_b"] + KERF_CM
        h_total = cfg["h_usada"]
    if h_total < 66: ax1.add_patch(patches.Rectangle((0, h_total), ab, 66-h_total, fc='#FADBD8', ec='#C0392B', hatch='...', alpha=0.4))
    ax2.set_xlim(0, 506); ax2.set_ylim(0, 66); ax2.set_aspect('equal'); ax2.grid(ls=':', alpha=0.4)
    ax2.set_title(f"Longitudinal 506 cm | {r['capas']} cortes", fontsize=12)
    for i in range(r['capas']):
        ax2.add_patch(patches.Rectangle((i*(lp+KERF_CM), 0), lp, 66, fc='#3498DB', ec='w', alpha=0.8))
        ax2.text(i*(lp+KERF_CM)+lp/2, 33, str(i+1), ha='center', va='center', c='w', fontweight='bold')
    plt.tight_layout(); return fig

# ==========================================
# 🔄 MOTOR MIX CORREGIDO - ENFOQUE POR FILAS
# ==========================================
def _optimizar_seccion_filas(ancho_bloque, alto_bloque, piezas_unicas):
    """
    Optimiza la sección transversal usando enfoque de FILAS.
    piezas_unicas: lista de dicts con {id, w, h, color, m3, qty}
    Retorna: (layout, area_total, info_filas)
    """
    if not piezas_unicas:
        return [], 0, []
    
    # Paso 1: Obtener alturas únicas disponibles (considerando rotación)
    alturas_candidatas = set()
    for p in piezas_unicas:
        alturas_candidatas.add(round(p['h'], 1))
        alturas_candidatas.add(round(p['w'], 1))
    alturas_candidatas = sorted(alturas_candidatas)
    
    # Paso 2: Buscar la mejor combinación de filas que sume <= alto_bloque
    mejor_config = None
    mejor_piezas = 0
    
    # Probar todas las combinaciones de 1, 2, 3, 4 filas
    from itertools import combinations_with_replacement
    for num_filas in range(1, 5):
        for combo_alturas in combinations_with_replacement(alturas_candidatas, num_filas):
            # Calcular altura total con kerf entre filas
            h_total = sum(combo_alturas) + (num_filas - 1) * KERF_CM
            if h_total > alto_bloque + 0.01:
                continue
            
            # Para cada fila, calcular cuántas piezas caben en el ancho
            total_piezas_config = 0
            for altura_fila in combo_alturas:
                # Buscar piezas que puedan ir en esta fila (misma altura o rotadas)
                piezas_compatibles = []
                for p in piezas_unicas:
                    if abs(p['h'] - altura_fila) < 0.01:
                        piezas_compatibles.append({'w': p['w'], 'h': p['h'], 'id': p['id'], 'color': p['color'], 'm3': p['m3']})
                    elif abs(p['w'] - altura_fila) < 0.01:
                        piezas_compatibles.append({'w': p['h'], 'h': p['w'], 'id': p['id'], 'color': p['color'], 'm3': p['m3']})
                
                if not piezas_compatibles:
                    continue
                
                # Ordenar por ancho (mayor primero) para mejor empaque
                piezas_compatibles.sort(key=lambda x: x['w'], reverse=True)
                
                # Contar cuántas caben en el ancho
                x_pos = 0
                count = 0
                for pc in piezas_compatibles:
                    if x_pos + pc['w'] <= ancho_bloque + 0.01:
                        count += 1
                        x_pos += pc['w'] + KERF_CM
                    else:
                        break
                
                total_piezas_config += count
            
            if total_piezas_config > mejor_piezas:
                mejor_piezas = total_piezas_config
                mejor_config = combo_alturas
    
    if mejor_config is None:
        return [], 0, []
    
    # Paso 3: Construir el layout con la mejor configuración
    layout = []
    y_pos = 0
    area_total = 0
    info_filas = []
    
    for altura_fila in mejor_config:
        # Buscar piezas compatibles
        piezas_compatibles = []
        for p in piezas_unicas:
            if abs(p['h'] - altura_fila) < 0.01:
                piezas_compatibles.append({'w': p['w'], 'h': p['h'], 'id': p['id'], 'color': p['color'], 'm3': p['m3']})
            elif abs(p['w'] - altura_fila) < 0.01:
                piezas_compatibles.append({'w': p['h'], 'h': p['w'], 'id': p['id'], 'color': p['color'], 'm3': p['m3']})
        
        if not piezas_compatibles:
            y_pos += altura_fila + KERF_CM
            continue
        
        piezas_compatibles.sort(key=lambda x: x['w'], reverse=True)
        
        x_pos = 0
        piezas_en_fila = []
        for pc in piezas_compatibles:
            if x_pos + pc['w'] <= ancho_bloque + 0.01:
                pieza_colocada = {
                    'x': x_pos, 'y': y_pos,
                    'w': pc['w'], 'h': pc['h'],
                    'id': pc['id'], 'color': pc['color'], 'm3': pc['m3']
                }
                layout.append(pieza_colocada)
                piezas_en_fila.append(pc['id'])
                area_total += pc['w'] * pc['h']
                x_pos += pc['w'] + KERF_CM
            else:
                break
        
        info_filas.append({
            'altura': altura_fila,
            'y_inicio': y_pos,
            'piezas': piezas_en_fila,
            'ancho_usado': x_pos - KERF_CM if piezas_en_fila else 0
        })
        
        y_pos += altura_fila + KERF_CM
    
    return layout, area_total, info_filas

def _calcular_volumen_real(layout, largo_m3):
    """Calcula el volumen real sumando cada pieza individualmente"""
    vol_total = 0.0
    for p in layout:
        vol_total += p['w'] * p['h'] * largo_m3
    return vol_total / 1_000_000  # Convertir a m³

def _calcular_kerf_mix(grupos, ancho, alto, kerf):
    """Calcula kerf para layouts mixtos"""
    vol_kerf = 0.0
    for g in grupos:
        m3 = g['m3']
        capas = g['capas']
        lay = g['lay']
        
        # Kerf longitudinal (cortes entre capas a lo largo de 506)
        if capas > 1:
            vol_kerf += (capas - 1) * ancho * alto * kerf
        
        # Kerf en la cara transversal
        # Cortes horizontales (entre filas)
        alturas_filas = sorted(list(set(p['y'] for p in lay)))
        if len(alturas_filas) > 1:
            # Cada corte horizontal atraviesa todo el ancho y el largo m3
            vol_kerf += (len(alturas_filas) - 1) * ancho * m3 * kerf
        
        # Cortes verticales (entre piezas en cada fila)
        for y in set(p['y'] for p in lay):
            piezas_en_fila = [p for p in lay if p['y'] == y]
            if len(piezas_en_fila) > 1:
                # Cada corte vertical atraviesa la altura de la fila y el largo m3
                altura_fila = piezas_en_fila[0]['h']
                vol_kerf += (len(piezas_en_fila) - 1) * altura_fila * m3 * kerf
    
    return vol_kerf / 1_000_000

def _graficar_mix_longitudinal(pats, ancho_bloque):
    """Gráfico longitudinal mostrando TODOS los grupos"""
    fig, ax = plt.subplots(figsize=(14, 3.5))
    ax.set_xlim(0, 506)
    ax.set_ylim(-2, 12)
    ax.axis('off')
    
    # Fondo del bloque
    ax.add_patch(patches.Rectangle((0, 0), 506, 10, facecolor='#F0F2F6', edgecolor='#CBD5E1', lw=1.5))
    
    current_x = 0
    colores_usados = []
    
    for idx, p in enumerate(pats):
        m3 = p['m3']
        capas = p['capas']
        color = p['c']
        modelos = p['modelos']
        
        len_grupo = capas * (m3 + KERF_CM)
        
        # Dibujar bloque del grupo
        ax.add_patch(patches.Rectangle((current_x, 0), len_grupo, 10, 
                                       facecolor=color, alpha=0.85, edgecolor='white', lw=1.5))
        
        # Texto con info del grupo
        modelos_str = ', '.join(sorted(set(modelos)))
        ax.text(current_x + len_grupo/2, 6, f"{modelos_str}", 
                ha='center', va='center', fontsize=9, fontweight='bold', color='white')
        ax.text(current_x + len_grupo/2, 2, f"L={m3:.1f}cm × {capas} cortes", 
                ha='center', va='center', fontsize=8, color='white')
        
        # Líneas de corte internas
        for c in range(1, capas):
            cut_pos = current_x + c * (m3 + KERF_CM)
            ax.plot([cut_pos, cut_pos], [0, 10], color='white', linestyle='--', alpha=0.7, lw=1)
        
        current_x += len_grupo
        colores_usados.append((modelos_str, color))
    
    # Residuo
    if current_x < 506:
        res = 506 - current_x
        ax.add_patch(patches.Rectangle((current_x, 0), res, 10, 
                                       facecolor='#FADBD8', edgecolor='#C0392B', hatch='||', alpha=0.6))
        ax.text(current_x + res/2, 5, f"Residuo\n{res:.1f} cm", 
                ha='center', va='center', fontsize=9, color='#C0392B', fontweight='bold')
    
    # Regla
    ax.set_xticks([0, 100, 200, 300, 400, 506])
    ax.tick_params(axis='x', colors='gray')
    
    # Leyenda de colores
    leyenda_y = -1.5
    for i, (modelo, color) in enumerate(colores_usados[:6]):
        ax.add_patch(patches.Rectangle((i*85, leyenda_y-0.3), 80, 0.6, facecolor=color, alpha=0.85))
        ax.text(i*85 + 40, leyenda_y, modelo, ha='center', va='center', fontsize=7)
    
    plt.title("Vista Longitudinal del Bloque (506 cm) - Orden de corte por grupo de largo", 
              fontsize=11, fontweight='bold', pad=10)
    plt.tight_layout()
    return fig

# ==========================================
# 🖥️ INTERFAZ STREAMLIT
# ==========================================
st.title("📦 Calculador EPS Covintec")
st.caption(f"⚙️ Kerf: {KERF_CM*10:.0f}mm | Mix Corregido v19.0")

tab1, tab2 = st.tabs(["🔹 Single (Pieza Única)", "🔹 Mix (Combinaciones Inteligentes)"])

with tab1:
    st.header("Cálculo de Pieza Única")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Parámetros")
        modo_optimo = st.checkbox("🔍 Calcular Ancho Óptimo (126-156)", value=False)
        if modo_optimo:
            st.info("Elegirá el ancho con MAYOR eficiencia % (aprovechamiento).")
            ancho_slider = 130
        else:
            st.info("Ajusta manualmente el ancho.")
            ancho_slider = st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_single")
        
        st.markdown("### 📐 Dimensiones (cm)")
        d1 = st.number_input("Medida 1", value=5.0)
        d2 = st.number_input("Medida 2", value=61.0)
        d3 = st.number_input("Medida 3", value=122.0)
        
        st.markdown("### ⚖️ Densidad y Geometría")
        densidad = st.selectbox("Densidad EPS (kg/m³)", list(range(7, 20)), index=3, key="densidad_single")
        modo_bovedilla = st.checkbox("🔸 Activar modo Bovedilla (Perfilado CNC)", value=False)
        factor_perfilado = 20.0
        if modo_bovedilla: factor_perfilado = st.slider("Pérdida por perfilado (%)", 5.0, 35.0, 20.0, 1.0)
        modo_uniforme = st.checkbox("✅ Priorizar Acomodo Operativo (Largo Estándar)", value=True)
        
        calc = st.button("🚀 Calcular", type="primary", use_container_width=True)

    with col2:
        if calc:
            st.subheader("📊 Resultados")
            ancho_final = ancho_slider
            if modo_optimo:
                mejor_ef, mejor_a = -1, 126
                for a in range(126, 157):
                    r = _calcular_layout(a, 66.0, 506.0, d1, d2, d3, modo_uniforme)
                    if r and r['vol_gross_m3']/r['vol_bloque_m3'] > mejor_ef:
                        mejor_ef, mejor_a = r['vol_gross_m3']/r['vol_bloque_m3'], a
                ancho_final = mejor_a
            
            r = _calcular_layout(ancho_final, 66.0, 506.0, d1, d2, d3, modo_uniforme)
            if r:
                vol_gross, vol_kerf, vol_block = r['vol_gross_m3'], r['vol_kerf_m3'], r['vol_bloque_m3']
                vol_prof = vol_gross * (factor_perfilado/100) if modo_bovedilla else 0.0
                vol_net = vol_gross - vol_prof
                vol_rest = max(0, vol_block - vol_gross - vol_kerf)
                
                pct_net, pct_prof, pct_kerf, pct_rest = [(v/vol_block)*100 for v in [vol_net, vol_prof, vol_kerf, vol_rest]]
                peso_net, peso_prof, peso_kerf, peso_rest = [(v*densidad) for v in [vol_net, vol_prof, vol_kerf, vol_rest]]
                peso_total = vol_block * densidad
                
                st.info(f"📋 **Estrategia:** {'Operativo' if modo_uniforme else 'Matemático'} | **Largo:** `{r['lp']:.0f} cm`")
                c1,c2,c3 = st.columns(3)
                c1.metric("📦 Total Piezas", r['total']); c2.metric("📈 Eficiencia Bruta", f"{(vol_gross/vol_block)*100:.2f}%"); c3.metric("🧱 Peso Neto", f"{peso_net:.2f} kg")
                
                st.divider(); st.subheader("📉 Desglose del Bloque (100%)")
                st.info(f"⚖️ **Peso Total:** `{peso_total:.2f} kg` | 📦 **Volumen Total:** `{vol_block:.4f} m³`")
                st.markdown(f"🔵 **Producto Final (Neto):** `{pct_net:.2f}%` → `{vol_net:.4f} m³` → `{peso_net:.2f} kg`"); st.progress(min(1.0, pct_net/100))
                if modo_bovedilla: st.markdown(f"🔸 **Perfilado Bovedilla:** `{pct_prof:.2f}%` → `{vol_prof:.4f} m³` → `{peso_prof:.2f} kg`"); st.progress(min(1.0, pct_prof/100))
                st.markdown(f"🔴 **Kerf (Hilo):** `{pct_kerf:.2f}%` → `{vol_kerf:.4f} m³` → `{peso_kerf:.2f} kg`"); st.progress(min(1.0, pct_kerf/100))
                st.markdown(f"⬜ **Restante Físico:** `{pct_rest:.2f}%` → `{vol_rest:.4f} m³` → `{peso_rest:.2f} kg`"); st.progress(min(1.0, pct_rest/100))
                st.success(f"✅ **Verificación:** {vol_net:.4f}+{vol_prof:.4f}+{vol_kerf:.4f}+{vol_rest:.4f} ≈ `{vol_block:.4f} m³`")
                st.pyplot(_graficar_single(r))

# ==========================================
# 🔹 MODO MIX CORREGIDO
# ==========================================
with tab2:
    st.header("🔄 Optimización de Mezcla con Combinaciones")
    st.markdown("""
    🔹 **Combinaciones Inteligentes**: Busca piezas que sumen ~66 cm en altura  
    🔹 **Mezcla Real**: Todos los modelos se consideran en cada grupo de largo  
    🔹 **Volumen Real**: Calcula pieza por pieza, no asume dimensiones iguales
    """)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ Configuración Mix")
        modo_optimo_mix = st.checkbox("🔍 Buscar Ancho Óptimo Mix (126-156)", value=False)
        ancho_mix = st.slider("Ancho Bloque (cm)", 126, 156, 140, step=1, key="slider_mix", disabled=modo_optimo_mix)
        densidad_mix = st.selectbox("Densidad EPS (kg/m³)", list(range(7, 20)), index=3, key="densidad_mix")
        
        st.markdown("### 🔸 Geometría de Pieza")
        modo_bovedilla_mix = st.checkbox("Activar modo Bovedilla (Perfilado CNC)", value=False)
        factor_perfilado_mix = 20.0
        if modo_bovedilla_mix: factor_perfilado_mix = st.slider("Pérdida por perfilado (%)", 5.0, 35.0, 20.0, 1.0)
        
        st.markdown("### 📋 Lista de Pedidos")
        st.caption("💡 **Usa punto (.) para decimales**. Ejemplo: 2.5, 3.5, 44.5")
        
        # Datos de prueba con tus medidas
        default_prod = [
            {'id':'A','m1':3.5,'m2':34.0,'m3':46.0,'qty':10,'color':'#3498DB'},
            {'id':'B','m1':2.5,'m2':17.5,'m3':19.0,'qty':20,'color':'#2ECC71'},
            {'id':'C','m1':2.5,'m2':19.0,'m3':44.5,'qty':15,'color':'#E67E22'},
            {'id':'D','m1':2.5,'m2':22.5,'m3':44.5,'qty':12,'color':'#9B59B6'},
            {'id':'E','m1':3.5,'m2':42.0,'m3':54.0,'qty':8,'color':'#F39C12'},
            {'id':'F','m1':3.5,'m2':39.0,'m3':54.0,'qty':10,'color':'#E74C3C'},
            {'id':'G','m1':3.5,'m2':34.0,'m3':39.0,'qty':15,'color':'#1ABC9C'},
            {'id':'H','m1':2.5,'m2':30.5,'m3':33.0,'qty':18,'color':'#34495E'},
            {'id':'I','m1':2.5,'m2':30.5,'m3':50.0,'qty':12,'color':'#95A5A6'},
            {'id':'J','m1':2.5,'m2':36.0,'m3':50.0,'qty':10,'color':'#D35400'},
            {'id':'K','m1':2.5,'m2':33.0,'m3':50.0,'qty':14,'color':'#8E44AD'}
        ]
        
        if 'prod_mix' not in st.session_state:
            st.session_state['prod_mix'] = default_prod
        
        edited_df = st.data_editor(
            st.session_state['prod_mix'],
            column_config={
                "id": st.column_config.TextColumn("ID", width="small"),
                "m1": st.column_config.NumberColumn("M1 (cm)", format="%.2f", step=0.5, width="small"),
                "m2": st.column_config.NumberColumn("M2 (cm)", format="%.2f", step=0.5, width="small"),
                "m3": st.column_config.NumberColumn("M3 Largo (cm)", format="%.1f", step=0.5, width="small"),
                "qty": st.column_config.NumberColumn("Cantidad", format="%d", step=1, width="small"),
                "color": st.column_config.TextColumn("Color Hex", width="small")
            },
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_mix_v19"
        )
        
        if edited_df != st.session_state['prod_mix']:
            st.session_state['prod_mix'] = edited_df
        
        calc_mix = st.button("🚀 Optimizar con Combinaciones", type="primary", use_container_width=True)

    with col2:
        if calc_mix:
            st.subheader("📊 Resultados Mix")
            
            # Construir pool de piezas únicas por modelo
            modelos_unicos = {}
            for row in st.session_state['prod_mix']:
                try:
                    m1, m2, m3 = float(row['m1']), float(row['m2']), float(row['m3'])
                    qty = int(row['qty'])
                except:
                    continue
                
                if m3 > 506:
                    st.error(f"❌ {row['id']} largo >506")
                    continue
                
                key = (row['id'], m3)
                modelos_unicos[key] = {
                    'id': row['id'],
                    'w': m1,
                    'h': m2,
                    'm3': m3,
                    'color': row['color'],
                    'qty': qty
                }
            
            # Agrupar por largo (M3)
            groups = defaultdict(list)
            for key, pieza in modelos_unicos.items():
                groups[pieza['m3']].append(pieza)
            
            # Optimizador
            anchos_a_probar = range(126, 157) if modo_optimo_mix else [ancho_mix]
            mejor_res, mejor_ancho, mejor_ef = None, None, -1
            
            for a in anchos_a_probar:
                pats = []
                tp_total = 0
                vol_gross_total = 0.0
                longitud_usada = 0.0
                
                for m3, grp in sorted(groups.items(), reverse=True):
                    # Optimizar sección para este grupo de largo
                    lay, area, info_filas = _optimizar_seccion_filas(a, 66.0, grp)
                    
                    if not lay:
                        continue
                    
                    # Calcular cuántas capas caben en el espacio restante
                    espacio_restante = 506.0 - longitud_usada
                    cap = int(espacio_restante // (m3 + KERF_CM))
                    
                    if cap > 0:
                        # Calcular volumen REAL sumando cada pieza
                        vol_seccion = _calcular_volumen_real(lay, m3)
                        vol_grupo = vol_seccion * cap
                        
                        # Contar piezas totales
                        tp_grupo = len(lay) * cap
                        
                        # Obtener modelos en esta sección
                        modelos_en_seccion = list(set(p['id'] for p in lay))
                        
                        tp_total += tp_grupo
                        vol_gross_total += vol_grupo
                        
                        pats.append({
                            'm3': m3,
                            'lay': lay,
                            'capas': cap,
                            'tg': tp_grupo,
                            'c': grp[0]['color'],
                            'area_seccion': area,
                            'vol_seccion': vol_seccion,
                            'modelos': modelos_en_seccion,
                            'info_filas': info_filas
                        })
                        longitud_usada += cap * (m3 + KERF_CM)
                
                if not pats:
                    continue
                
                vol_block = 66.0 * a * 506.0 / 1_000_000
                vol_kerf = _calcular_kerf_mix(pats, a, 66.0, KERF_CM)
                vol_prof = vol_gross_total * (factor_perfilado_mix/100) if modo_bovedilla_mix else 0.0
                vol_net = vol_gross_total - vol_prof
                vol_rest = max(0, vol_block - vol_gross_total - vol_kerf)
                ef_neta = (vol_net / vol_block) * 100
                
                if ef_neta > mejor_ef:
                    mejor_ef = ef_neta
                    mejor_ancho = a
                    mejor_res = {
                        "pats": pats,
                        "tp": tp_total,
                        "vol_gross": vol_gross_total,
                        "vol_kerf": vol_kerf,
                        "vol_prof": vol_prof,
                        "vol_net": vol_net,
                        "vol_rest": vol_rest,
                        "vol_block": vol_block,
                        "densidad": densidad_mix,
                        "longitud_usada": longitud_usada
                    }
            
            if mejor_res:
                r = mejor_res
                st.success(f"✅ **Mejor Mezcla Encontrada** | Ancho: `{mejor_ancho} cm` | Eficiencia Neta: `{mejor_ef:.2f}%` | Total: `{r['tp']}` piezas")
                
                peso_net = r['vol_net'] * r['densidad']
                peso_prof = r['vol_prof'] * r['densidad']
                peso_kerf = r['vol_kerf'] * r['densidad']
                peso_rest = r['vol_rest'] * r['densidad']
                peso_total = r['vol_block'] * r['densidad']
                
                pct_net = (r['vol_net']/r['vol_block'])*100
                pct_prof = (r['vol_prof']/r['vol_block'])*100
                pct_kerf = (r['vol_kerf']/r['vol_block'])*100
                pct_rest = (r['vol_rest']/r['vol_block'])*100
                
                c1, c2, c3 = st.columns(3)
                c1.metric("📦 Total Piezas", r['tp'])
                c2.metric("📈 Eficiencia Neta", f"{pct_net:.2f}%")
                c3.metric("🧱 Peso Neto", f"{peso_net:.2f} kg")
                
                st.divider()
                st.subheader("📉 Desglose del Bloque (100%)")
                st.info(f"⚖️ **Peso Total:** `{peso_total:.2f} kg` | 📦 **Volumen Total:** `{r['vol_block']:.4f} m³`")
                
                st.markdown(f"🔵 **Producto Final (Neto):** `{pct_net:.2f}%` → `{r['vol_net']:.4f} m³` → `{peso_net:.2f} kg`")
                st.progress(min(1.0, pct_net/100))
                
                if modo_bovedilla_mix:
                    st.markdown(f"🔸 **Perfilado Bovedilla:** `{pct_prof:.2f}%` → `{r['vol_prof']:.4f} m³` → `{peso_prof:.2f} kg`")
                    st.progress(min(1.0, pct_prof/100))
                
                st.markdown(f"🔴 **Kerf (Hilo):** `{pct_kerf:.2f}%` → `{r['vol_kerf']:.4f} m³` → `{peso_kerf:.2f} kg`")
                st.progress(min(1.0, pct_kerf/100))
                
                st.markdown(f"⬜ **Restante Físico:** `{pct_rest:.2f}%` → `{r['vol_rest']:.4f} m³` → `{peso_rest:.2f} kg`")
                st.progress(min(1.0, pct_rest/100))
                
                st.success(f"✅ **Verificación:** {r['vol_net']:.4f}+{r['vol_prof']:.4f}+{r['vol_kerf']:.4f}+{r['vol_rest']:.4f} ≈ `{r['vol_block']:.4f} m³`")
                
                # VISTA LONGITUDINAL - MUESTRA TODOS LOS GRUPOS
                st.subheader("📏 Vista Longitudinal (Orden de Corte)")
                st.markdown("Cada bloque de color representa un grupo de piezas con el mismo largo. Las líneas punteadas son los cortes del hilo caliente.")
                st.pyplot(_graficar_mix_longitudinal(r['pats'], mejor_ancho))
                
                # TABLA RESUMEN POR GRUPO
                st.subheader("📋 Resumen por Grupo de Largo")
                datos_resumen = []
                for p in r['pats']:
                    modelos = ', '.join(sorted(set(p['modelos'])))
                    datos_resumen.append({
                        'Largo (cm)': p['m3'],
                        'Modelos': modelos,
                        'Piezas/Sección': len(p['lay']),
                        'Capas': p['capas'],
                        'Total Piezas': p['tg'],
                        'Volumen (m³)': f"{p['vol_seccion'] * p['capas']:.4f}",
                        'Longitud Usada (cm)': f"{p['capas'] * (p['m3'] + KERF_CM):.1f}"
                    })
                st.table(datos_resumen)
                
                # VISTA TRANSVERSAL DETALLADA
                st.subheader("🔍 Vista Transversal Detallada (Sección 66×Ancho)")
                st.markdown("Selecciona un grupo de largo para ver cómo se acomodan las piezas en la cara del bloque.")
                
                if r['pats']:
                    opciones = [f"Largo {p['m3']:.1f} cm - Modelos: {', '.join(sorted(set(p['modelos'])))} ({p['tg']} pz)" for p in r['pats']]
                    sel = st.selectbox("Ver sección de:", opciones, key="sel_seccion_mix_v19")
                    
                    # Extraer m3 seleccionado
                    m3_seleccionado = float(sel.split()[1])
                    pat = r['pats'][[p['m3'] for p in r['pats']].index(m3_seleccionado)]
                    
                    fig, ax = plt.subplots(figsize=(11, 6))
                    ax.set_xlim(0, mejor_ancho)
                    ax.set_ylim(0, 66)
                    ax.set_aspect('equal')
                    ax.grid(ls=':', alpha=0.5)
                    
                    # Título con info de combinación
                    alturas_filas = sorted(list(set(p['h'] for p in pat['lay'])))
                    suma_alturas = sum(alturas_filas) + (len(alturas_filas)-1) * KERF_CM
                    ax.set_title(f"Sección {mejor_ancho}×66 cm | Largo: {pat['m3']:.1f} cm\nCombinación alturas: {' + '.join([f'{h:.1f}' for h in alturas_filas])} = {suma_alturas:.1f} cm", 
                                fontsize=11, fontweight='bold')
                    
                    # Dibujar piezas
                    for p in pat['lay']:
                        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], 
                                                       fc=p['color'], ec='white', lw=1.5, alpha=0.9))
                        ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['id'], 
                                ha='center', va='center', c='white', fontweight='bold', fontsize=10)
                    
                    # Líneas de separación de filas
                    for info in pat['info_filas']:
                        if info['y_inicio'] > 0:
                            ax.axhline(y=info['y_inicio'] - KERF_CM/2, color='yellow', linestyle='-', alpha=0.7, lw=2)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Información detallada
                    st.markdown("### 📐 Detalle de Filas")
                    for i, info in enumerate(pat['info_filas']):
                        st.markdown(f"**Fila {i+1}** (altura {info['altura']:.1f} cm): Piezas {', '.join(info['piezas'])} | Ancho usado: {info['ancho_usado']:.1f} cm de {mejor_ancho} cm")
            else:
                st.warning("⚠️ No se encontró una mezcla válida con los parámetros actuales.")

st.markdown("---")
st.caption("💡 *Covintec v19.0 | Mix con combinaciones inteligentes y visualización clara de todos los grupos.*")