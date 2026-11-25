#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CALCULADOR EPS WEB v24.0 - GESTIÓN DE FILAS + REPORTE PDF
- Botones: Agregar fila, Limpiar tabla, Eliminar fila específica
- Reporte PDF con portada, bloques, segmentos y resumen final
- Usa fpdf2 (pip install fpdf2)
"""
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math
import io
from collections import defaultdict
from fpdf import FPDF

KERF_CM = 0.2
ALTO_BLOQUE = 66.0
LARGO_BLOQUE = 506.0

st.set_page_config(page_title="📦 Calculador EPS Covintec", layout="wide")

# ==========================================
# 🧠 MOTOR SINGLE (INTACTO)
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
# 🔄 MOTOR MIX v24.0
# ==========================================
def _ffdh_nesting(ancho, alto, piezas):
    if not piezas: return []
    expandidas = []
    for p in piezas:
        for _ in range(p['qty']):
            expandidas.append({'w': p['w'], 'h': p['h'], 'id': p['id'], 'color': p['color'], 'm3': p['m3']})
    expandidas.sort(key=lambda x: max(x['w'], x['h']), reverse=True)
    shelves, layout = [], []
    for pieza in expandidas:
        colocada = False
        orientaciones = sorted([(pieza['w'], pieza['h']), (pieza['h'], pieza['w'])], key=lambda o: o[1])
        for w, h in orientaciones:
            if w > ancho + 0.01 or h > alto + 0.01: continue
            for shelf in shelves:
                if shelf['altura'] >= h - 0.01 and shelf['x_actual'] + w <= ancho + 0.01:
                    layout.append({'x': shelf['x_actual'], 'y': shelf['y'], 'w': w, 'h': h,
                                   'id': pieza['id'], 'color': pieza['color'], 'm3': pieza['m3']})
                    shelf['x_actual'] += w + KERF_CM
                    colocada = True
                    break
            if colocada: break
        if not colocada:
            nuevo_y = sum(s['altura'] + KERF_CM for s in shelves)
            for w, h in orientaciones:
                if w <= ancho + 0.01 and nuevo_y + h <= alto + 0.01:
                    shelves.append({'y': nuevo_y, 'altura': h, 'x_actual': w + KERF_CM})
                    layout.append({'x': 0, 'y': nuevo_y, 'w': w, 'h': h,
                                   'id': pieza['id'], 'color': pieza['color'], 'm3': pieza['m3']})
                    colocada = True
                    break
    return layout

def _distribuir_en_bloques(grupos, ancho):
    sub_segmentos = []
    for m3, piezas in grupos.items():
        layout = _ffdh_nesting(ancho, ALTO_BLOQUE, piezas)
        if not layout: continue
        ppc = len(layout)
        qty_total = sum(p['qty'] for p in piezas)
        if ppc == 0: continue
        capas_max_segmento = int(LARGO_BLOQUE // (m3 + KERF_CM))
        if capas_max_segmento == 0: continue
        piezas_restantes = qty_total
        while piezas_restantes > 0:
            capas_necesarias = math.ceil(piezas_restantes / ppc)
            capas_este = min(capas_max_segmento, capas_necesarias)
            piezas_este = min(ppc * capas_este, piezas_restantes)
            sub_segmentos.append({
                'm3': m3, 'layout': layout, 'piezas_por_capa': ppc,
                'capas': capas_este, 'piezas_en_segmento': piezas_este,
                'long': capas_este * (m3 + KERF_CM), 'color': piezas[0]['color']
            })
            piezas_restantes -= piezas_este
    sub_segmentos.sort(key=lambda x: x['long'], reverse=True)
    bloques = []
    for seg in sub_segmentos:
        colocado = False
        for bloque in bloques:
            if bloque['usado'] + seg['long'] <= LARGO_BLOQUE + 0.01:
                bloque['segmentos'].append(seg)
                bloque['usado'] += seg['long']
                colocado = True
                break
        if not colocado:
            bloques.append({'segmentos': [seg], 'usado': seg['long']})
    return bloques

def _calcular_kerf_bloque(segmentos, ancho):
    vol = 0.0
    for s in segmentos:
        m3, capas, lay = s['m3'], s['capas'], s['layout']
        if capas > 1:
            vol += (capas - 1) * ancho * ALTO_BLOQUE * KERF_CM
        ys = sorted(set(p['y'] for p in lay))
        if len(ys) > 1:
            vol += (len(ys) - 1) * ancho * m3 * KERF_CM
        for y in ys:
            fila = [p for p in lay if p['y'] == y]
            if len(fila) > 1:
                vol += (len(fila) - 1) * fila[0]['h'] * m3 * KERF_CM
    return vol / 1e6

def _volumen_piezas_segmento(s):
    vol_capa = sum(p['w'] * p['h'] * s['m3'] for p in s['layout']) / 1e6
    ppc = s['piezas_por_capa']
    piezas = s['piezas_en_segmento']
    capas_completas = piezas // ppc
    piezas_parciales = piezas % ppc
    vol = vol_capa * capas_completas
    if piezas_parciales > 0:
        vol += sum(p['w'] * p['h'] * s['m3'] for p in s['layout'][:piezas_parciales]) / 1e6
    return vol

def _graficar_longitudinal_bloque(bloque, ancho, num_bloque, total_bloques):
    fig, ax = plt.subplots(figsize=(15, 3.5))
    ax.set_xlim(0, LARGO_BLOQUE); ax.set_ylim(-1, 11); ax.axis('off')
    ax.add_patch(patches.Rectangle((0, 0), LARGO_BLOQUE, 10, facecolor='#F0F2F6', edgecolor='#333', lw=2))
    x = 0
    for s in bloque['segmentos']:
        m3, capas, lay = s['m3'], s['capas'], s['layout']
        modelos = sorted(set(p['id'] for p in lay))
        largo_seg = capas * (m3 + KERF_CM)
        ax.add_patch(patches.Rectangle((x, 0), largo_seg, 10, facecolor=s['color'], alpha=0.85, edgecolor='white', lw=2))
        ax.text(x + largo_seg/2, 5, f"{', '.join(modelos)}\n{m3:.1f}cm x{capas}", ha='center', va='center',
                fontsize=9 if largo_seg > 60 else 7, fontweight='bold', color='white')
        for c in range(1, capas):
            ax.plot([x + c*(m3+KERF_CM), x + c*(m3+KERF_CM)], [0, 10], color='white', ls='--', alpha=0.7)
        x += largo_seg
    if x < LARGO_BLOQUE - 0.5:
        res = LARGO_BLOQUE - x
        ax.add_patch(patches.Rectangle((x, 0), res, 10, facecolor='#FADBD8', edgecolor='#C0392B', hatch='||', alpha=0.7, lw=2))
        ax.text(x + res/2, 5, f"RESIDUO\n{res:.1f} cm", ha='center', va='center', fontsize=10, color='#C0392B', fontweight='bold')
    ax.set_xticks([0, 100, 200, 300, 400, 506]); ax.tick_params(axis='x', colors='gray', labelsize=8)
    ax.set_title(f"BLOQUE {num_bloque}/{total_bloques} - Ancho {ancho} cm | Usados {x:.1f} cm de 506 cm",
                 fontsize=12, fontweight='bold', pad=8)
    plt.tight_layout(); return fig

def _graficar_transversal_segmento(s, ancho):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.set_xlim(0, ancho); ax.set_ylim(0, ALTO_BLOQUE); ax.set_aspect('equal'); ax.grid(ls=':', alpha=0.4)
    modelos = sorted(set(p['id'] for p in s['layout']))
    ax.set_title(f"Seccion 66x{ancho} cm | Largo {s['m3']:.1f} cm | {s['capas']} capas | Patron: {len(s['layout'])} pz/capa | Total: {s['piezas_en_segmento']} pz",
                 fontsize=11, fontweight='bold')
    for p in s['layout']:
        ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], fc=p['color'], ec='white', lw=1.5, alpha=0.92))
        if p['w'] > 8 and p['h'] > 3:
            ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['id'], ha='center', va='center', c='white', fontweight='bold', fontsize=8)
    max_y = max((p['y']+p['h'] for p in s['layout']), default=0)
    if max_y < ALTO_BLOQUE - 0.5:
        ax.add_patch(patches.Rectangle((0, max_y), ancho, ALTO_BLOQUE-max_y, fc='#EAECEE', ec='#999', hatch='//', alpha=0.5))
        ax.text(ancho/2, max_y + (ALTO_BLOQUE-max_y)/2, f"Espacio vacio: {ALTO_BLOQUE-max_y:.1f} cm de alto",
                ha='center', va='center', fontsize=9, color='#555', style='italic')
    ax.set_xlabel("Ancho (cm)"); ax.set_ylabel("Alto (cm)")
    plt.tight_layout(); return fig

# ==========================================
# 📄 GENERADOR DE PDF
# ==========================================
def _fig_to_png(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    return buf

def _generar_reporte_pdf(bloques, ancho_mix, densidad_mix, factor_perfilado, modo_bovedilla, total_pedidas, total_colocadas):
    """Genera PDF completo con todos los bloques y resumen."""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ---- PORTADA ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 22)
    pdf.cell(0, 20, 'Reporte de Optimizacion EPS', ln=True, align='C')
    pdf.set_font('Helvetica', '', 14)
    pdf.cell(0, 10, f'Ancho de bloque: {ancho_mix} cm | Largo: {LARGO_BLOQUE} cm | Alto: {ALTO_BLOQUE} cm', ln=True, align='C')
    pdf.cell(0, 10, f'Kerf: {KERF_CM*10:.0f} mm', ln=True, align='C')
    pdf.ln(10)
    
    # Resumen general
    vol_total = sum(_volumen_piezas_segmento(s) for b in bloques for s in b['segmentos'])
    vol_bloques = len(bloques) * (ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE / 1e6)
    ef = (vol_total / vol_bloques * 100) if vol_bloques > 0 else 0
    peso = vol_total * densidad_mix
    
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'RESUMEN GENERAL', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Total de bloques necesarios: {len(bloques)}', ln=True)
    pdf.cell(0, 7, f'Piezas solicitadas: {total_pedidas}', ln=True)
    pdf.cell(0, 7, f'Piezas colocadas: {total_colocadas}', ln=True)
    pdf.cell(0, 7, f'Eficiencia global: {ef:.2f}%', ln=True)
    pdf.cell(0, 7, f'Volumen util: {vol_total:.4f} m3', ln=True)
    pdf.cell(0, 7, f'Peso neto: {peso:.2f} kg', ln=True)
    pdf.ln(10)
    
    # ---- UN BLOQUE POR SECCION ----
    for num_b, bloque in enumerate(bloques, 1):
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, f'BLOQUE {num_b}/{len(bloques)}', ln=True)
        pdf.set_font('Helvetica', '', 11)
        
        # Longitudinal
        fig_long = _graficar_longitudinal_bloque(bloque, ancho_mix, num_b, len(bloques))
        buf = _fig_to_png(fig_long)
        pdf.image(buf, x=10, w=190)
        plt.close(fig_long)
        pdf.ln(5)
        
        # Tabla de segmentos
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'Segmentos del bloque:', ln=True)
        pdf.set_font('Helvetica', '', 9)
        
        # Headers
        col_w = [10, 25, 40, 25, 20, 25, 30]
        headers = ['#', 'Largo', 'Modelos', 'Pz/capa', 'Capas', 'Total Pz', 'Longitud']
        for i, h in enumerate(headers):
            pdf.cell(col_w[i], 7, h, border=1, align='C')
        pdf.ln()
        
        for i, s in enumerate(bloque['segmentos']):
            modelos = ', '.join(sorted(set(p['id'] for p in s['layout'])))
            row = [str(i+1), f"{s['m3']:.1f}", modelos[:25], str(s['piezas_por_capa']), 
                   str(s['capas']), str(s['piezas_en_segmento']), f"{s['long']:.1f}"]
            for j, val in enumerate(row):
                pdf.cell(col_w[j], 6, val, border=1, align='C')
            pdf.ln()
        
        # Desglose
        pdf.ln(5)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, 'Desglose del bloque:', ln=True)
        pdf.set_font('Helvetica', '', 10)
        
        vk = _calcular_kerf_bloque(bloque['segmentos'], ancho_mix)
        vseg = sum(_volumen_piezas_segmento(s) for s in bloque['segmentos'])
        vb = ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
        vpr = vseg * (factor_perfilado/100) if modo_bovedilla else 0.0
        vn = vseg - vpr
        vr = max(0, vb - vseg - vk)
        pn, pp, pk, pr = [(v/vb)*100 for v in [vn, vpr, vk, vr]]
        
        pdf.cell(0, 6, f'Producto Neto: {pn:.2f}% ({vn:.4f} m3)', ln=True)
        if modo_bovedilla:
            pdf.cell(0, 6, f'Perfilado Bovedilla: {pp:.2f}% ({vpr:.4f} m3)', ln=True)
        pdf.cell(0, 6, f'Kerf (Hilo): {pk:.2f}% ({vk:.4f} m3)', ln=True)
        pdf.cell(0, 6, f'Restante Fisico: {pr:.2f}% ({vr:.4f} m3)', ln=True)
        
        # Transversal de cada segmento
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, f'Vistas Transversales - Bloque {num_b}', ln=True)
        pdf.set_font('Helvetica', '', 10)
        
        for i, s in enumerate(bloque['segmentos']):
            modelos = ', '.join(sorted(set(p['id'] for p in s['layout'])))
            pdf.cell(0, 8, f'Segmento {i+1}: {modelos} | Largo {s["m3"]:.1f} cm | {s["piezas_en_segmento"]} pz', ln=True)
            fig_t = _graficar_transversal_segmento(s, ancho_mix)
            buf = _fig_to_png(fig_t, dpi=120)
            pdf.image(buf, x=10, w=190)
            plt.close(fig_t)
            pdf.ln(3)
    
    # ---- RESUMEN FINAL ----
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 15, 'RESUMEN FINAL', ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'Totales consolidados:', ln=True)
    pdf.set_font('Helvetica', '', 11)
    pdf.cell(0, 7, f'Numero de bloques: {len(bloques)}', ln=True)
    pdf.cell(0, 7, f'Eficiencia global: {ef:.2f}%', ln=True)
    pdf.cell(0, 7, f'Volumen total util: {vol_total:.4f} m3', ln=True)
    pdf.cell(0, 7, f'Peso total neto: {peso:.2f} kg', ln=True)
    pdf.cell(0, 7, f'Piezas producidas: {total_colocadas} de {total_pedidas} solicitadas', ln=True)
    
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'Detalle por bloque:', ln=True)
    pdf.set_font('Helvetica', '', 10)
    
    col_w2 = [20, 30, 30, 30, 30, 30]
    headers2 = ['Bloque', 'Segmentos', 'Piezas', 'Volumen (m3)', 'Usado (cm)', 'Eficiencia']
    for i, h in enumerate(headers2):
        pdf.cell(col_w2[i], 7, h, border=1, align='C')
    pdf.ln()
    
    for num_b, bloque in enumerate(bloques, 1):
        vk_b = _calcular_kerf_bloque(bloque['segmentos'], ancho_mix)
        vseg_b = sum(_volumen_piezas_segmento(s) for s in bloque['segmentos'])
        vb_b = ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
        ef_b = (vseg_b / vb_b * 100) if vb_b > 0 else 0
        piezas_b = sum(s['piezas_en_segmento'] for s in bloque['segmentos'])
        usado_b = sum(s['long'] for s in bloque['segmentos'])
        
        row = [str(num_b), str(len(bloque['segmentos'])), str(piezas_b),
               f'{vseg_b:.4f}', f'{usado_b:.1f}', f'{ef_b:.1f}%']
        for j, val in enumerate(row):
            pdf.cell(col_w2[j], 6, val, border=1, align='C')
        pdf.ln()
    
    return pdf

# ==========================================
# 🖥️ INTERFAZ
# ==========================================
st.title("📦 Calculador EPS Covintec")
st.caption(f"⚙️ Kerf: {KERF_CM*10:.0f}mm | Mix v24.0 + PDF")

tab1, tab2 = st.tabs(["🔹 Single (Pieza Única)", "🔹 Mix (Nesting FFDH)"])

with tab1:
    st.header("Cálculo de Pieza Única")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Parámetros")
        modo_optimo = st.checkbox("🔍 Calcular Ancho Óptimo (126-156)", value=False)
        if modo_optimo:
            ancho_slider = 130
        else:
            ancho_slider = st.slider("Ancho Bloque (cm)", 126, 156, 126, step=1, key="slider_single")
        st.markdown("### 📐 Dimensiones (cm)")
        d1 = st.number_input("Medida 1", value=5.0, key="s_d1")
        d2 = st.number_input("Medida 2", value=61.0, key="s_d2")
        d3 = st.number_input("Medida 3", value=122.0, key="s_d3")
        st.markdown("### ⚖️ Densidad y Geometría")
        densidad = st.selectbox("Densidad EPS (kg/m³)", list(range(7, 20)), index=3, key="densidad_single")
        modo_bovedilla = st.checkbox("🔸 Activar modo Bovedilla (Perfilado CNC)", value=False, key="bov_single")
        factor_perfilado = 20.0
        if modo_bovedilla: factor_perfilado = st.slider("Pérdida por perfilado (%)", 5.0, 35.0, 20.0, 1.0, key="fp_single")
        modo_uniforme = st.checkbox("✅ Priorizar Acomodo Operativo (Largo Estándar)", value=True, key="uni_single")
        calc = st.button("🚀 Calcular", type="primary", use_container_width=True, key="btn_single")

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
                vg, vk, vb = r['vol_gross_m3'], r['vol_kerf_m3'], r['vol_bloque_m3']
                vpr = vg * (factor_perfilado/100) if modo_bovedilla else 0.0
                vn = vg - vpr
                vr = max(0, vb - vg - vk)
                pn, pp, pk, pr = [(v/vb)*100 for v in [vn, vpr, vk, vr]]
                wn, wp, wk, wr = [(v*densidad) for v in [vn, vpr, vk, vr]]
                wt = vb * densidad
                st.info(f"📋 **Estrategia:** {'Operativo' if modo_uniforme else 'Matemático'} | **Largo:** `{r['lp']:.0f} cm`")
                c1,c2,c3 = st.columns(3)
                c1.metric("📦 Total Piezas", r['total']); c2.metric("📈 Eficiencia Bruta", f"{(vg/vb)*100:.2f}%"); c3.metric("🧱 Peso Neto", f"{wn:.2f} kg")
                st.divider(); st.subheader("📉 Desglose del Bloque (100%)")
                st.info(f"⚖️ **Peso Total:** `{wt:.2f} kg` | 📦 **Volumen Total:** `{vb:.4f} m³`")
                st.markdown(f"🔵 **Producto Final (Neto):** `{pn:.2f}%` → `{vn:.4f} m³` → `{wn:.2f} kg`"); st.progress(min(1.0, pn/100))
                if modo_bovedilla: st.markdown(f"🔸 **Perfilado Bovedilla:** `{pp:.2f}%` → `{vpr:.4f} m³` → `{wp:.2f} kg`"); st.progress(min(1.0, pp/100))
                st.markdown(f"🔴 **Kerf (Hilo):** `{pk:.2f}%` → `{vk:.4f} m³` → `{wk:.2f} kg`"); st.progress(min(1.0, pk/100))
                st.markdown(f"⬜ **Restante Físico:** `{pr:.2f}%` → `{vr:.4f} m³` → `{wr:.2f} kg`"); st.progress(min(1.0, pr/100))
                st.success(f"✅ **Verificación:** {vn:.4f}+{vpr:.4f}+{vk:.4f}+{vr:.4f} ≈ `{vb:.4f} m³`")
                st.pyplot(_graficar_single(r))

with tab2:
    st.header("🔀 Optimización de Mezcla (Nesting FFDH)")
    st.markdown("🔹 Mezcla modelos con el mismo largo. 🔹 Divide grupos largos. 🔹 Conteo exacto. 🔹 Reporte PDF.")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⚙️ Configuración")
        ancho_mix = st.slider("Ancho Bloque (cm)", 126, 156, 140, step=1, key="slider_mix")
        densidad_mix = st.selectbox("Densidad EPS (kg/m³)", list(range(7, 20)), index=3, key="densidad_mix")
        modo_bovedilla_mix = st.checkbox("🔸 Activar modo Bovedilla (Perfilado CNC)", value=False, key="bov_mix")
        factor_perfilado_mix = 20.0
        if modo_bovedilla_mix: factor_perfilado_mix = st.slider("Pérdida por perfilado (%)", 5.0, 35.0, 20.0, 1.0, key="fp_mix")

        st.markdown("### 📋 Lista de Pedidos")
        st.caption("💡 M1/M2 = cara | M3 = largo (cm). Usa punto decimal: 2.5, 44.5")
        
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
            hide_index=True, num_rows="dynamic", use_container_width=True, key="editor_mix_v24"
        )
        if edited_df != st.session_state['prod_mix']:
            st.session_state['prod_mix'] = edited_df
        
        # ✅ NUEVO: Botones de gestión de filas
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("➕ Agregar fila", use_container_width=True, key="btn_add_row"):
                nueva_fila = {'id': f'N{len(st.session_state["prod_mix"])+1}', 'm1': 0.0, 'm2': 0.0, 'm3': 0.0, 'qty': 1, 'color': '#808080'}
                st.session_state['prod_mix'].append(nueva_fila)
                st.rerun()
        with col_btn2:
            if st.button("🗑️ Limpiar tabla", use_container_width=True, key="btn_clear_table"):
                st.session_state['prod_mix'] = []
                st.rerun()
        with col_btn3:
            if st.button("🔄 Cargar ejemplo", use_container_width=True, key="btn_load_example"):
                st.session_state['prod_mix'] = default_prod
                st.rerun()
        
        calc_mix = st.button("🚀 Optimizar Mezcla", type="primary", use_container_width=True, key="btn_mix")
        if calc_mix:
            st.session_state['mix_calculado'] = True

    with col2:
        if st.session_state.get('mix_calculado', False):
            st.subheader("📊 Resultados Mix")
            grupos = defaultdict(list)
            for row in st.session_state['prod_mix']:
                try:
                    m1, m2, m3 = float(row['m1']), float(row['m2']), float(row['m3'])
                    qty = int(row['qty'])
                except: continue
                if qty <= 0: continue
                if m3 > LARGO_BLOQUE:
                    st.error(f"❌ {row['id']} largo {m3} > 506 cm"); continue
                grupos[m3].append({'id': row['id'], 'w': m1, 'h': m2, 'm3': m3, 'color': row['color'], 'qty': qty})

            bloques = _distribuir_en_bloques(grupos, ancho_mix)
            if not bloques:
                st.warning("⚠️ No hay piezas válidas para optimizar."); st.stop()

            total_piezas_pedidas = sum(p['qty'] for g in grupos.values() for p in g)
            total_piezas_colocadas = sum(s['piezas_en_segmento'] for b in bloques for s in b['segmentos'])
            st.success(f"✅ **{len(bloques)} bloque(s)** | {total_piezas_colocadas}/{total_piezas_pedidas} piezas colocadas")

            vol_total_piezas = sum(_volumen_piezas_segmento(s) for b in bloques for s in b['segmentos'])
            vol_total_bloques = len(bloques) * (ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE / 1e6)
            ef_global = (vol_total_piezas / vol_total_bloques) * 100 if vol_total_bloques > 0 else 0
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📦 Piezas", f"{total_piezas_colocadas}/{total_piezas_pedidas}")
            c2.metric("🧱 Bloques", len(bloques))
            c3.metric("📈 Eficiencia Global", f"{ef_global:.2f}%")
            c4.metric("🧱 Peso Neto", f"{vol_total_piezas * densidad_mix:.2f} kg")

            if ef_global < 40:
                st.warning(f"⚠️ **Eficiencia baja ({ef_global:.1f}%)**: cantidades pequeñas para llenar bloques de 506 cm. "
                           f"Agrupa pedidos de varios días o aumenta cantidades por modelo.")

            # ✅ NUEVO: Botón de descarga PDF
            pdf = _generar_reporte_pdf(bloques, ancho_mix, densidad_mix, factor_perfilado_mix, 
                                       modo_bovedilla_mix, total_piezas_pedidas, total_piezas_colocadas)
            pdf_bytes = pdf.output()
            st.download_button(
                label="📄 Descargar Reporte PDF",
                data=pdf_bytes,
                file_name=f"reporte_eps_{len(bloques)}bloques.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key="btn_pdf"
            )

            if len(bloques) > 1:
                num_b = st.radio("Ver bloque:", list(range(1, len(bloques)+1)), horizontal=True, key="sel_bloque")
            else:
                num_b = 1
            bloque = bloques[num_b-1]

            st.subheader(f"📏 Bloque {num_b} — Vista Longitudinal (506 cm)")
            st.pyplot(_graficar_longitudinal_bloque(bloque, ancho_mix, num_b, len(bloques)))

            vk = _calcular_kerf_bloque(bloque['segmentos'], ancho_mix)
            vseg = sum(_volumen_piezas_segmento(s) for s in bloque['segmentos'])
            vb = ancho_mix * ALTO_BLOQUE * LARGO_BLOQUE / 1e6
            vpr = vseg * (factor_perfilado_mix/100) if modo_bovedilla_mix else 0.0
            vn = vseg - vpr
            vr = max(0, vb - vseg - vk)
            pn, pp, pk, pr = [(v/vb)*100 for v in [vn, vpr, vk, vr]]

            st.markdown("#### Desglose del Bloque (100%)")
            st.markdown(f"🔵 **Producto Final (Neto):** `{pn:.2f}%` → `{vn:.4f} m³` → `{vn*densidad_mix:.2f} kg`"); st.progress(min(1.0, pn/100))
            if modo_bovedilla_mix:
                st.markdown(f"🔸 **Perfilado Bovedilla:** `{pp:.2f}%` → `{vpr:.4f} m³` → `{vpr*densidad_mix:.2f} kg`"); st.progress(min(1.0, pp/100))
            st.markdown(f"🔴 **Kerf (Hilo):** `{pk:.2f}%` → `{vk:.4f} m³` → `{vk*densidad_mix:.2f} kg`"); st.progress(min(1.0, pk/100))
            st.markdown(f"⬜ **Restante Físico:** `{pr:.2f}%` → `{vr:.4f} m³` → `{vr*densidad_mix:.2f} kg`"); st.progress(min(1.0, pr/100))
            st.success(f"✅ **Verificación:** {vn:.4f}+{vpr:.4f}+{vk:.4f}+{vr:.4f} ≈ `{vb:.4f} m³`")

            st.markdown("#### 📋 Segmentos de este bloque")
            datos = []
            for i, s in enumerate(bloque['segmentos']):
                modelos = ', '.join(sorted(set(p['id'] for p in s['layout'])))
                datos.append({
                    '#': i+1, 'Largo (cm)': f"{s['m3']:.1f}", 'Modelos': modelos,
                    'Pz/capa': s['piezas_por_capa'], 'Capas': s['capas'],
                    'Total Pz': s['piezas_en_segmento'], 'Longitud (cm)': f"{s['long']:.1f}"
                })
            st.table(datos)

            st.subheader("🔍 Vista Transversal por Segmento")
            if bloque['segmentos']:
                nombres = [f"Segmento {i+1}: {', '.join(sorted(set(p['id'] for p in s['layout'])))} | largo {s['m3']:.1f} cm | {s['piezas_en_segmento']} pz"
                           for i, s in enumerate(bloque['segmentos'])]
                idx = st.selectbox("Elige segmento:", range(len(bloque['segmentos'])),
                                   format_func=lambda i: nombres[i], key=f"sel_seg_b{num_b}")
                seg = bloque['segmentos'][idx]
                st.pyplot(_graficar_transversal_segmento(seg, ancho_mix))
            else:
                st.info("Este bloque no tiene segmentos.")

st.markdown("---")
st.caption("💡 *Covintec v24.0 | Gestión de filas + Reporte PDF completo.*")