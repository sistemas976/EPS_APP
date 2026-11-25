#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CALCULADOR EPS WEB v27.0 - MULTI-BLOQUE AUTOMÁTICO
- Calcula cuántos bloques necesitas automáticamente
- Distribuye piezas en múltiples bloques mezclando tipos
- Resumen consolidado + detalle por bloque
- Estrategia: alterna tipos para mezcla equilibrada
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
from collections import defaultdict
from itertools import permutations

try:
    from fpdf import FPDF
    FPDF_DISPONIBLE = True
except ImportError:
    FPDF_DISPONIBLE = False

KERF_CM = 0.2
ALTO_BLOQUE = 66.0
LARGO_BLOQUE = 506.0

st.set_page_config(page_title="📦 Calculador EPS Covintec", layout="wide")

# ==========================================
# 🧠 MOTOR SINGLE (Intacto)
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
# 🔄 MOTOR MIX v27.0: MULTI-BLOQUE AUTOMÁTICO
# ==========================================
class Space3D:
    __slots__ = ('x','y','z','w','h','d')
    def __init__(self, x, y, z, w, h, d):
        self.x, self.y, self.z = x, y, z
        self.w, self.h, self.d = w, h, d

def _pieza_cabe_en_bloque(w, h, d, ancho_bloque):
    dims_pieza = sorted([w, h, d])
    dims_bloque = sorted([ancho_bloque, ALTO_BLOQUE, LARGO_BLOQUE])
    return all(p <= b + 0.01 for p, b in zip(dims_pieza, dims_bloque))

def _llenar_un_bloque(items_pendientes, block_w, block_h, block_d):
    """
    Llena UN bloque con piezas pendientes.
    Alterna entre tipos para mezcla equilibrada.
    Retorna: (piezas_colocadas, items_pendientes_actualizados)
    """
    placed = []
    spaces = [Space3D(0, 0, 0, block_w, block_h, block_d)]
    
    # Estrategia: rotar entre tipos de piezas
    tipo_actual = 0
    max_intentos = 500  # Límite para evitar loops infinitos
    intentos = 0
    
    while spaces and intentos < max_intentos:
        intentos += 1
        
        # Encontrar el siguiente tipo con piezas pendientes
        tipos_con_pendientes = [i for i, item in enumerate(items_pendientes) if item['pendientes'] > 0]
        if not tipos_con_pendientes:
            break
        
        # Rotar entre tipos
        tipo_actual = tipos_con_pendientes[tipo_actual % len(tipos_con_pendientes)]
        item = items_pendientes[tipo_actual]
        
        if item['pendientes'] <= 0:
            tipo_actual += 1
            continue
        
        # Ordenar espacios por volumen descendente
        spaces.sort(key=lambda s: s.w*s.h*s.d, reverse=True)
        
        # Buscar el mejor espacio para esta pieza
        best_space_idx = -1
        best_orient = None
        best_score = float('inf')
        
        orientaciones = list(set(permutations([item['w'], item['h'], item['d']])))
        
        for i, space in enumerate(spaces):
            for orient in orientaciones:
                pw, ph, pd = orient
                if pw <= space.w + 0.01 and ph <= space.h + 0.01 and pd <= space.d + 0.01:
                    # Score: minimizar espacio desperdiciado
                    wasted = (space.w - pw) + (space.h - ph) + (space.d - pd)
                    if wasted < best_score:
                        best_score = wasted
                        best_space_idx = i
                        best_orient = orient
        
        if best_space_idx == -1:
            # Esta pieza no cabe en ningún espacio, probar siguiente tipo
            tipo_actual += 1
            continue
        
        space = spaces.pop(best_space_idx)
        pw, ph, pd = best_orient
        
        placed.append({
            'x': space.x, 'y': space.y, 'z': space.z,
            'w': pw, 'h': ph, 'd': pd,
            'id': item['id'], 'color': item['color']
        })
        item['pendientes'] -= 1
        
        # Dividir espacio restante (Guillotina sin solapamiento)
        rem_w = space.w - pw - KERF_CM
        if rem_w > 2:
            spaces.append(Space3D(space.x + pw + KERF_CM, space.y, space.z,
                                   rem_w, space.h, space.d))
        rem_h = space.h - ph - KERF_CM
        if rem_h > 2:
            spaces.append(Space3D(space.x, space.y + ph + KERF_CM, space.z,
                                   pw, rem_h, space.d))
        rem_d = space.d - pd - KERF_CM
        if rem_d > 2:
            spaces.append(Space3D(space.x, space.y, space.z + pd + KERF_CM,
                                   pw, ph, rem_d))
        
        # Limitar espacios para rendimiento
        if len(spaces) > 80:
            spaces.sort(key=lambda s: s.w*s.h*s.d, reverse=True)
            del spaces[80:]
        
        tipo_actual += 1
    
    return placed

def _distribuir_en_multiples_bloques(items_list, block_w, block_h, block_d):
    """
    Distribuye todas las piezas en múltiples bloques automáticamente.
    """
    # Copia de items con contador de pendientes
    items_pendientes = []
    for item in items_list:
        items_pendientes.append({
            'w': item['w'], 'h': item['h'], 'd': item['d'],
            'id': item['id'], 'color': item['color'],
            'qty': item['qty'], 'pendientes': item['qty']
        })
    
    bloques = []
    bloque_num = 1
    
    # Mientras haya piezas pendientes
    while any(item['pendientes'] > 0 for item in items_pendientes):
        placed = _llenar_un_bloque(items_pendientes, block_w, block_h, block_d)
        
        if not placed:
            break  # No se pudo colocar nada más
        
        bloques.append({
            'numero': bloque_num,
            'piezas': placed,
            'total_piezas': len(placed)
        })
        bloque_num += 1
        
        # Límite de seguridad
        if bloque_num > 100:
            break
    
    return bloques, items_pendientes

def _verificar_no_solapamiento(placed):
    n = len(placed)
    if n > 800:
        return True, 0
    conflictos = 0
    for i in range(n):
        a = placed[i]
        for j in range(i+1, n):
            b = placed[j]
            if (a['x'] < b['x']+b['w']-0.05 and b['x'] < a['x']+a['w']-0.05 and
                a['y'] < b['y']+b['h']-0.05 and b['y'] < a['y']+a['h']-0.05 and
                a['z'] < b['z']+b['d']-0.05 and b['z'] < a['z']+a['d']-0.05):
                conflictos += 1
                if conflictos > 5:
                    return False, conflictos
    return conflictos == 0, conflictos

def _agrupar_por_filete(placed):
    filetes = defaultdict(list)
    for p in placed:
        filetes[round(p['z'], 1)].append(p)
    out = []
    for z in sorted(filetes.keys()):
        piezas = filetes[z]
        max_d = max(p['d'] for p in piezas)
        out.append({'z_inicio': z, 'longitud': max_d, 'z_fin': z + max_d, 'piezas': piezas})
    return out

def _graficar_filete(filete_data, ancho_bloque):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, ancho_bloque); ax.set_ylim(0, ALTO_BLOQUE)
    ax.set_aspect('equal'); ax.grid(ls=':', alpha=0.4)
    modelos = sorted(set(p['id'] for p in filete_data['piezas']))
    ax.set_title(f"Filete {filete_data['z_inicio']:.1f}-{filete_data['z_fin']:.1f} cm (largo {filete_data['longitud']:.1f})\n{', '.join(modelos)}",
                 fontsize=11, fontweight='bold')
    for p in filete_data['piezas']:
        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], fc=p['color'], ec='white', lw=1.5, alpha=0.9))
        if p['w'] > 5 and p['h'] > 3:
            ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['id'], ha='center', va='center', c='white', fontweight='bold', fontsize=8)
    ax.set_xlabel("Ancho (cm)"); ax.set_ylabel("Alto (cm)")
    plt.tight_layout(); return fig

def _graficar_mapa_longitudinal(filetes, ancho_bloque):
    fig, ax = plt.subplots(figsize=(15, 3))
    ax.set_xlim(0, LARGO_BLOQUE); ax.set_ylim(0, 10); ax.axis('off')
    ax.add_patch(patches.Rectangle((0, 0), LARGO_BLOQUE, 10, facecolor='#F0F2F6', edgecolor='#333', lw=2))
    x_actual = 0
    for f in filetes:
        longitud = f['longitud']
        modelos = sorted(set(p['id'] for p in f['piezas']))
        color = f['piezas'][0]['color']
        ax.add_patch(patches.Rectangle((x_actual, 0), longitud, 10, facecolor=color, alpha=0.85, edgecolor='white', lw=2))
        fs = 9 if longitud > 40 else 7
        ax.text(x_actual + longitud/2, 5, f"{', '.join(modelos)}\n{longitud:.1f} cm",
                ha='center', va='center', fontsize=fs, fontweight='bold', color='white')
        if x_actual > 0:
            ax.plot([x_actual, x_actual], [0, 10], color='red', ls='-', lw=2, alpha=0.7)
        x_actual += longitud + KERF_CM
    if x_actual - KERF_CM < LARGO_BLOQUE - 0.5:
        res = LARGO_BLOQUE - (x_actual - KERF_CM)
        ax.add_patch(patches.Rectangle((x_actual - KERF_CM, 0), res, 10, facecolor='#FADBD8', edgecolor='#C0392B', hatch='||', alpha=0.7, lw=2))
        ax.text(x_actual - KERF_CM + res/2, 5, f"RESIDUO\n{res:.1f} cm", ha='center', va='center', fontsize=9, color='#C0392B', fontweight='bold')
    ax.set_xticks([0, 100, 200, 300, 400, 506]); ax.tick_params(axis='x', colors='gray', labelsize=8)
    ax.set_title(f"MAPA DE CORTES (506 cm) | Ancho {ancho_bloque} cm", fontsize=12, fontweight='bold', pad=8)
    plt.tight_layout(); return fig

# ==========================================
# 📄 PDF
# ==========================================
def _fig_to_png(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0); return buf

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
    pdf.cell(0, 7, f'Total piezas: {r["total"]} | Capas: {r["capas"]} | Pz/capa: {r["ps"]}', ln=True)
    pdf.cell(0, 7, f'Eficiencia: {(vg/vb)*100:.2f}% | Volumen: {vg:.4f} m3 | Peso bloque: {wt:.2f} kg', ln=True)
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
    for i, h in enumerate(['Concepto', '%', 'Volumen (m3)', 'Peso (kg)', 'Descripcion']):
        pdf.cell(col_w[i], 7, h, border=1, align='C')
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
    pdf_buffer = io.BytesIO(); pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

def _generar_reporte_pdf_mix(bloques, ancho_bloque, densidad, total_pedidas, total_colocadas, vol_total_colocado):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    vol_bloque_unitario = ancho_bloque * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
    vol_total_bloques = len(bloques) * vol_bloque_unitario
    ef = (vol_total_colocado / vol_total_bloques * 100) if vol_total_bloques > 0 else 0
    
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 22)
    pdf.cell(0, 20, 'Reporte EPS - Mezcla 3D Multi-Bloque', ln=True, align='C')
    pdf.set_font('Helvetica', '', 13)
    pdf.cell(0, 10, f'Bloque unitario: {ancho_bloque} x {ALTO_BLOQUE} x {LARGO_BLOQUE} cm', ln=True, align='C')
    pdf.cell(0, 8, f'Total bloques: {len(bloques)}', ln=True, align='C')
    pdf.cell(0, 8, f'Piezas: {total_colocadas} de {total_pedidas} | Eficiencia global: {ef:.2f}%', ln=True, align='C')
    pdf.cell(0, 8, f'Peso total: {vol_total_colocado*densidad:.2f} kg', ln=True, align='C')
    pdf.ln(10)
    
    for bloque in bloques:
        filetes = _agrupar_por_filete(bloque['piezas'])
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, f'BLOQUE {bloque["numero"]} - {bloque["total_piezas"]} piezas', ln=True)
        pdf.ln(5)
        
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'Mapa de cortes longitudinales', ln=True)
        fig = _graficar_mapa_longitudinal(filetes, ancho_bloque)
        pdf.image(_fig_to_png(fig, dpi=130), x=10, w=190)
        plt.close(fig)
        pdf.ln(5)
        
        for i, f in enumerate(filetes):
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 14)
            modelos = ', '.join(sorted(set(p['id'] for p in f['piezas'])))
            pdf.cell(0, 10, f'FILETE {i+1}: {f["z_inicio"]:.1f} a {f["z_fin"]:.1f} cm', ln=True)
            pdf.set_font('Helvetica', '', 11)
            pdf.cell(0, 7, f'Largo: {f["longitud"]:.1f} cm | Modelos: {modelos} | Piezas: {len(f["piezas"])}', ln=True)
            pdf.ln(5)
            fig_t = _graficar_filete(f, ancho_bloque)
            pdf.image(_fig_to_png(fig_t, dpi=120), x=10, w=190)
            plt.close(fig_t)
    
    pdf_buffer = io.BytesIO(); pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

# ==========================================
# 🖥️ INTERFAZ
# ==========================================
st.title("📦 Calculador EPS Covintec")
st.caption(f"⚙️ Kerf: {KERF_CM*10:.0f}mm | v27.0 - Multi-bloque automático")

if not FPDF_DISPONIBLE:
    st.warning("⚠️ **fpdf2 no está instalado.** Agrega `fpdf2` a `requirements.txt` para habilitar PDFs.")

tab1, tab2 = st.tabs(["🔹 Single (Pieza Única)", "🔹 Mix (Multi-Bloque Automático)"])

with tab1:
    st.header("Cálculo de Pieza Única")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Parámetros")
        modo_optimo = st.checkbox("🔍 Calcular Ancho Óptimo (126-156)", value=False)
        ancho_slider = 130 if modo_optimo else st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_single")
        st.markdown("### 📐 Dimensiones (cm)")
        d1 = st.number_input("Medida 1", value=5.0, key="s_d1")
        d2 = st.number_input("Medida 2", value=61.0, key="s_d2")
        d3 = st.number_input("Medida 3", value=122.0, key="s_d3")
        st.markdown("### ⚖️ Densidad y Geometría")
        densidad = st.selectbox("Densidad EPS (kg/m³)", list(range(7, 20)), index=3, key="densidad_single")
        modo_bovedilla = st.checkbox("🔸 Activar modo Bovedilla", value=False, key="bov_single")
        fp = 20.0
        if modo_bovedilla: fp = st.slider("Pérdida perfilado (%)", 5.0, 35.0, 20.0, 1.0, key="fp_single")
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
                c1.metric("📦 Total Piezas", r['total'])
                c2.metric("📈 Eficiencia", f"{(vg/vb)*100:.2f}%")
                c3.metric("🧱 Peso Neto", f"{wn:.2f} kg")
                st.divider()
                st.markdown(f"🔵 **Neto:** `{pn:.2f}%` → `{vn:.4f} m³` → `{wn:.2f} kg`")
                if modo_bovedilla: st.markdown(f"🔸 **Bovedilla:** `{pp:.2f}%` → `{vpr:.4f} m³` → `{wp:.2f} kg`")
                st.markdown(f"🔴 **Kerf:** `{pk:.2f}%` → `{vk:.4f} m³` → `{wk:.2f} kg`")
                st.markdown(f"⬜ **Restante:** `{pr:.2f}%` → `{vr:.4f} m³` → `{wr:.2f} kg`")
                st.success(f"✅ Verificación: {vn:.4f}+{vpr:.4f}+{vk:.4f}+{vr:.4f} ≈ `{vb:.4f} m³`")
                st.pyplot(_graficar_single(r))
                if FPDF_DISPONIBLE:
                    pdf_bytes = _generar_reporte_pdf_single(r, d1, d2, d3, densidad, fp, modo_bovedilla, modo_uniforme)
                    st.download_button("📄 Descargar PDF (Single)", data=pdf_bytes,
                                       file_name=f"single_{int(d1)}x{int(d2)}.pdf", mime="application/pdf", use_container_width=True)

with tab2:
    st.header("🔀 Empaquetado 3D Multi-Bloque Automático")
    st.markdown("🔹 **Distribución automática:** calcula cuántos bloques necesitas y distribuye las piezas. 🔹 Mezcla tipos en cada bloque.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Configuración")
        ancho_mix = st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_mix")
        densidad_mix = st.selectbox("Densidad (kg/m³)", list(range(7, 20)), index=3, key="densidad_mix")

        st.markdown("### 📋 Lista de Pedidos")
        st.caption("💡 Dim1/Dim2/Dim3 = las 3 medidas. El sistema prueba las 6 orientaciones.")
        default_prod = [
            {'id':'Grande','w':25.0,'h':40.0,'d':40.0,'qty':1000,'color':'#3498DB'},
            {'id':'Larga1','w':2.5,'h':122.0,'d':244.0,'qty':1000,'color':'#E74C3C'},
            {'id':'Larga2','w':2.5,'h':122.0,'d':122.0,'qty':200,'color':'#F39C12'}
        ]
        if 'prod_mix' not in st.session_state:
            st.session_state['prod_mix'] = default_prod
        edited_df = st.data_editor(
            st.session_state['prod_mix'],
            column_config={
                "id": st.column_config.TextColumn("ID", width="small"),
                "w": st.column_config.NumberColumn("Dim1 (cm)", format="%.2f", step=0.5, width="small"),
                "h": st.column_config.NumberColumn("Dim2 (cm)", format="%.2f", step=0.5, width="small"),
                "d": st.column_config.NumberColumn("Dim3 (cm)", format="%.1f", step=0.5, width="small"),
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
        calc_mix = st.button("🚀 Distribuir en Bloques", type="primary", use_container_width=True, key="btn_mix_3d")
        if calc_mix:
            st.session_state['mix_3d_calculado'] = True

    with col2:
        if st.session_state.get('mix_3d_calculado', False):
            st.subheader("📊 Resultados Multi-Bloque")
            items_list = []
            total_pedidas = 0
            vol_total_solicitado = 0
            for row in st.session_state['prod_mix']:
                try:
                    w, h, d = float(row['w']), float(row['h']), float(row['d'])
                    qty = int(row['qty'])
                except: continue
                if qty <= 0 or w <= 0 or h <= 0 or d <= 0: continue
                if not _pieza_cabe_en_bloque(w, h, d, ancho_mix):
                    st.error(f"❌ {row['id']} ({w}x{h}x{d}) no cabe en bloque {ancho_mix}x{ALTO_BLOQUE}x{LARGO_BLOQUE}")
                    continue
                items_list.append({'w': w, 'h': h, 'd': d, 'id': row['id'], 'color': row['color'], 'qty': qty})
                total_pedidas += qty
                vol_total_solicitado += w * h * d * qty
            
            if not items_list:
                st.warning("⚠️ No hay piezas válidas."); st.stop()
            
            # Calcular bloques necesarios (estimación)
            vol_bloque_unitario = ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE
            bloques_estimados = math.ceil(vol_total_solicitado / vol_bloque_unitario)
            st.info(f"📐 **Estimación:** necesitas ~{bloques_estimados} bloques para colocar todas las piezas")
            
            # Distribuir en múltiples bloques
            with st.spinner(f"Distribuyendo en ~{bloques_estimados} bloques..."):
                bloques, items_finales = _distribuir_en_multiples_bloques(items_list, ancho_mix, ALTO_BLOQUE, LARGO_BLOQUE)
            
            # Calcular totales
            total_colocadas = sum(b['total_piezas'] for b in bloques)
            vol_total_colocado = sum(sum(p['w']*p['h']*p['d'] for p in b['piezas']) for b in bloques) / 1e6
            vol_total_bloques = len(bloques) * vol_bloque_unitario / 1e6
            eficiencia_global = (vol_total_colocado / vol_total_bloques * 100) if vol_total_bloques > 0 else 0
            
            st.success(f"✅ **Distribuidas:** {total_colocadas} de {total_pedidas} piezas en **{len(bloques)} bloques** | Eficiencia global: {eficiencia_global:.2f}%")
            
            # Detalle por tipo
            st.markdown("#### 📦 Detalle por tipo de pieza:")
            for item in items_list:
                colocadas = sum(1 for b in bloques for p in b['piezas'] if p['id'] == item['id'])
                pedidas = item['qty']
                (st.success if colocadas == pedidas else st.warning)(
                    f"**{item['id']}** ({item['w']}x{item['h']}x{item['d']}): {colocadas} de {pedidas} colocadas"
                )
            
            if total_colocadas < total_pedidas:
                st.warning(f"⚠️ {total_pedidas - total_colocadas} piezas no se pudieron colocar (límite de 100 bloques)")
            
            # Métricas globales
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🧱 Bloques Usados", len(bloques))
            c2.metric("📦 Piezas Colocadas", total_colocadas)
            c3.metric("📈 Eficiencia Global", f"{eficiencia_global:.2f}%")
            c4.metric("🧱 Peso Total", f"{vol_total_colocado * densidad_mix:.2f} kg")
            
            # PDF
            if FPDF_DISPONIBLE:
                pdf_bytes = _generar_reporte_pdf_mix(bloques, ancho_mix, densidad_mix, total_pedidas, total_colocadas, vol_total_colocado)
                st.download_button("📄 Descargar PDF (Multi-Bloque)", data=pdf_bytes,
                                   file_name=f"mix_multibloque_{len(bloques)}bloques.pdf", mime="application/pdf", use_container_width=True)
            
            # Selector de bloque
            if len(bloques) > 1:
                st.divider()
                st.subheader("🔍 Ver detalle por bloque")
                bloque_sel = st.selectbox("Selecciona un bloque:", [f"Bloque {b['numero']} ({b['total_piezas']} piezas)" for b in bloques], key="sel_bloque_detalle")
                bloque_idx = [f"Bloque {b['numero']} ({b['total_piezas']} piezas)" for b in bloques].index(bloque_sel)
                bloque = bloques[bloque_idx]
            else:
                bloque = bloques[0]
            
            filetes = _agrupar_por_filete(bloque['piezas'])
            
            # Verificación anti-solapamiento (solo para bloques pequeños)
            if bloque['total_piezas'] <= 800:
                ok, conflictos = _verificar_no_solapamiento(bloque['piezas'])
                if not ok:
                    st.error(f"🚨 Bloque {bloque['numero']}: {conflictos} piezas se solapan")
                else:
                    st.success(f"✔️ Bloque {bloque['numero']}: verificación OK")
            
            st.subheader(f"📏 Bloque {bloque['numero']} - Mapa de Cortes")
            st.pyplot(_graficar_mapa_longitudinal(filetes, ancho_mix))
            
            st.subheader("🔍 Filetes del bloque")
            for i, f in enumerate(filetes):
                with st.expander(f"Filete {i+1}: {f['z_inicio']:.1f}-{f['z_fin']:.1f} cm | {len(f['piezas'])} piezas", expanded=(i==0)):
                    st.pyplot(_graficar_filete(f, ancho_mix))

st.markdown("---")
st.caption("💡 *Covintec v27.0 | Multi-bloque automático: distribuye piezas en todos los bloques necesarios.*")