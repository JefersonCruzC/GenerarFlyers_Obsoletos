import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os
import gspread
import json
import textwrap
import time
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN DE LIENZO ---
ANCHO, ALTO = 2500, 3750
SHEET_ID = "10_VQTvW_Dkpg1rQ-nq2vkATwTwxmoFhqfUIKqxv6Aow"
USUARIO_GITHUB = "JefersonCruzC" 
REPO_NOMBRE = "GenerarFlyers_Obsoletos"
URL_BASE_PAGES = f"https://{USUARIO_GITHUB}.github.io/{REPO_NOMBRE}/flyers/"

# --- RUTAS DE FUENTES ---
FONT_BOLD_COND = "Mark Simonson - Proxima Nova Alt Condensed Bold.otf"
FONT_EXTRABOLD_COND = "Mark Simonson - Proxima Nova Alt Condensed Extrabold.otf"
FONT_REGULAR_COND = "Mark Simonson - Proxima Nova Alt Condensed Regular.otf"
FONT_EXTRABOLD = "Mark Simonson - Proxima Nova Extrabold.otf"
FONT_SEMIBOLD = "Mark Simonson - Proxima Nova Semibold.otf"
FONT_RUBIK = "Rubik-Medium.ttf"

# --- COLORES ---
LC_AMARILLO = (255, 203, 5)
LC_AMARILLO_OSCURO = (235, 180, 0)
EFE_AZUL = (0, 107, 213) 
EFE_AZUL_OSCURO = (0, 60, 150)
EFE_NARANJA = (255, 100, 0)
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
GRIS_MARCA = (100, 100, 100)

output_dir = "docs/flyers"
os.makedirs(output_dir, exist_ok=True)

fecha_peru = (datetime.utcnow() - timedelta(hours=5)).strftime("%d/%m/%Y %I:%M %p")

def conectar_sheets():
    info_creds = json.loads(os.environ['GOOGLE_SHEETS_JSON'])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info_creds, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

def descargar_imagen(url):
    if not url or str(url).lower() == 'nan' or str(url).strip() == "": return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        return Image.open(BytesIO(res.content)).convert("RGBA")
    except: return None

def formatear_precio(valor):
    s = str(valor).replace("S/.", "").replace("S/", "").strip()
    if not s or s == "0": return "0,00"
    if "," not in s and "." not in s and len(s) > 2:
        s = s[:-2] + "," + s[-2:]
    else:
        s = s.replace(".", ",")
        if "," not in s: s += ",00"
    return s

def crear_flyer(productos, tienda_nombre, flyer_count):
    es_efe = "EFE" in tienda_nombre.upper()
    color_fondo = EFE_AZUL_OSCURO if es_efe else LC_AMARILLO_OSCURO
    color_slogan_bg = EFE_AZUL if es_efe else LC_AMARILLO
    logo_path = "logo-efe-sin-fondo.png" if es_efe else "logo-lc-sin-fondo.png"
    tienda_bg_path = "efe tienda.jpg" if es_efe else "LC-MIRAFLORES-LOGO-3D[2].jpg"
    
    flyer = Image.new('RGB', (ANCHO, ALTO), color=color_fondo)
    draw = ImageDraw.Draw(flyer)
    
    # 1. IMAGEN DE TIENDA
    header_h = 1000
    try:
        bg = Image.open(tienda_bg_path).convert("RGBA")
        bg = ImageOps.fit(bg, (ANCHO, header_h), method=Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', (ANCHO, header_h), (0, 0, 0, 50))
        bg.paste(overlay, (0, 0), overlay)
        flyer.paste(bg, (0, 0))
    except: pass

    # 2. LOGO (INCREMENTADO Y CENTRADO)
    try:
        logo = Image.open(logo_path).convert("RGBA")
        if es_efe:
            draw.ellipse([ANCHO-650, 50, ANCHO-50, 650], fill=BLANCO)
            logo.thumbnail((480, 480))
            flyer.paste(logo, (ANCHO-650 + (600-logo.width)//2, 50 + (600-logo.height)//2), logo)
        else:
            draw.rounded_rectangle([ANCHO-650, 0, ANCHO-50, 480], radius=60, fill=BLANCO)
            draw.rectangle([ANCHO-650, 0, ANCHO-50, 60], fill=BLANCO)
            logo.thumbnail((500, 500))
            flyer.paste(logo, (ANCHO-650 + (600-logo.width)//2, 40), logo)
    except: pass

    # 3. NOMBRE TIENDA
    f_tienda = ImageFont.truetype(FONT_EXTRABOLD_COND, 90)
    txt_tienda = tienda_nombre.upper()
    tw_t = draw.textlength(txt_tienda, font=f_tienda)
    if es_efe:
        draw.rounded_rectangle([ANCHO - tw_t - 150, 680, ANCHO, 860], radius=50, fill=EFE_NARANJA)
        draw.text((ANCHO - tw_t - 80, 715), txt_tienda, font=f_tienda, fill=BLANCO)
    else:
        points = [(ANCHO - tw_t - 250, 750), (ANCHO - tw_t - 150, 550), (ANCHO, 550), (ANCHO, 750)]
        draw.polygon(points, fill=NEGRO)
        draw.text((ANCHO - tw_t - 100, 600), txt_tienda, font=f_tienda, fill=LC_AMARILLO)

    # 4. FECHA GENERADO (BOLD Y MÁS ANCHO)
    f_fecha = ImageFont.truetype(FONT_BOLD_COND, 45)
    txt_gen = f"Generado: {fecha_peru}"
    tw_g = draw.textlength(txt_gen, font=f_fecha)
    draw.rounded_rectangle([0, 850, tw_g + 120, 960], radius=40, fill=BLANCO)
    draw.text((60, 880), txt_gen, font=f_fecha, fill=NEGRO)

    # 5. SLOGAN
    f_slogan = ImageFont.truetype(FONT_EXTRABOLD, 105)
    slogan_txt = "¡APROVECHA ESTAS INCREÍBLES OFERTAS!"
    sw = draw.textlength(slogan_txt, font=f_slogan)
    draw.rectangle([0, 1030, ANCHO, 1260], fill=color_slogan_bg)
    draw.text(((ANCHO-sw)//2, 1085), slogan_txt, font=f_slogan, fill=BLANCO if es_efe else NEGRO)

    # 6. PRODUCTOS (SUBIDOS PARA EVITAR EL PIE)
    anchos = [100, 1310]
    altos = [1300, 2050, 2800] # Se restaron 50-90px a cada fila
    
    f_marca_prod = ImageFont.truetype(FONT_SEMIBOLD, 50)
    f_art_prod = ImageFont.truetype(FONT_REGULAR_COND, 65)
    f_precio_num = ImageFont.truetype(FONT_EXTRABOLD, 120)
    f_simbolo_s = ImageFont.truetype(FONT_REGULAR_COND, 65)
    f_sku_prod = ImageFont.truetype(FONT_BOLD_COND, 55)

    for i, prod in enumerate(productos):
        if i >= 6: break
        x, y = anchos[i%2], altos[i//2]
        draw.rounded_rectangle([x, y, x+1090, y+710], radius=70, fill=BLANCO)
        
        img_p = descargar_imagen(prod['image_link'])
        if img_p:
            img_p.thumbnail((480, 480))
            flyer.paste(img_p, (x+30, y + (710-img_p.height)//2), img_p)
            
        tx = x + 540
        area_texto_w = 520
        
        # Marca
        marca = str(prod['Nombre Marca']).upper()
        draw.text((tx + (area_texto_w - draw.textlength(marca, f_marca_prod))//2, y+50), marca, font=f_marca_prod, fill=GRIS_MARCA)
        
        # Título Centrado
        titulo = str(prod['Nombre Articulo'])
        lines = textwrap.wrap(titulo, width=22)
        ty = y + 130
        for line in lines[:3]:
            tw_line = draw.textlength(line, font=f_art_prod)
            draw.text((tx + (area_texto_w - tw_line)//2, ty), line, font=f_art_prod, fill=NEGRO)
            ty += 70
            
        # BLOQUES DE PRECIO
        ty_b = y + 410
        p_val = formatear_precio(prod['S/.ACTUAL'])
        rec_color_p = EFE_AZUL if es_efe else LC_AMARILLO
        rec_color_s = EFE_NARANJA if es_efe else NEGRO
        
        draw.rounded_rectangle([tx + 20, ty_b, tx+area_texto_w - 20, ty_b + 140], radius=35, fill=rec_color_p)
        draw.rectangle([tx + 20, ty_b+70, tx+area_texto_w - 20, ty_b+140], fill=rec_color_p)
        
        p_full = f"S/ {p_val}"
        tw_p = draw.textlength(p_full, font=f_precio_num)
        start_p = tx + (area_texto_w - tw_p)//2
        
        # Símbolo S/ ajustado
        draw.text((start_p, ty_b + 42), "S/", font=f_simbolo_s, fill=BLANCO if es_efe else NEGRO)
        draw.text((start_p + 85, ty_b + 12), p_val, font=f_precio_num, fill=BLANCO if es_efe else NEGRO)
        
        sku_val = str(prod['%Cod Articulo'])
        draw.rounded_rectangle([tx + 20, ty_b + 140, tx+area_texto_w - 20, ty_b + 220], radius=35, fill=rec_color_s)
        draw.rectangle([tx + 20, ty_b + 140, tx+area_texto_w - 20, ty_b + 175], fill=rec_color_s)
        
        tw_s = draw.textlength(sku_val, font=f_sku_prod)
        draw.text((tx + (area_texto_w - tw_s)//2, ty_b + 150), sku_val, font=f_sku_prod, fill=BLANCO)

    # 7. PIE DE PÁGINA
    draw.rectangle([0, ALTO-200, ANCHO, ALTO], fill=BLANCO)

    path = os.path.join(output_dir, f"{tienda_nombre}_{flyer_count}.jpg")
    flyer.save(path, "JPEG", quality=95)
    return flyer

# --- PROCESO ---
print("Conectando con Google Sheets...")
ss = conectar_sheets()
df = pd.DataFrame(ss.worksheet("Detalle de Inventario").get_all_records())
grupos = df.groupby('Tienda Retail')
tienda_links_pdf = []



for nombre_tienda, grupo in grupos:
    if not str(nombre_tienda).strip(): continue
    print(f"Generando PDF: {nombre_tienda}")
    paginas = []
    indices = grupo.index.tolist()
    
    for i in range(0, len(indices), 6):
        bloque = df.loc[indices[i:i+6]].to_dict('records')
        img_f = crear_flyer(bloque, str(nombre_tienda), (i//6)+1)
        paginas.append(img_f.convert("RGB"))
    
    if paginas:
        t_clean = "".join(x for x in str(nombre_tienda) if x.isalnum())
        pdf_fn = f"PDF_{t_clean}.pdf"
        pdf_path = os.path.join(output_dir, pdf_fn)
        paginas[0].save(pdf_path, save_all=True, append_images=paginas[1:])
        tienda_links_pdf.append([nombre_tienda, f"{URL_BASE_PAGES}{pdf_fn}"])

try:
    hoja_pdf = ss.worksheet("FLYER_TIENDA")
except:
    hoja_pdf = ss.add_worksheet(title="FLYER_TIENDA", rows="100", cols="2")

hoja_pdf.clear()
hoja_pdf.update('A1', [["TIENDA RETAIL", "LINK PDF FLYERS"]] + tienda_links_pdf)
print("¡Proceso Finalizado!")