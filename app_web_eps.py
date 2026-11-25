#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CALCULADOR EPS WEB v25.0 - EMPAQUETADO 3D GUILLOTINA REAL
- Algoritmo 3D que rellena huecos (offcut utilization).
- Permite mezclar piezas de diferentes longitudes en el mismo bloque.
- Plan de corte longitudinal claro (a qué cm cortar).
- Reportes PDF para Single y Mix.
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
from collections import defaultdict

try:
    from fpdf import FPDF
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

KERF_CM = 0.2
ALTO_BLOQUE = 66.0
ANCHO_BLOQUE_DEF = 126.0 # Se ajustará con el slider
LARGO_BLOQUE = 506.0

st.set_page_config(page_title="📦 Calculador EPS Covintec", layout="wide")

# ==========================================
# 🧠 MOTOR SINGLE (Intacto y Probado)
# ==========================================
def _calcular_layout(ancho_bloque, alto_bloque, largo_bloque, d1, d2, d3, modo_uniforme=False):
    dims = sorted([float(d1), float(d2), float(d3)], reverse=True)
    mejor, max_piezas = None, -1
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
            if n_h1 > 0 and n_w1 > 0: candidatos.append({"n_h": n_h1, "n_w": n_w1, "h_p": dA, "w_p": dB, "total_capa": n_h1 * n_w1})
            n_h2 = int((alto_bloque + KERF_CM) // (dB + KERF_CM))
            n_w2 = int((ancho_bloque + KERF_CM) // (dA + KERF_CM))
            if n_h2 > 0 and n_w2 > 0: candidatos.append({"n_h": n_h2, "n_w": n_w2, "h_p": dB, "w_p": dA, "total_capa": n_h2 * n_w2})
        else:
            max_a, max_b = int(alto_bloque // dA), int(alto_bloque // dB)
            for n_a in range(max_a + 1):
                for n_b in range(max_b + 1):
                    if n_a == 0 and n_b == 0: continue
                    tf = n_a + n_b
                    hu = n_a * dA + n_b * dB + (tf - 1) * KERF_CM
                    if hu > alto_bloque + 0.001: continue
                    nx_a = int((ancho_bloque + KERF_CM) // (dB + KERF_CM))
                    nx_b = int((ancho_bloque + KERF_CM) // (dA + KERF_CM))
                    total_fila = n_a * nx_a + n_b * nx_b
                    if total_fila > 0:
                        candidatos.append({"n_a": n_a, "nx_a": nx_a, "h_a": dA, "w_a": dB, "n_b": n_b, "nx_b": nx_b,
                                           "h_b": dB, "w_b": dA, "total_filas": tf, "h_usada": hu, "total_capa": total_fila})
        for cfg in candidatos:
            total_final = cfg["total_capa"] * capas
            if total_final > max_piezas:
                max_piezas = total_final
                cl = max(0, capas - 1)
                al = cl * alto_bloque * ancho_bloque
                if modo_uniforme:
                    ch = max(0, cfg["n_h"] - 1); ah = ch * ancho_bloque * lp
                    cv = cfg["n_h"] * max(0, cfg["n_w"] - 1); av = cv * cfg["h_p"] * lp
                else:
                    ch = max(0, cfg["total_filas"] - 1); ah = ch * ancho_bloque * lp
                    av = 0
                    if cfg["n_a"] > 0: av += cfg["n_a"] * max(0, cfg["nx_a"]-1) * cfg["h_a"] * lp
                    if cfg["n_b"] > 0: av += cfg["n_b"] * max(0, cfg["nx_b"]-1) * cfg["h_b"] * lp
                vk = (al + ah + av) * KERF_CM
                vp = d1*d2*d3
                vb = alto_bloque * ancho_bloque * largo_bloque
                mejor = {"total": total_final, "capas": capas, "ps": cfg["total_capa"], "lp": lp,
                         "config_sec": cfg, "ancho_usado": ancho_bloque, "uniforme": modo_uniforme,
                         "vol_bloque_m3": vb/1e6, "vol_kerf_m3": vk/1e6, "vol_gross_m3": (total_final*vp)/1e6}
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
# 🔄 MOTOR MIX v25.0: EMPAQUETADO 3D GUILLOTINA
# ==========================================
class Space3D:
    def __init__(self, x, y, z, w, h, d):
        self.x, self.y, self.z = x, y, z  # Posición
        self.w, self.h, self.d = w, h, d  # Dimensiones (ancho, alto, largo)

def _pack_3d_guillotine(items_list, block_w, block_h, block_d):
    """
    Empaqueta piezas en 3D usando división guillotina.
    items_list: lista de dicts con 'w', 'h', 'd', 'id', 'color', 'qty'
    """
    # 1. Expandir cantidades y ordenar por volumen descendente (los grandes primero)
    expanded = []
    for item in items_list:
        for _ in range(item['qty']):
            expanded.append({
                'w': item['w'], 'h': item['h'], 'd': item['d'],
                'id': item['id'], 'color': item['color']
            })
    expanded.sort(key=lambda x: x['w'] * x['h'] * x['d'], reverse=True)
    
    spaces = [Space3D(0, 0, 0, block_w, block_h, block_d)]
    placed = []
    
    for item in expanded:
        best_space_idx = -1
        best_rotation = None
        
        # Buscar el mejor espacio que acomode la pieza (permitiendo rotar ancho y alto)
        for i, space in enumerate(spaces):
            # Orientación normal
            if item['w'] <= space.w + 0.01 and item['h'] <= space.h + 0.01 and item['d'] <= space.d + 0.01:
                best_space_idx = i
                best_rotation = (item['w'], item['h'], item['d'])
                break
            # Orientación rotada (ancho y alto intercambiados)
            elif item['h'] <= space.w + 0.01 and item['w'] <= space.h + 0.01 and item['d'] <= space.d + 0.01:
                best_space_idx = i
                best_rotation = (item['h'], item['w'], item['d'])
                break
        
        if best_space_idx != -1:
            space = spaces.pop(best_space_idx)
            pw, ph, pd = best_rotation
            
            placed.append({
                'x': space.x, 'y': space.y, 'z': space.z,
                'w': pw, 'h': ph, 'd': pd,
                'id': item['id'], 'color': item['color']
            })
            
            # Dividir el espacio restante en 3 nuevos espacios (Guillotina)
            # 1. Espacio a la derecha (a lo largo del ancho)
            if space.w - pw > KERF_CM:
                spaces.append(Space3D(space.x + pw + KERF_CM, space.y, space.z,
                                      space.w - pw - KERF_CM, space.h, space.d))
            # 2. Espacio arriba (a lo largo del alto)
            if space.h - ph > KERF_CM:
                spaces.append(Space3D(space.x, space.y + ph + KERF_CM, space.z,
                                      pw, space.h - ph - KERF_CM, space.d))
            # 3. Espacio al frente (a lo largo del largo)
            if space.d - pd > KERF_CM:
                spaces.append(Space3D(space.x, space.y, space.z + pd + KERF_CM,
                                      space.w, space.h, space.d - pd - KERF_CM))
            
            # Reordenar espacios: poner los más grandes primero para mejor ajuste (Best Fit)
            spaces.sort(key=lambda s: s.w * s.h * s.d, reverse=True)
            
    return placed, spaces

def _agrupar_por_rebanada(placed, block_w):
    """Agrupa las piezas colocadas por su posición longitudinal (z) para mostrar el plan de corte."""
    slices = defaultdict(list)
    for p in placed:
        # Redondear z para agrupar piezas que están en la misma "rebanada" longitudinal
        z_slice = round(p['z'], 1)
        slices[z_slice].append(p)
    
    # Ordenar rebanadas de inicio a fin del bloque
    sorted_slices = []
    for z in sorted(slices.keys()):
        piezas_en_rebanada = slices[z]
        # La longitud de esta rebanada es la máxima dimensión 'd' de las piezas en ella
        max_d = max(p['d'] for p in piezas_en_rebanada)
        sorted_slices.append({
            'z_inicio': z,
            'longitud': max_d,
            'z_fin': z + max_d,
            'piezas': piezas_en_rebanada
        })
    return sorted_slices

def _graficar_rebanada(slice_data, ancho_bloque):
    """Dibuja la vista transversal de una rebanada específica."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, ancho_bloque)
    ax.set_ylim(0, ALTO_BLOQUE)
    ax.set_aspect('equal')
    ax.grid(ls=':', alpha=0.4)
    
    modelos = sorted(set(p['id'] for p in slice_data['piezas']))
    ax.set_title(f"Rebanada: {slice_data['z_inicio']:.1f} cm a {slice_data['z_fin']:.1f} cm (Largo: {slice_data['longitud']:.1f} cm)\nModelos: {', '.join(modelos)}", 
                 fontsize=11, fontweight='bold')
    
    for p in slice_data['piezas']:
        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], 
                                       fc=p['color'], ec='white', lw=1.5, alpha=0.9))
        if p['w'] > 5 and p['h'] > 3:
            ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['id'], 
                    ha='center', va='center', c='white', fontweight='bold', fontsize=8)
            
    ax.set_xlabel("Ancho (cm)"); ax.set_ylabel("Alto (cm)")
    plt.tight_layout()
    return fig

def _graficar_mapa_longitudinal(slices, ancho_bloque):
    """Dibuja el mapa de cortes a lo largo de los 506 cm."""
    fig, ax = plt.subplots(figsize=(15, 3))
    ax.set_xlim(0, LARGO_BLOQUE)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    ax.add_patch(patches.Rectangle((0, 0), LARGO_BLOQUE, 10, facecolor='#F0F2F6', edgecolor='#333', lw=2))
    
    colores_usados = {}
    x_actual = 0
    
    for s in slices:
        longitud = s['longitud']
        modelos = sorted(set(p['id'] for p in s['piezas']))
        color = s['piezas'][0]['color']
        
        ax.add_patch(patches.Rectangle((x_actual, 0), longitud, 10, facecolor=color, alpha=0.85, edgecolor='white', lw=2))
        
        label = f"{', '.join(modelos)}\n{s['longitud']:.1f} cm"
        fs = 9 if longitud > 40 else 7
        ax.text(x_actual + longitud/2, 5, label, ha='center', va='center', fontsize=fs, fontweight='bold', color='white')
        
        # Línea de corte
        if x_actual > 0:
            ax.plot([x_actual, x_actual], [0, 10], color='red', ls='-', lw=2, alpha=0.7)
            
        colores_usados[', '.join(modelos)] = color
        x_actual += longitud + KERF_CM
        
    if x_actual - KERF_CM < LARGO_BLOQUE - 0.5:
        res = LARGO_BLOQUE - (x_actual - KERF_CM)
        ax.add_patch(patches.Rectangle((x_actual - KERF_CM, 0), res, 10, facecolor='#FADBD8', edgecolor='#C0392B', hatch='||', alpha=0.7, lw=2))
        ax.text(x_actual - KERF_CM + res/2, 5, f"RESIDUO\n{res:.1f} cm", ha='center', va='center', fontsize=9, color='#C0392B', fontweight='bold')
        
    ax.set_xticks([0, 100, 200, 300, 400, 506])
    ax.tick_params(axis='x', colors='gray', labelsize=8)
    ax.set_title(f"MAPA DE CORTES LONGITUDINALES (Bloque de {LARGO_BLOQUE} cm)", fontsize=12, fontweight='bold', pad=8)
    plt.tight_layout()
    return fig

# ==========================================
# 📄 GENERADORES DE PDF
# ==========================================
def _fig_to_png(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    return buf

def _generar_reporte_pdf_single(r, d1, d2, d3, densidad, factor_perfilado, modo_bovedilla, modo_uniforme):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    vg, vk, vb = r['vol_gross_m3'], r['vol_kerf_m3'], r['vol_bloque_m3']
    vpr = vg * (factor_perfilado/100) if modo_bovedilla else 0.0
    vn, vr = vg - vpr, max(0, vb - vg - vk)
    pn, pp, pk, pr = [(v/vb)*100 for v in [vn, vpr, vk, vr]]
    wn, wp, wk, wr = [(v*densidad) for v in [vn, vpr, vk, vr]]
    wt = vb * densidad
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 22)
    pdf.cell(0, 15, 'Reporte EPS - Pieza Unica', ln=True, align='C')
    pdf.set_font('Helvetica', '', 13)
    pdf.cell(0, 10, f'Dimensiones pieza: {d1} x {d2} x {d3} cm', ln=True, align='C')
    pdf.cell(0, 8, f'Bloque: {r["ancho_usado"]:.0f} x {ALTO_BLOQUE:.0f} x {LARGO_BLOQUE:.0f} cm | Kerf: {KERF_CM*10:.0f} mm', ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'RESUMEN', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Total de piezas: {r["total"]} | Capas: {r["capas"]} | Pz/capa: {r["ps"]}', ln=True)
    pdf.cell(0, 7, f'Eficiencia bruta: {(vg/vb)*100:.2f}% | Volumen bruto: {vg:.4f} m3 | Peso total: {wt:.2f} kg', ln=True)
    pdf.ln(5)
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'PLANOS DE CORTE', ln=True)
    fig = _graficar_single(r)
    pdf.image(_fig_to_png(fig, dpi=130), x=10, w=190)
    plt.close(fig)
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'DESGLOSE DEL BLOQUE (100%)', ln=True)
    pdf.ln(5)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 8, f'Volumen total: {vb:.4f} m3 | Peso total: {wt:.2f} kg', ln=True)
    pdf.ln(3)
    
    col_w = [50, 25, 35, 35, 35]
    headers = ['Concepto', '%', 'Volumen (m3)', 'Peso (kg)', 'Descripcion']
    for i, h in enumerate(headers): pdf.cell(col_w[i], 7, h, border=1, align='C')
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    filas = [('Producto Neto', pn, vn, wn, 'Piezas utiles'), ('Kerf (Hilo)', pk, vk, wk, 'Desgaste hilo'), ('Restante Fisico', pr, vr, wr, 'Residuo')]
    if modo_bovedilla: filas.insert(1, ('Perfilado Bovedilla', pp, vpr, wp, 'CNC'))
    for concepto, pct, vol, peso, desc in filas:
        pdf.cell(col_w[0], 6, concepto, border=1)
        pdf.cell(col_w[1], 6, f'{pct:.2f}%', border=1, align='C')
        pdf.cell(col_w[2], 6, f'{vol:.4f}', border=1, align='C')
        pdf.cell(col_w[3], 6, f'{peso:.2f}', border=1, align='C')
        pdf.cell(col_w[4], 6, desc, border=1)
        pdf.ln()
        
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

def _generar_reporte_pdf_mix(slices, ancho_bloque, densidad, total_pedidas, total_colocadas):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    vol_total = sum(sum(p['w']*p['h']*p['d'] for p in s['piezas']) for s in slices) / 1e6
    vol_bloque = ancho_bloque * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
    ef = (vol_total / vol_bloque * 100) if vol_bloque > 0 else 0
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 22)
    pdf.cell(0, 20, 'Reporte EPS - Mezcla 3D', ln=True, align='C')
    pdf.set_font('Helvetica', '', 13)
    pdf.cell(0, 10, f'Bloque: {ancho_bloque} x {ALTO_BLOQUE} x {LARGO_BLOQUE} cm', ln=True, align='C')
    pdf.cell(0, 8, f'Piezas colocadas: {total_colocadas} de {total_pedidas} | Eficiencia: {ef:.2f}%', ln=True, align='C')
    pdf.ln(10)
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'MAPA DE CORTES LONGITUDINALES', ln=True)
    fig = _graficar_mapa_longitudinal(slices, ancho_bloque)
    pdf.image(_fig_to_png(fig, dpi=130), x=10, w=190)
    plt.close(fig)
    
    for i, s in enumerate(slices):
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        modelos = ', '.join(sorted(set(p['id'] for p in s['piezas'])))
        pdf.cell(0, 10, f'REBANADA {i+1}: {s["z_inicio"]:.1f} cm a {s["z_fin"]:.1f} cm', ln=True)
        pdf.set_font('Helvetica', '', 11)
        pdf.cell(0, 7, f'Longitud de corte: {s["longitud"]:.1f} cm | Modelos: {modelos}', ln=True)
        pdf.cell(0, 7, f'Piezas en esta rebanada: {len(s["piezas"])}', ln=True)
        pdf.ln(5)
        
        fig_t = _graficar_rebanada(s, ancho_bloque)
        pdf.image(_fig_to_png(fig_t, dpi=120), x=10, w=190)
        plt.close(fig_t)
        
    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

# ==========================================
# 🖥️ INTERFAZ
# ==========================================
st.title("📦 Calculador EPS Covintec")
st.caption(f"⚙️ Kerf: {KERF_CM*10:.0f}mm | v25.0 - Empaquetado 3D Guillotina Real")

if not FPDF_DISPONIBLE:
    st.warning("⚠️ **fpdf2 no está instalado.** Instala con `pip install fpdf2` y agrega a `requirements.txt` para habilitar PDFs.")

tab1, tab2 = st.tabs(["🔹 Single (Pieza Única)", "🔹 Mix (Empaquetado 3D Real)"])

with tab1:
    st.header("Cálculo de Pieza Única")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Parámetros")
        modo_optimo = st.checkbox("🔍 Calcular Ancho Óptimo (126-156)", value=False)
        ancho_slider = 130 if modo_optimo else st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_single")
        st.markdown("### 📐 Dimensiones (cm)")
        d1, d2, d3 = st.number_input("Medida 1", value=5.0, key="s_d1"), st.number_input("Medida 2", value=61.0, key="s_d2"), st.number_input("Medida 3", value=122.0, key="s_d3")
        st.markdown("### ⚖️ Densidad y Geometría")
        densidad = st.selectbox("Densidad EPS (kg/m³)", list(range(7, 20)), index=3, key="densidad_single")
        modo_bovedilla = st.checkbox("🔸 Activar modo Bovedilla", value=False, key="bov_single")
        fp = 20.0 if not modo_bovedilla else st.slider("Pérdida perfilado (%)", 5.0, 35.0, 20.0, 1.0, key="fp_single")
        modo_uniforme = st.checkbox("✅ Acomodo Operativo", value=True, key="uni_single")
        calc = st.button("🚀 Calcular", type="primary", use_container_width=True, key="btn_single")

    with col2:
        if calc:
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
                vg, vk, vb = r['vol_gross_m3'], r['vol_kerf_m3'], r['vol_bloque_m3']
                vpr = vg * (fp/100) if modo_bovedilla else 0.0
                vn, vr = vg - vpr, max(0, vb - vg - vk)
                pn, pp, pk, pr = [(v/vb)*100 for v in [vn, vpr, vk, vr]]
                wn, wp, wk, wr = [(v*densidad) for v in [vn, vpr, vk, vr]]
                
                st.info(f"📋 **Estrategia:** {'Operativo' if modo_uniforme else 'Matemático'} | **Largo:** `{r['lp']:.0f} cm`")
                c1,c2,c3 = st.columns(3)
                c1.metric("📦 Total Piezas", r['total']); c2.metric("📈 Eficiencia", f"{(vg/vb)*100:.2f}%"); c3.metric("🧱 Peso Neto", f"{wn:.2f} kg")
                st.divider()
                st.markdown(f"🔵 **Neto:** `{pn:.2f}%` → `{vn:.4f} m³` | 🔴 **Kerf:** `{pk:.2f}%` → `{vk:.4f} m³` | ⬜ **Restante:** `{pr:.2f}%` → `{vr:.4f} m³`")
                if modo_bovedilla: st.markdown(f"🔸 **Bovedilla:** `{pp:.2f}%` → `{vpr:.4f} m³`")
                st.success(f"✅ Verificación: {vn:.4f} + {vpr:.4f} + {vk:.4f} + {vr:.4f} ≈ `{vb:.4f} m³`")
                st.pyplot(_graficar_single(r))
                
                if FPDF_DISPONIBLE:
                    pdf_bytes = _generar_reporte_pdf_single(r, d1, d2, d3, densidad, fp, modo_bovedilla, modo_uniforme)
                    st.download_button("📄 Descargar PDF (Single)", data=pdf_bytes, file_name=f"single_{int(d1)}x{int(d2)}.pdf", mime="application/pdf", use_container_width=True)

with tab2:
    st.header("🔀 Empaquetado 3D Real (Mezcla de diferentes largos)")
    st.markdown("🔹 **Algoritmo Guillotina:** Coloca las piezas grandes primero y usa los huecos restantes para las pequeñas. 🔹 Permite rotar piezas para encajar.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Configuración")
        ancho_mix = st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_mix") # Default 126 para el ejemplo del usuario
        densidad_mix = st.selectbox("Densidad (kg/m³)", list(range(7, 20)), index=3, key="densidad_mix")
        
        st.markdown("### 📋 Lista de Pedidos")
        st.caption("💡 Ejemplo: 25x40x40 y 2.5x122x244")
        default_prod = [
            {'id':'Grande','w':25.0,'h':40.0,'d':40.0,'qty':10,'color':'#3498DB'},
            {'id':'Larga1','w':2.5,'h':122.0,'d':244.0,'qty':2,'color':'#E74C3C'},
            {'id':'Larga2','w':2.5,'h':122.0,'d':122.0,'qty':2,'color':'#F39C12'}
        ]
        if 'prod_mix' not in st.session_state:
            st.session_state['prod_mix'] = default_prod
            
        edited_df = st.data_editor(
            st.session_state['prod_mix'],
            column_config={
                "id": st.column_config.TextColumn("ID", width="small"),
                "w": st.column_config.NumberColumn("Ancho (cm)", format="%.2f", step=0.5, width="small"),
                "h": st.column_config.NumberColumn("Alto (cm)", format="%.2f", step=0.5, width="small"),
                "d": st.column_config.NumberColumn("Largo (cm)", format="%.1f", step=0.5, width="small"),
                "qty": st.column_config.NumberColumn("Cant.", format="%d", step=1, width="small"),
                "color": st.column_config.TextColumn("Color", width="small")
            },
            hide_index=True, num_rows="dynamic", use_container_width=True, key="editor_mix_3d"
        )
        if edited_df != st.session_state['prod_mix']:
            st.session_state['prod_mix'] = edited_df
            
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ Agregar", use_container_width=True, key="btn_add_3d"):
                st.session_state['prod_mix'].append({'id': f'N{len(st.session_state["prod_mix"])+1}', 'w': 0.0, 'h': 0.0, 'd': 0.0, 'qty': 1, 'color': '#808080'})
                st.rerun()
        with col_btn2:
            if st.button("🗑️ Limpiar", use_container_width=True, key="btn_clear_3d"):
                st.session_state['prod_mix'] = []
                st.rerun()
                
        calc_mix = st.button("🚀 Empaquetar en 3D", type="primary", use_container_width=True, key="btn_mix_3d")
        if calc_mix:
            st.session_state['mix_3d_calculado'] = True

    with col2:
        if st.session_state.get('mix_3d_calculado', False):
            st.subheader("📊 Resultados del Empaquetado 3D")
            
            items_list = []
            total_pedidas = 0
            for row in st.session_state['prod_mix']:
                try:
                    w, h, d = float(row['w']), float(row['h']), float(row['d'])
                    qty = int(row['qty'])
                except: continue
                if qty <= 0 or w <= 0 or h <= 0 or d <= 0: continue
                if d > LARGO_BLOQUE or w > ancho_mix or h > ALTO_BLOQUE:
                    st.error(f"❌ {row['id']} excede dimensiones del bloque ({ancho_mix}x{ALTO_BLOQUE}x{LARGO_BLOQUE})")
                    continue
                items_list.append({'w': w, 'h': h, 'd': d, 'id': row['id'], 'color': row['color'], 'qty': qty})
                total_pedidas += qty

            if not items_list:
                st.warning("⚠️ No hay piezas válidas."); st.stop()

            # EJECUCIÓN DEL ALGORITMO 3D
            placed, remaining_spaces = _pack_3d_guillotine(items_list, ancho_mix, ALTO_BLOQUE, LARGO_BLOQUE)
            slices = _agrupar_por_rebanada(placed, ancho_mix)
            
            total_colocadas = len(placed)
            vol_colocado = sum(p['w']*p['h']*p['d'] for p in placed) / 1e6
            vol_bloque = ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
            eficiencia = (vol_colocado / vol_bloque) * 100
            
            st.success(f"✅ **Colocadas:** {total_colocadas} de {total_pedidas} piezas | **Eficiencia:** {eficiencia:.2f}%")
            if total_colocadas < total_pedidas:
                st.warning(f"⚠️ {total_pedidas - total_colocadas} piezas no cupieron en el bloque. Considera aumentar el ancho o usar un segundo bloque.")

            c1, c2, c3 = st.columns(3)
            c1.metric("📦 Piezas Colocadas", total_colocadas)
            c2.metric("📈 Eficiencia Volumétrica", f"{eficiencia:.2f}%")
            c3.metric("🧱 Peso Neto", f"{vol_colocado * densidad_mix:.2f} kg")

            # Botón PDF
            if FPDF_DISPONIBLE:
                pdf_bytes = _generar_reporte_pdf_mix(slices, ancho_mix, densidad_mix, total_pedidas, total_colocadas)
                st.download_button("📄 Descargar PDF (Mix 3D)", data=pdf_bytes, file_name=f"mix_3d_{len(slices)}rebanadas.pdf", mime="application/pdf", use_container_width=True)

            st.divider()
            st.subheader("📏 Mapa de Cortes Longitudinales")
            st.markdown("Este gráfico muestra a qué distancia cortar el bloque de 506 cm y qué modelos van en cada rebanada.")
            st.pyplot(_graficar_mapa_longitudinal(slices, ancho_mix))
            
            st.subheader("🔍 Detalle por Rebanada")
            for i, s in enumerate(slices):
                with st.expander(f"Rebanada {i+1}: {s['z_inicio']:.1f} cm a {s['z_fin']:.1f} cm (Largo: {s['longitud']:.1f} cm) - {len(s['piezas'])} piezas", expanded=(i==0)):
                    modelos = ', '.join(sorted(set(p['id'] for p in s['piezas'])))
                    st.write(f"**Modelos en esta rebanada:** {modelos}")
                    st.pyplot(_graficar_rebanada(s, ancho_mix))

st.markdown("---")
st.caption("💡 *Covintec v25.0 | Empaquetado 3D Guillotina: Rellena huecos automáticamente para máxima eficiencia.*")