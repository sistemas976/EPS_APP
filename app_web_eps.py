#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CALCULADOR EPS WEB v18.0 - MIX CON COMBINACIONES INTELIGENTES
- Algoritmo de combinaciones que busca sumar ~66 cm en altura
- Permite cortes "entero + medio" (rearme)
- Optimiza para ~100% de aprovechamiento
- Decimales funcionales en la tabla
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
from collections import defaultdict
from itertools import combinations

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
# 🔄 MOTOR MIX CON COMBINACIONES INTELIGENTES
# ==========================================
def _encontrar_combinaciones_filas(items, alto_max=66.0):
    """
    Encuentra combinaciones de piezas que sumen ~alto_max (66 cm)
    Retorna lista de filas óptimas
    """
    # Agrupar por altura disponible
    alturas_disponibles = set()
    for item in items:
        alturas_disponibles.add(item['h'])
        alturas_disponibles.add(item['w'])  # Rotación
    
    alturas_disponibles = sorted(alturas_disponibles)
    
    # Buscar combinaciones que sumen cercano a alto_max
    mejores_combinaciones = []
    
    # Probar combinaciones de 1, 2, 3 piezas de altura
    for r in range(1, 4):
        for combo in combinations(alturas_disponibles, r):
            suma = sum(combo) + (r-1) * KERF_CM
            if suma <= alto_max + 0.01:
                desperdicio = alto_max - suma
                mejores_combinaciones.append({
                    'alturas': combo,
                    'suma': suma,
                    'desperdicio': desperdicio,
                    'eficiencia': (suma / alto_max) * 100
                })
    
    # Ordenar por eficiencia (mayor a menor)
    mejores_combinaciones.sort(key=lambda x: x['eficiencia'], reverse=True)
    
    return mejores_combinaciones[:10]  # Top 10

def _armar_seccion_optimizada(ancho_bloque, alto_bloque, items_grupo):
    """
    Arma la sección transversal óptima combinando piezas
    """
    if not items_grupo:
        return [], 0
    
    # Encontrar mejores combinaciones de altura
    combinaciones = _encontrar_combinaciones_filas(items_grupo, alto_bloque)
    
    if not combinaciones:
        return [], 0
    
    # Tomar la mejor combinación
    mejor_combo = combinaciones[0]
    alturas_fila = mejor_combo['alturas']
    
    # Armar filas con esas alturas
    layout_final = []
    y_pos = 0
    area_total = 0
    
    for altura_objetivo in alturas_fila:
        # Filtrar piezas que tengan esa altura (normal o rotada)
        piezas_compatibles = []
        for item in items_grupo:
            if abs(item['h'] - altura_objetivo) < 0.01:
                piezas_compatibles.append({'w': item['w'], 'h': item['h'], 'id': item['id'], 'color': item['color'], 'm3': item['m3']})
            elif abs(item['w'] - altura_objetivo) < 0.01:
                piezas_compatibles.append({'w': item['h'], 'h': item['w'], 'id': item['id'], 'color': item['color'], 'm3': item['m3']})
        
        if not piezas_compatibles:
            continue
        
        # Ordenar por ancho (mayor a menor) para mejor empaque
        piezas_compatibles.sort(key=lambda x: x['w'], reverse=True)
        
        # Colocar piezas en la fila
        x_pos = 0
        for pieza in piezas_compatibles:
            if x_pos + pieza['w'] > ancho_bloque:
                # Verificar si cabe como "mitad" (rearme)
                espacio_restante = ancho_bloque - x_pos
                if espacio_restante >= pieza['w'] / 2:
                    # Colocar mitad
                    pieza_colocada = {
                        'x': x_pos, 'y': y_pos,
                        'w': espacio_restante, 'h': pieza['h'],
                        'id': f"{pieza['id']}½", 'color': pieza['color'], 'm3': pieza['m3'],
                        'es_mitad': True
                    }
                    layout_final.append(pieza_colocada)
                    area_total += espacio_restante * pieza['h']
                break
            
            pieza_colocada = {
                'x': x_pos, 'y': y_pos,
                'w': pieza['w'], 'h': pieza['h'],
                'id': pieza['id'], 'color': pieza['color'], 'm3': pieza['m3'],
                'es_mitad': False
            }
            layout_final.append(pieza_colocada)
            area_total += pieza['w'] * pieza['h']
            x_pos += pieza['w'] + KERF_CM
        
        y_pos += altura_objetivo + KERF_CM
    
    return layout_final, area_total

def _calcular_kerf_mix(grupos, ancho, alto, kerf):
    vol_kerf = 0.0
    for g in grupos:
        m3, capas, lay = g['m3'], g['capas'], g['lay']
        if capas > 1:
            vol_kerf += (capas - 1) * ancho * alto * kerf
        vol_cortes_cara = len(lay) * m3 * kerf * 1.5
        vol_kerf += vol_cortes_cara * capas
    return vol_kerf / 1_000_000

def _graficar_mix_longitudinal(pats):
    fig, ax = plt.subplots(figsize=(14, 3))
    ax.set_xlim(0, 506)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    current_x = 0
    ax.add_patch(patches.Rectangle((0, 0), 506, 10, facecolor='#F0F2F6', edgecolor='#CBD5E1', lw=1))
    
    for p in pats:
        m3, capas, color = p['m3'], p['capas'], p['c']
        id_modelo = p['lay'][0]['id'] if p['lay'] else 'Mix'
        len_grupo = capas * (m3 + KERF_CM)
        
        ax.add_patch(patches.Rectangle((current_x, 0), len_grupo, 10, facecolor=color, alpha=0.85, edgecolor='white', lw=1))
        ax.text(current_x + len_grupo/2, 5, f"{id_modelo}\n{m3}cm (x{capas})", 
                ha='center', va='center', fontsize=10, fontweight='bold', color='white')
        
        for c in range(1, capas):
            cut_pos = current_x + c * (m3 + KERF_CM)
            ax.plot([cut_pos, cut_pos], [0, 10], color='white', linestyle='--', alpha=0.6)
        
        current_x += len_grupo
    
    if current_x < 506:
        res = 506 - current_x
        ax.add_patch(patches.Rectangle((current_x, 0), res, 10, facecolor='#FADBD8', edgecolor='#C0392B', hatch='||', alpha=0.6))
        ax.text(current_x + res/2, 5, f"Residuo\n{res:.1f} cm", ha='center', va='center', fontsize=9, color='#C0392B', fontweight='bold')
    
    ax.set_xticks([0, 100, 200, 300, 400, 506])
    ax.tick_params(axis='x', colors='gray')
    plt.tight_layout()
    return fig

# ==========================================
# 🖥️ INTERFAZ STREAMLIT
# ==========================================
st.title("📦 Calculador EPS Covintec")
st.caption(f"⚙️ Kerf: {KERF_CM*10:.0f}mm | Mix Combinaciones v18.0")

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
# 🔹 MODO MIX CON COMBINACIONES INTELIGENTES
# ==========================================
with tab2:
    st.header("🔄 Optimización de Mezcla con Combinaciones")
    st.markdown("""
    🔹 **Combinaciones Inteligentes**: Busca piezas que sumen ~66 cm en altura  
    🔹 **Corte Entero + Medio**: Permite rearme cuando una pieza no cabe completa  
    🔹 **Optimización ~100%**: Maximiza aprovechamiento del bloque
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
        
        # Editor con soporte para decimales
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
            key="editor_mix_combinaciones"
        )
        
        if edited_df != st.session_state['prod_mix']:
            st.session_state['prod_mix'] = edited_df
        
        calc_mix = st.button("🚀 Optimizar con Combinaciones", type="primary", use_container_width=True)

    with col2:
        if calc_mix:
            st.subheader("📊 Resultados Mix")
            
            # Construir pool de piezas
            pool = []
            for row in st.session_state['prod_mix']:
                try:
                    m1, m2, m3 = float(row['m1']), float(row['m2']), float(row['m3'])
                    qty = int(row['qty'])
                except:
                    continue
                
                if m3 > 506:
                    st.error(f"❌ {row['id']} largo >506")
                    continue
                
                for _ in range(qty):
                    pool.append({
                        'id': row['id'],
                        'w': m1,
                        'h': m2,
                        'm3': m3,
                        'color': row['color']
                    })
            
            # Agrupar por largo (M3)
            groups = defaultdict(list)
            for item in pool:
                groups[item['m3']].append(item)
            
            # Optimizador
            anchos_a_probar = range(126, 157) if modo_optimo_mix else [ancho_mix]
            mejor_res, mejor_ancho, mejor_ef = None, None, -1
            
            for a in anchos_a_probar:
                pats, tp, vol_gross = [], 0, 0.0
                longitud_usada = 0.0
                
                for m3, grp in sorted(groups.items(), reverse=True):
                    # Combinaciones inteligentes
                    lay, area = _armar_seccion_optimizada(a, 66.0, grp)
                    
                    if not lay:
                        continue
                    
                    espacio_restante = 506.0 - longitud_usada
                    cap = int(espacio_restante // (m3 + KERF_CM))
                    
                    if cap > 0:
                        tg = len(lay) * cap
                        tp += tg
                        vol_gross += tg * (lay[0]['w'] * lay[0]['h'] * m3) / 1_000_000
                        pats.append({
                            'm3': m3,
                            'lay': lay,
                            'capas': cap,
                            'tg': tg,
                            'c': grp[0]['color'],
                            'area_seccion': area
                        })
                        longitud_usada += cap * (m3 + KERF_CM)
                
                if not pats:
                    continue
                
                vol_block = 66.0 * a * 506.0 / 1_000_000
                vol_kerf = _calcular_kerf_mix(pats, a, 66.0, KERF_CM)
                vol_prof = vol_gross * (factor_perfilado_mix/100) if modo_bovedilla_mix else 0.0
                vol_net = vol_gross - vol_prof
                vol_rest = max(0, vol_block - vol_gross - vol_kerf)
                ef_neta = (vol_net / vol_block) * 100
                
                if ef_neta > mejor_ef:
                    mejor_ef = ef_neta
                    mejor_ancho = a
                    mejor_res = {
                        "pats": pats,
                        "tp": tp,
                        "vol_gross": vol_gross,
                        "vol_kerf": vol_kerf,
                        "vol_prof": vol_prof,
                        "vol_net": vol_net,
                        "vol_rest": vol_rest,
                        "vol_block": vol_block,
                        "densidad": densidad_mix
                    }
            
            if mejor_res:
                r = mejor_res
                st.success(f"✅ **Mejor Mezcla Encontrada** | Ancho: `{mejor_ancho} cm` | Eficiencia Neta: `{mejor_ef:.2f}%`")
                
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
                
                # VISTA LONGITUDINAL
                st.subheader("📏 Vista Longitudinal (Orden de Corte)")
                st.pyplot(_graficar_mix_longitudinal(r['pats']))
                
                # VISTA TRANSVERSAL DETALLADA
                st.subheader("🔍 Vista Transversal Detallada")
                if r['pats']:
                    opciones = [f"Largo {p['m3']:.1f} cm ({p['tg']} pz)" for p in r['pats']]
                    sel = st.selectbox("Ver sección de:", opciones, key="sel_seccion_mix_v4")
                    m3_seleccionado = float(sel.split()[1])
                    pat = r['pats'][[p['m3'] for p in r['pats']].index(m3_seleccionado)]
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.set_xlim(0, mejor_ancho)
                    ax.set_ylim(0, 66)
                    ax.set_aspect('equal')
                    ax.grid(ls=':', alpha=0.5)
                    ax.set_title(f"Sección {mejor_ancho}×66 cm | Largo: {pat['m3']:.1f} cm", fontsize=12, fontweight='bold')
                    
                    for p in pat['lay']:
                        color = p['color']
                        if p.get('es_mitad', False):
                            color = '#FF6B6B'  # Rojo para mitades
                        
                        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], 
                                                       fc=color, ec='white', lw=1.5, alpha=0.9))
                        
                        # Texto con indicador de mitad
                        texto = p['id']
                        if p.get('es_mitad', False):
                            texto += "½"
                        
                        ax.text(p['x']+p['w']/2, p['y']+p['h']/2, texto, 
                                ha='center', va='center', c='white', fontweight='bold', fontsize=9)
                    
                    plt.tight_layout()
                    st.pyplot(fig)
                    
                    # Información detallada de combinaciones
                    alturas_fila = sorted(list(set(p['h'] for p in pat['lay'])))
                    modelos_en_seccion = sorted(list(set(p['id'].replace('½','') for p in pat['lay'])))
                    
                    st.info(f"📐 **Modelos en sección:** {', '.join(modelos_en_seccion)}")
                    st.info(f"📏 **Combinación de alturas:** {' + '.join([f'{h:.1f}cm' for h in alturas_fila])} = {sum(alturas_fila) + (len(alturas_fila)-1)*KERF_CM:.1f} cm de 66 cm")
                    
                    # Verificar si hay mitades
                    hay_mitades = any(p.get('es_mitad', False) for p in pat['lay'])
                    if hay_mitades:
                        st.warning("⚠️ **Incluye piezas rearmadas (mitades)**: Requieren corte y unión")
                    else:
                        st.success("✅ **Todas las piezas son enteras**: Corte directo sin rearme")
            else:
                st.warning("⚠️ No se encontró una mezcla válida con los parámetros actuales.")

st.markdown("---")
st.caption("💡 *Covintec v18.0 | Mix con Combinaciones Inteligentes: Busca sumar ~66 cm en altura + permite rearme.*")