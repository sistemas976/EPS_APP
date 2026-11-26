#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CALCULADOR EPS WEB v28.0 - PLANOS DE CORTE INDUSTRIALES
- 3 vistas ortogonales por bloque (frontal, lateral, longitudinal)
- PDF de UN bloque: 1 sola página
- PDF consolidado: 2-3 páginas con tablas de todos los bloques
- Reduce de 154 páginas a 1-3 páginas
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
import time
from collections import defaultdict
from itertools import permutations
import heapq

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
# 🔄 MOTOR MIX v28.0
# ==========================================
class Space3D:
    __slots__ = ('x','y','z','w','h','d','vol')
    def __init__(self, x, y, z, w, h, d):
        self.x, self.y, self.z = x, y, z
        self.w, self.h, self.d = w, h, d
        self.vol = w * h * d

def _pieza_cabe_en_bloque(w, h, d, ancho_bloque):
    dims_pieza = sorted([w, h, d])
    dims_bloque = sorted([ancho_bloque, ALTO_BLOQUE, LARGO_BLOQUE])
    return all(p <= b + 0.01 for p, b in zip(dims_pieza, dims_bloque))

def _llenar_un_bloque_mezcla_real(items_pendientes, block_w, block_h, block_d):
    placed = []
    counter = 0
    spaces_heap = [(-block_w*block_h*block_d, counter, Space3D(0, 0, 0, block_w, block_h, block_d))]
    counter += 1
    tipo_actual = 0
    max_intentos = 300
    intentos = 0
    MAX_SPACES = 50
    
    while spaces_heap and intentos < max_intentos:
        intentos += 1
        tipos_con_pendientes = [i for i, item in enumerate(items_pendientes) if item['pendientes'] > 0]
        if not tipos_con_pendientes: break
        tipo_actual = tipos_con_pendientes[tipo_actual % len(tipos_con_pendientes)]
        item = items_pendientes[tipo_actual]
        if item['pendientes'] <= 0:
            tipo_actual += 1
            continue
        best_space_idx = -1
        best_orient = None
        best_score = float('inf')
        orientaciones = list(set(permutations([item['w'], item['h'], item['d']])))
        espacios_a_probar = min(20, len(spaces_heap))
        temp_spaces = []
        for _ in range(espacios_a_probar):
            if not spaces_heap: break
            neg_vol, cnt, space = heapq.heappop(spaces_heap)
            temp_spaces.append((neg_vol, cnt, space))
            for orient in orientaciones:
                pw, ph, pd = orient
                if pw <= space.w + 0.01 and ph <= space.h + 0.01 and pd <= space.d + 0.01:
                    wasted = (space.w - pw) + (space.h - ph) + (space.d - pd)
                    if wasted < best_score:
                        best_score = wasted
                        best_space_idx = len(temp_spaces) - 1
                        best_orient = orient
        for idx, (neg_vol, cnt, space) in enumerate(temp_spaces):
            if idx != best_space_idx:
                heapq.heappush(spaces_heap, (neg_vol, cnt, space))
        if best_space_idx == -1:
            tipo_actual += 1
            continue
        _, _, space = temp_spaces[best_space_idx]
        pw, ph, pd = best_orient
        placed.append({
            'x': space.x, 'y': space.y, 'z': space.z,
            'w': pw, 'h': ph, 'd': pd,
            'id': item['id'], 'color': item['color']
        })
        item['pendientes'] -= 1
        rem_w = space.w - pw - KERF_CM
        if rem_w > 2:
            new_space = Space3D(space.x + pw + KERF_CM, space.y, space.z, rem_w, space.h, space.d)
            heapq.heappush(spaces_heap, (-new_space.vol, counter, new_space)); counter += 1
        rem_h = space.h - ph - KERF_CM
        if rem_h > 2:
            new_space = Space3D(space.x, space.y + ph + KERF_CM, space.z, pw, rem_h, space.d)
            heapq.heappush(spaces_heap, (-new_space.vol, counter, new_space)); counter += 1
        rem_d = space.d - pd - KERF_CM
        if rem_d > 2:
            new_space = Space3D(space.x, space.y, space.z + pd + KERF_CM, pw, ph, rem_d)
            heapq.heappush(spaces_heap, (-new_space.vol, counter, new_space)); counter += 1
        if len(spaces_heap) > MAX_SPACES:
            spaces_heap = heapq.nsmallest(MAX_SPACES, spaces_heap)
        tipo_actual += 1
    return placed

def _distribuir_en_multiples_bloques(items_list, block_w, block_h, block_d, progress_callback=None):
    items_pendientes = []
    for item in items_list:
        items_pendientes.append({
            'w': item['w'], 'h': item['h'], 'd': item['d'],
            'id': item['id'], 'color': item['color'],
            'qty': item['qty'], 'pendientes': item['qty']
        })
    bloques = []
    bloque_num = 1
    total_piezas = sum(item['qty'] for item in items_list)
    piezas_colocadas = 0
    while any(item['pendientes'] > 0 for item in items_pendientes):
        placed = _llenar_un_bloque_mezcla_real(items_pendientes, block_w, block_h, block_d)
        if not placed: break
        bloques.append({'numero': bloque_num, 'piezas': placed, 'total_piezas': len(placed)})
        piezas_colocadas += len(placed)
        bloque_num += 1
        if progress_callback: progress_callback(piezas_colocadas, total_piezas, bloque_num)
        if bloque_num > 100: break
    return bloques, items_pendientes

# ==========================================
# 📐 LAS 3 VISTAS ORTOGONALES (NUEVO)
# ==========================================
def _vista_frontal(placed, ancho_bloque):
    """Proyección X-Y: vista de frente del bloque."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, ancho_bloque); ax.set_ylim(0, ALTO_BLOQUE)
    ax.set_aspect('equal'); ax.grid(ls=':', alpha=0.3)
    ax.set_title("VISTA FRONTAL (proyección X-Y)\nAncho x Alto del bloque", fontsize=12, fontweight='bold')
    # Dibujar todas las piezas proyectadas (con transparencia para ver superposición)
    for p in placed:
        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'],
                                       fc=p['color'], ec='black', lw=0.8, alpha=0.35))
    # Dibujar solo la primera capa (z=0) con opacidad alta
    primera_capa = [p for p in placed if abs(p['z']) < 0.5]
    for p in primera_capa:
        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'],
                                       fc=p['color'], ec='black', lw=1.5, alpha=0.95))
        if p['w'] > 8 and p['h'] > 4:
            ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['id'],
                    ha='center', va='center', c='white', fontweight='bold', fontsize=9)
    ax.set_xlabel("Ancho (cm)"); ax.set_ylabel("Alto (cm)")
    plt.tight_layout(); return fig

def _vista_lateral(placed, ancho_bloque):
    """Proyección X-Z: vista lateral (ancho x largo)."""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, LARGO_BLOQUE); ax.set_ylim(0, ancho_bloque)
    ax.set_aspect('equal'); ax.grid(ls=':', alpha=0.3)
    ax.set_title("VISTA LATERAL (proyección Z-X)\nLargo x Ancho del bloque", fontsize=12, fontweight='bold')
    # Agrupar por z para evitar saturación
    for p in placed:
        ax.add_patch(patches.Rectangle((p['z'], p['x']), p['d'], p['w'],
                                       fc=p['color'], ec='black', lw=0.6, alpha=0.5))
    ax.set_xlabel("Largo (cm)"); ax.set_ylabel("Ancho (cm)")
    plt.tight_layout(); return fig

def _vista_longitudinal(placed, ancho_bloque):
    """Proyección Z-Y: vista longitudinal (largo x alto) = mapa de cortes."""
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, LARGO_BLOQUE); ax.set_ylim(0, ALTO_BLOQUE)
    ax.set_aspect('equal'); ax.grid(ls=':', alpha=0.3)
    ax.set_title("VISTA LONGITUDINAL (proyección Z-Y)\nLargo x Alto = Secuencia de cortes del hilo", fontsize=12, fontweight='bold')
    for p in placed:
        ax.add_patch(patches.Rectangle((p['z'], p['y']), p['d'], p['h'],
                                       fc=p['color'], ec='black', lw=0.6, alpha=0.5))
    ax.set_xlabel("Largo (cm)"); ax.set_ylabel("Alto (cm)")
    plt.tight_layout(); return fig

def _tabla_cortes_bloque(placed):
    """Genera tabla compacta de posiciones de corte únicas."""
    # Cortes transversales (en Z)
    cortes_z = sorted(set(round(p['z'], 1) for p in placed))
    # Cortes longitudinales (en Y, horizontal)
    cortes_y = sorted(set(round(p['y'], 1) for p in placed))
    # Cortes verticales (en X)
    cortes_x = sorted(set(round(p['x'], 1) for p in placed))
    return {'z': cortes_z, 'y': cortes_y, 'x': cortes_x}

def _resumen_tipos_bloque(placed):
    """Resumen de tipos de piezas en el bloque."""
    resumen = defaultdict(int)
    for p in placed:
        resumen[p['id']] += 1
    return dict(resumen)

# ==========================================
# 📄 PDF OPTIMIZADOS (NUEVO)
# ==========================================
def _fig_to_png(fig, dpi=72):
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
    pdf.cell(0, 8, f'Bloque: {r["ancho_usado"]:.0f} x {ALTO_BLOQUE:.0f} x {LARGO_BLOQUE:.0f} cm', ln=True, align='C')
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'RESUMEN', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Total piezas: {r["total"]} | Capas: {r["capas"]} | Pz/capa: {r["ps"]}', ln=True)
    pdf.cell(0, 7, f'Eficiencia: {(vg/vb)*100:.2f}% | Volumen: {vg:.4f} m3 | Peso: {wt:.2f} kg', ln=True)
    pdf.ln(5)
    fig = _graficar_single(r)
    pdf.image(_fig_to_png(fig, dpi=100), x=10, w=190)
    plt.close(fig)
    pdf_buffer = io.BytesIO(); pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

def _generar_pdf_bloque_unico(bloque, ancho_bloque, densidad, vol_colocado):
    """
    PDF de UN SOLO BLOQUE en 1-2 páginas:
    - Página 1: 3 vistas ortogonales + resumen + tabla de cortes
    - Página 2 (opcional): tabla extendida de cortes si hay muchos
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=10)
    
    vol_bloque = ancho_bloque * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
    ef = (vol_colocado / vol_bloque * 100) if vol_bloque > 0 else 0
    resumen = _resumen_tipos_bloque(bloque['piezas'])
    cortes = _tabla_cortes_bloque(bloque['piezas'])
    
    # ---- PÁGINA 1: PORTADA + VISTAS ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 10, f'PLANOS DE CORTE - BLOQUE {bloque["numero"]}', ln=True, align='C')
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Bloque: {ancho_bloque} x {ALTO_BLOQUE} x {LARGO_BLOQUE} cm | Kerf: {KERF_CM*10:.0f} mm', ln=True, align='C')
    pdf.cell(0, 7, f'Piezas: {bloque["total_piezas"]} | Eficiencia: {ef:.2f}% | Peso: {vol_colocado*densidad:.2f} kg', ln=True, align='C')
    pdf.ln(3)
    
    # Resumen de tipos
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 7, 'Piezas por tipo:', ln=True)
    pdf.set_font('Helvetica', '', 10)
    tipos_str = ' | '.join([f'{k}: {v}' for k, v in resumen.items()])
    pdf.cell(0, 6, tipos_str, ln=True)
    pdf.ln(2)
    
    # Vistas ortogonales
    fig_f = _vista_frontal(bloque['piezas'], ancho_bloque)
    pdf.image(_fig_to_png(fig_f, dpi=80), x=15, w=180)
    plt.close(fig_f)
    pdf.ln(2)
    
    fig_l = _vista_lateral(bloque['piezas'], ancho_bloque)
    pdf.image(_fig_to_png(fig_l, dpi=80), x=15, w=180)
    plt.close(fig_l)
    pdf.ln(2)
    
    fig_lo = _vista_longitudinal(bloque['piezas'], ancho_bloque)
    pdf.image(_fig_to_png(fig_lo, dpi=80), x=15, w=180)
    plt.close(fig_lo)
    
    # ---- PÁGINA 2: TABLA DE CORTES ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'TABLA DE POSICIONES DE CORTE', ln=True, align='C')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, 'Posiciones exactas donde el hilo debe atravesar el bloque (en cm desde el origen).', ln=True)
    pdf.ln(3)
    
    # Cortes Z (transversales - los principales)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 7, f'1. CORTES TRANSVERSALES (Z) - {len(cortes["z"])} cortes', ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, 'Cortes que dividen el bloque a lo largo de los 506 cm:', ln=True)
    pdf.ln(2)
    
    # Tabla de cortes Z en columnas
    n_cortes = len(cortes['z'])
    col_w = 30
    per_row = 6
    pdf.set_font('Helvetica', '', 9)
    for i in range(0, n_cortes, per_row):
        row = cortes['z'][i:i+per_row]
        for j, c in enumerate(row):
            pdf.cell(col_w, 6, f'#{i+j+1}: {c:.1f} cm', border=1, align='C')
        pdf.ln()
    pdf.ln(3)
    
    # Cortes Y (horizontales)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 7, f'2. CORTES HORIZONTALES (Y) - {len(cortes["y"])} cortes', ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, 'Cortes que dividen la altura del bloque (0-66 cm):', ln=True)
    pdf.ln(2)
    pdf.set_font('Helvetica', '', 9)
    for i in range(0, len(cortes['y']), per_row):
        row = cortes['y'][i:i+per_row]
        for j, c in enumerate(row):
            pdf.cell(col_w, 6, f'#{i+j+1}: {c:.1f} cm', border=1, align='C')
        pdf.ln()
    pdf.ln(3)
    
    # Cortes X (verticales)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 7, f'3. CORTES VERTICALES (X) - {len(cortes["x"])} cortes', ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, 'Cortes que dividen el ancho del bloque:', ln=True)
    pdf.ln(2)
    pdf.set_font('Helvetica', '', 9)
    for i in range(0, len(cortes['x']), per_row):
        row = cortes['x'][i:i+per_row]
        for j, c in enumerate(row):
            pdf.cell(col_w, 6, f'#{i+j+1}: {c:.1f} cm', border=1, align='C')
        pdf.ln()
    
    pdf_buffer = io.BytesIO(); pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

def _generar_pdf_consolidado(bloques, ancho_bloque, densidad, total_pedidas, total_colocadas, vol_total_colocado):
    """
    PDF CONSOLIDADO: 2-3 páginas con resumen tabular de TODOS los bloques.
    Sin imágenes, solo datos. Para el supervisor.
    """
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    vol_bloque_unitario = ancho_bloque * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
    vol_total_bloques = len(bloques) * vol_bloque_unitario
    ef_global = (vol_total_colocado / vol_total_bloques * 100) if vol_total_bloques > 0 else 0
    
    # ---- PÁGINA 1: RESUMEN GLOBAL ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(0, 15, 'RESUMEN CONSOLIDADO DE PRODUCCION', ln=True, align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, f'Bloque unitario: {ancho_bloque} x {ALTO_BLOQUE} x {LARGO_BLOQUE} cm', ln=True, align='C')
    pdf.cell(0, 8, f'Kerf: {KERF_CM*10:.0f} mm | Densidad: {densidad} kg/m3', ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 8, 'TOTALES GLOBALES:', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'  Total de bloques: {len(bloques)}', ln=True)
    pdf.cell(0, 7, f'  Piezas colocadas: {total_colocadas} de {total_pedidas}', ln=True)
    pdf.cell(0, 7, f'  Eficiencia global: {ef_global:.2f}%', ln=True)
    pdf.cell(0, 7, f'  Volumen util total: {vol_total_colocado:.4f} m3', ln=True)
    pdf.cell(0, 7, f'  Peso total neto: {vol_total_colocado*densidad:.2f} kg', ln=True)
    pdf.ln(5)
    
    # ---- PÁGINA 2: TABLA POR BLOQUE ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'DETALLE POR BLOQUE', ln=True, align='C')
    pdf.ln(3)
    
    col_w = [15, 20, 25, 30, 35, 35, 30]
    headers = ['Bloque', 'Piezas', 'Volumen (m3)', 'Eficiencia', 'Tipos incluidos', 'Cortes Z', 'Peso (kg)']
    pdf.set_font('Helvetica', 'B', 9)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, align='C')
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 8)
    for bloque in bloques:
        vol_b = sum(p['w']*p['h']*p['d'] for p in bloque['piezas']) / 1e6
        ef_b = (vol_b / vol_bloque_unitario * 100) if vol_bloque_unitario > 0 else 0
        resumen = _resumen_tipos_bloque(bloque['piezas'])
        tipos_str = ', '.join([f'{k}:{v}' for k, v in resumen.items()])[:30]
        cortes = _tabla_cortes_bloque(bloque['piezas'])
        n_cortes_z = len(cortes['z'])
        peso_b = vol_b * densidad
        
        row = [str(bloque['numero']), str(bloque['total_piezas']), f'{vol_b:.4f}',
               f'{ef_b:.1f}%', tipos_str, str(n_cortes_z), f'{peso_b:.2f}']
        for j, val in enumerate(row):
            pdf.cell(col_w[j], 5, val, border=1, align='C')
        pdf.ln()
    
    # ---- PÁGINA 3: RESUMEN POR TIPO DE PIEZA ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'RESUMEN POR TIPO DE PIEZA', ln=True, align='C')
    pdf.ln(3)
    
    # Acumular por tipo
    tipos_globales = defaultdict(int)
    tipos_volumen = defaultdict(float)
    for bloque in bloques:
        for p in bloque['piezas']:
            tipos_globales[p['id']] += 1
            tipos_volumen[p['id']] += p['w']*p['h']*p['d'] / 1e6
    
    col_w2 = [40, 30, 35, 35, 35]
    headers2 = ['Tipo', 'Total piezas', 'Volumen (m3)', 'Peso (kg)', '% del total']
    pdf.set_font('Helvetica', 'B', 10)
    for i, h in enumerate(headers2):
        pdf.cell(col_w2[i], 7, h, border=1, align='C')
    pdf.ln()
    
    pdf.set_font('Helvetica', '', 10)
    for tipo, total in sorted(tipos_globales.items(), key=lambda x: -x[1]):
        vol = tipos_volumen[tipo]
        peso = vol * densidad
        pct = (total / total_colocadas * 100) if total_colocadas > 0 else 0
        row = [tipo, str(total), f'{vol:.4f}', f'{peso:.2f}', f'{pct:.1f}%']
        for j, val in enumerate(row):
            pdf.cell(col_w2[j], 6, val, border=1, align='C')
        pdf.ln()
    
    pdf_buffer = io.BytesIO(); pdf.output(pdf_buffer)
    return pdf_buffer.getvalue()

# ==========================================
# 🖥️ INTERFAZ
# ==========================================
st.title("📦 Calculador EPS Covintec")
st.caption(f"⚙️ Kerf: {KERF_CM*10:.0f}mm | v28.0 - Planos de corte industriales")

if not FPDF_DISPONIBLE:
    st.warning("⚠️ **fpdf2 no está instalado.** Agrega `fpdf2` a `requirements.txt`.")

tab1, tab2 = st.tabs(["🔹 Single (Pieza Única)", "🔹 Mix (Planos Industriales)"])

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
    st.header("🔀 Empaquetado 3D con Planos Industriales")
    st.markdown("🔹 **3 vistas ortogonales** por bloque (frontal, lateral, longitudinal). 🔹 **PDF compacto:** 2 páginas por bloque en lugar de 31.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Configuración")
        ancho_mix = st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_mix")
        densidad_mix = st.selectbox("Densidad (kg/m³)", list(range(7, 20)), index=3, key="densidad_mix")

        st.markdown("### 📋 Lista de Pedidos")
        st.caption("💡 Dim1/Dim2/Dim3 = las 3 medidas.")
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
                    st.error(f"❌ {row['id']} no cabe en bloque {ancho_mix}x{ALTO_BLOQUE}x{LARGO_BLOQUE}")
                    continue
                items_list.append({'w': w, 'h': h, 'd': d, 'id': row['id'], 'color': row['color'], 'qty': qty})
                total_pedidas += qty
                vol_total_solicitado += w * h * d * qty
            
            if not items_list:
                st.warning("⚠️ No hay piezas válidas."); st.stop()
            
            vol_bloque_unitario = ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE
            bloques_estimados = math.ceil(vol_total_solicitado / (vol_bloque_unitario * 0.85))
            st.info(f"📐 **Estimación:** ~{bloques_estimados} bloques necesarios")
            
            progress_bar = st.progress(0, text="Empaquetando...")
            start_time = time.time()
            
            def progress_callback(piezas_colocadas, total_piezas, bloque_num):
                progress = piezas_colocadas / total_piezas
                progress_bar.progress(progress, text=f"Bloque {bloque_num} | {piezas_colocadas}/{total_piezas} piezas")
            
            bloques, items_finales = _distribuir_en_multiples_bloques(items_list, ancho_mix, ALTO_BLOQUE, LARGO_BLOQUE, progress_callback)
            progress_bar.progress(1.0, text="✅ Completado!")
            
            total_colocadas = sum(b['total_piezas'] for b in bloques)
            vol_total_colocado = sum(sum(p['w']*p['h']*p['d'] for p in b['piezas']) for b in bloques) / 1e6
            vol_total_bloques = len(bloques) * vol_bloque_unitario / 1e6
            eficiencia_global = (vol_total_colocado / vol_total_bloques * 100) if vol_total_bloques > 0 else 0
            
            elapsed = time.time() - start_time
            st.success(f"✅ **{elapsed:.1f} seg** | {total_colocadas}/{total_pedidas} piezas en **{len(bloques)} bloques** | Eficiencia: {eficiencia_global:.2f}%")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🧱 Bloques", len(bloques))
            c2.metric("📦 Piezas", total_colocadas)
            c3.metric("📈 Eficiencia", f"{eficiencia_global:.2f}%")
            c4.metric("🧱 Peso Total", f"{vol_total_colocado * densidad_mix:.2f} kg")
            
            st.divider()
            
            # Selector de bloque
            st.subheader("🔍 Selecciona un bloque para ver sus planos")
            nombres_bloques = [f"Bloque {b['numero']} ({b['total_piezas']} piezas)" for b in bloques]
            sel_bloque = st.selectbox("Elige bloque:", range(len(bloques)), format_func=lambda i: nombres_bloques[i], key="sel_bloque_v28")
            bloque = bloques[sel_bloque]
            
            vol_bloque_sel = sum(p['w']*p['h']*p['d'] for p in bloque['piezas']) / 1e6
            ef_bloque = (vol_bloque_sel / vol_bloque_unitario * 100) if vol_bloque_unitario > 0 else 0
            
            st.info(f"📋 **Bloque {bloque['numero']}**: {bloque['total_piezas']} piezas | Eficiencia: {ef_bloque:.2f}% | Peso: {vol_bloque_sel*densidad_mix:.2f} kg")
            
            # LAS 3 VISTAS
            st.subheader("📐 Vista FRONTAL (Ancho x Alto)")
            st.caption("Lo que ve el operario mirando el bloque de frente. Las piezas oscuras son la primera capa (z=0).")
            st.pyplot(_vista_frontal(bloque['piezas'], ancho_mix))
            
            st.subheader("📐 Vista LATERAL (Largo x Ancho)")
            st.caption("Vista desde arriba del bloque. Muestra cómo se distribuyen las piezas en el eje horizontal.")
            st.pyplot(_vista_lateral(bloque['piezas'], ancho_mix))
            
            st.subheader("📐 Vista LONGITUDINAL (Largo x Alto)")
            st.caption("Vista desde un costado. Muestra la secuencia de cortes del hilo caliente.")
            st.pyplot(_vista_longitudinal(bloque['piezas'], ancho_mix))
            
            # Tabla de cortes
            st.subheader("🔪 Tabla de Posiciones de Corte")
            cortes = _tabla_cortes_bloque(bloque['piezas'])
            resumen = _resumen_tipos_bloque(bloque['piezas'])
            
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                st.markdown(f"**Cortes transversales (Z):** {len(cortes['z'])}")
                st.write(f"Posiciones: {', '.join([f'{c:.1f}' for c in cortes['z'][:15]])}{'...' if len(cortes['z'])>15 else ''}")
            with col_t2:
                st.markdown(f"**Cortes horizontales (Y):** {len(cortes['y'])}")
                st.write(f"Posiciones: {', '.join([f'{c:.1f}' for c in cortes['y'][:15]])}{'...' if len(cortes['y'])>15 else ''}")
            with col_t3:
                st.markdown(f"**Cortes verticales (X):** {len(cortes['x'])}")
                st.write(f"Posiciones: {', '.join([f'{c:.1f}' for c in cortes['x'][:15]])}{'...' if len(cortes['x'])>15 else ''}")
            
            st.markdown("**Piezas por tipo:** " + " | ".join([f"{k}: {v}" for k, v in resumen.items()]))
            
            # BOTONES DE PDF
            if FPDF_DISPONIBLE:
                st.divider()
                st.subheader("📄 Generar Reportes PDF")
                
                col_pdf1, col_pdf2 = st.columns(2)
                with col_pdf1:
                    st.markdown("### 🎯 PDF de ESTE bloque")
                    st.caption("2 páginas: 3 vistas + tabla de cortes. Para el operario.")
                    if st.button("🚀 Generar PDF (1 bloque)", use_container_width=True, key="btn_pdf_bloque"):
                        with st.spinner("Generando PDF..."):
                            pdf_bytes = _generar_pdf_bloque_unico(bloque, ancho_mix, densidad_mix, vol_bloque_sel)
                        st.download_button("📥 Descargar PDF", data=pdf_bytes,
                                           file_name=f"bloque_{bloque['numero']}_planos.pdf",
                                           mime="application/pdf", use_container_width=True, key="dl_bloque")
                
                with col_pdf2:
                    st.markdown("### 📊 PDF CONSOLIDADO")
                    st.caption("3 páginas: resumen global + tabla de todos los bloques + resumen por tipo. Para supervisor.")
                    if st.button("🚀 Generar PDF (todos)", use_container_width=True, key="btn_pdf_consolidado"):
                        with st.spinner("Generando PDF consolidado..."):
                            pdf_bytes = _generar_pdf_consolidado(bloques, ancho_mix, densidad_mix, total_pedidas, total_colocadas, vol_total_colocado)
                        st.download_button("📥 Descargar PDF", data=pdf_bytes,
                                           file_name=f"consolidado_{len(bloques)}bloques.pdf",
                                           mime="application/pdf", use_container_width=True, key="dl_consolidado")

st.markdown("---")
st.caption("💡 *Covintec v28.0 | Planos de corte industriales: 3 vistas + tabla de cortes. PDF de 154 páginas → 2 páginas.*")