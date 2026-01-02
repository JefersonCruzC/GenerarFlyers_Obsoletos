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

# --- CONFIGURACIÓN DE LIENZO Y RUTAS ---
ANCHO, ALTO = 2500, 3750  # Resolución pedida
SHEET_ID = "10_VQTvW_Dkpg1rQ-nq2vkATwTwxmoFhqfUIKqxv6Aow"
USUARIO_GITHUB = "JefersonCruzC" 
REPO_NOMBRE = "GenerarFlyers_Obsoletos"
URL_BASE_PAGES = f"https://{USUARIO_GITHUB}.github.io/{REPO_NOMBRE}/flyers/"

# Fuentes (Asegúrate de tener estos archivos en el repo)
FONT_BOLD = "Mark Simonson - Proxima Nova Alt Condensed Bold.otf"
FONT_EXTRABOLD = "Mark Simonson - Proxima Nova Alt Condensed Extrabold.otf"
FONT_REGULAR = "Mark Simonson - Proxima Nova Alt Condensed Regular.otf"
FONT_MEDIUM = "Rubik-Medium.ttf"

# Colores Identidad
CURACAO_AMARILLO = (255, 203, 5)     # Amarillo LC
CURACAO_AMARILLO_OSCURO = (240, 190, 0) # Fondo LC
EFE_AZUL = (0, 50, 130)             # Azul EFE
EFE_NARANJA = (255, 100, 0)         # Naranja EFE
EFE_AZUL_FONDO = (0, 40, 100)       # Fondo EFE
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)

output_dir = "docs/flyers"
os.makedirs(output_dir, exist_ok=True)

# Fecha Perú
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
    # Detectar Marca
    es_efe = "EFE" in tienda_nombre.upper()
    color_fondo_base = EFE_AZUL_FONDO if es_efe else CURACAO_AMARILLO_OSCURO
    color_slogan_bg = EFE_AZUL if es_efe else CURACAO_AMARILLO
    
    flyer = Image.new('RGB', (ANCHO, ALTO), color=color_fondo_base)
    draw = ImageDraw.Draw(flyer)
    
    # 1. CABECERA (Imagen Tienda)
    img_path = "efe tienda.jpg" if es_efe else "LC-MIRAFLORES-LOGO-3D[2].jpg"
    header_h = 1000
    try:
        tienda_bg = Image.open(img_path).convert("RGBA")
        tienda_bg = ImageOps.fit(tienda_bg, (ANCHO, header_h), method=Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', (ANCHO, header_h), (0, 0, 0, 40)) # Más claro como pediste
        tienda_bg.paste(overlay, (0, 0), overlay)
        flyer.paste(tienda_bg, (0, 0))
    except: pass

    # 2. LOGO Y TIENDA (DERECHA SUPERIOR)
    logo_url = "https://images.seeklogo.com/logo-png/34/1/tiendas-efe-logo-png_seeklogo-342334.png" if es_efe else "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRkl4lFS8XSvCHa8o1t35NE01cSQZQ2KAcVAg&s"
    logo_img = descargar_imagen(logo_url)
    if logo_img:
        # Contenedor Blanco Logo
        rect_w, rect_h = 500, 450
        if es_efe: # Circulo para EFE
            draw.ellipse([ANCHO-550, 50, ANCHO-50, 550], fill=BLANCO)
            logo_img.thumbnail((400, 400))
            flyer.paste(logo_img, (ANCHO-550 + (500-logo_img.width)//2, 50 + (500-logo_img.height)//2), logo_img)
        else: # Rectangulo redondeado abajo para LC
            draw.rounded_rectangle([ANCHO-550, 0, ANCHO-50, 400], radius=50, fill=BLANCO)
            logo_img.thumbnail((350, 350))
            flyer.paste(logo_img, (ANCHO-550 + (500-logo_img.width)//2, 25), logo_img)

    # Nombre Tienda (Rombo / Ovalado)
    f_tienda = ImageFont.truetype(FONT_BOLD, 80)
    tw = draw.textlength(tienda_nombre, font=f_tienda)
    bg_tienda = EFE_NARANJA if es_efe else BLANCO
    txt_tienda_color = BLANCO if es_efe else NEGRO
    # Dibujar forma (Simplificado a rounded rect para legibilidad técnica)
    draw.rounded_rectangle([ANCHO-tw-150, 580 if es_efe else 450, ANCHO-50, 750 if es_efe else 600], radius=40, fill=bg_tienda)
    draw.text((ANCHO-tw-100, 610 if es_efe else 480), tienda_nombre.upper(), font=f_tienda, fill=txt_tienda_color)

    # 3. FECHA GENERADO (IZQUIERDA)
    f_fecha = ImageFont.truetype(FONT_REGULAR, 50)
    txt_gen = f"Generado: {fecha_peru}"
    tw_gen = draw.textlength(txt_gen, font=f_fecha)
    draw.rounded_rectangle([0, 850, tw_gen+100, 980], radius=50, fill=BLANCO) # Redondeado solo derecha (esquina simplificada)
    draw.text((40, 885), txt_gen, font=f_fecha, fill=NEGRO)

    # 4. SLOGAN (CENTRO)
    f_slogan = ImageFont.truetype(FONT_EXTRABOLD, 100)
    slogan = "¡APROVECHA ESTAS INCREÍBLES OFERTAS!"
    sw = draw.textlength(slogan, font=f_slogan)
    draw.rectangle([0, 1050, ANCHO, 1250], fill=color_slogan_bg)
    draw.text(((ANCHO-sw)//2, 1090), slogan, font=f_slogan, fill=BLANCO if es_efe else NEGRO)

    # 5. PRODUCTOS (Cuadrícula 2x3)
    anchos = [100, 1300]
    altos = [1350, 2100, 2850]
    f_marca = ImageFont.truetype(FONT_EXTRABOLD, 55)
    f_art = ImageFont.truetype(FONT_REGULAR, 65)
    f_precio = ImageFont.truetype(FONT_EXTRABOLD, 120)
    f_simbolo = ImageFont.truetype(FONT_REGULAR, 70)
    f_sku = ImageFont.truetype(FONT_BOLD, 50)

    for i, prod in enumerate(productos):
        if i >= 6: break
        x, y = anchos[i%2], altos[i//2]
        # Tarjeta blanca
        draw.rounded_rectangle([x, y, x+1100, y+700], radius=60, fill=BLANCO)
        
        # Imagen Producto
        img_p = descargar_imagen(prod['image_link'])
        if img_p:
            img_p.thumbnail((500, 500))
            flyer.paste(img_p, (x+40, y + (700-img_p.height)//2), img_p)
        
        # Textos Derecha
        tx = x + 580
        # Marca
        draw.text((tx, y + 80), str(prod['Nombre Marca']).upper(), font=f_marca, fill=NEGRO)
        # Título
        lines = textwrap.wrap(str(prod['Nombre Articulo']), width=18)
        ty = y + 170
        for line in lines[:3]:
            draw.text((tx, ty), line, font=f_art, fill=NEGRO)
            ty += 75
            
        # BLOQUE PRECIO + SKU
        p_col = EFE_AZUL if es_efe else CURACAO_AMARILLO
        s_col = EFE_NARANJA if es_efe else NEGRO
        p_texto = formatear_precio(prod['S/.ACTUAL'])
        
        # Recuadro Precio
        draw.rounded_rectangle([tx, y+450, tx+480, y+600], radius=30, fill=p_col)
        draw.text((tx+30, y+490), "S/", font=f_simbolo, fill=BLANCO if es_efe else NEGRO)
        draw.text((tx+120, y+465), p_texto, font=f_precio, fill=BLANCO if es_efe else NEGRO)
        
        # Recuadro SKU (Pegado abajo)
        sku_val = str(prod['%Cod Articulo'])
        draw.rounded_rectangle([tx+40, y+600, tx+440, y+680], radius=20, fill=s_col)
        sw_sku = draw.textlength(sku_val, font=f_sku)
        draw.text((tx+40 + (400-sw_sku)//2, y+615), sku_val, font=f_sku, fill=BLANCO)

    # 6. ESPACIO LEGAL (BLANCO AL FINAL)
    draw.rectangle([0, ALTO-150, ANCHO, ALTO], fill=BLANCO)

    path = os.path.join(output_dir, f"{tienda_nombre}_{flyer_count}.jpg")
    flyer.save(path, "JPEG", quality=90)
    return flyer

# --- PROCESO ---
spreadsheet = conectar_sheets()
df = pd.DataFrame(spreadsheet.worksheet("Detalle de Inventario").get_all_records())
grupos_tienda = df.groupby('Tienda Retail')
tienda_links_pdf = []



for nombre_tienda, grupo in grupos_tienda:
    if not str(nombre_tienda).strip(): continue
    print(f"Generando: {nombre_tienda}")
    paginas_img = []
    indices = grupo.index.tolist()
    
    for i in range(0, len(indices), 6):
        bloque = df.loc[indices[i:i+6]].to_dict('records')
        img_pag = crear_flyer(bloque, str(nombre_tienda), (i//6)+1)
        paginas_img.append(img_pag.convert("RGB"))
    
    if paginas_img:
        tienda_clean = "".join(x for x in str(nombre_tienda) if x.isalnum())
        pdf_fn = f"PDF_{tienda_clean}.pdf"
        pdf_path = os.path.join(output_dir, pdf_fn)
        paginas_img[0].save(pdf_path, save_all=True, append_images=paginas_img[1:])
        url_pdf = f"https://{USUARIO_GITHUB}.github.io/{REPO_NOMBRE}/flyers/{pdf_fn}"
        tienda_links_pdf.append([nombre_tienda, url_pdf])

try:
    hoja_pdf = spreadsheet.worksheet("FLYER_TIENDA")
except:
    hoja_pdf = spreadsheet.add_worksheet(title="FLYER_TIENDA", rows="100", cols="2")

hoja_pdf.clear()
hoja_pdf.update('A1', [["TIENDA RETAIL", "LINK PDF FLYERS"]] + tienda_links_pdf)
print("¡Proceso finalizado!")