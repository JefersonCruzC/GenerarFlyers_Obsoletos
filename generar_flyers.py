import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import os
import gspread
import json
import textwrap
import time
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
SHEET_ID = "10_VQTvW_Dkpg1rQ-nq2vkATwTwxmoFhqfUIKqxv6Aow"
USUARIO_GITHUB = "JefersonCruzC" 
REPO_NOMBRE = "GenerarFlyers_Obsoletos"
URL_BASE_PAGES = f"https://{USUARIO_GITHUB}.github.io/{REPO_NOMBRE}/flyers/"
FONT_PATH = "LiberationSans-Bold.ttf"

# Colores
COLOR_AMARILLO = (255, 221, 0)
COLOR_NEGRO = (0, 0, 0)
COLOR_BLANCO = (255, 255, 255)
COLOR_GRIS_TEXTO = (60, 60, 60)

output_dir = "docs/flyers"
os.makedirs(output_dir, exist_ok=True)

def conectar_sheets():
    info_creds = json.loads(os.environ['GOOGLE_SHEETS_JSON'])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info_creds, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    return spreadsheet

def descargar_imagen(url):
    if not url or str(url).lower() == 'nan' or str(url).strip() == "":
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=7)
        return Image.open(BytesIO(res.content)).convert("RGBA")
    except:
        return None

def crear_flyer(productos, tienda_nombre, flyer_count):
    flyer = Image.new('RGB', (1200, 1800), color=COLOR_AMARILLO)
    draw = ImageDraw.Draw(flyer)
    
    # 1. CABECERA (Fondo imagen tienda)
    img_tienda_url = "https://gestion.pe/resizer/v2/N32EUI3BE5G6JPABAKRQN7A5AQ.jpg?auth=ebbfe564fe4c0de551f7879f231456528d5271c69fff869aeef04889e5ded81e&width=2212&height=1556&quality=75&smart=true"
    tienda_bg = descargar_imagen(img_tienda_url)
    header_h = 450
    if tienda_bg:
        tienda_bg = ImageOps.fit(tienda_bg, (1200, header_h), method=Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', (1200, header_h), (0, 0, 0, 80)) # Menos oscuro
        tienda_bg.paste(overlay, (0, 0), overlay)
        flyer.paste(tienda_bg, (0, 0))

    # Logo Centrado en Círculo
    logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRkl4lFS8XSvCHa8o1t35NE01cSQZQ2KAcVAg&s"
    logo_img = descargar_imagen(logo_url)
    if logo_img:
        size = 220
        logo_img = ImageOps.fit(logo_img, (size, size), method=Image.Resampling.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        
        circ_size = 240
        circulo = Image.new('RGBA', (circ_size, circ_size), (0,0,0,0))
        ImageDraw.Draw(circulo).ellipse((0, 0, circ_size, circ_size), fill="white")
        
        flyer.paste(circulo, (930, 30), circulo)
        flyer.paste(logo_img, (930 + (circ_size-size)//2, 30 + (circ_size-size)//2), mask)

    # Recuadro Tienda Adaptativo
    f_tienda = ImageFont.truetype(FONT_PATH, 35)
    txt_tienda = f"TIENDA: {tienda_nombre.upper()}"
    tw = draw.textlength(txt_tienda, font=f_tienda)
    padding = 30
    draw.rounded_rectangle([1150 - tw - (padding*2), 270, 1150, 350], radius=40, fill=COLOR_AMARILLO)
    draw.text((1150 - tw - padding, 285), txt_tienda, font=f_tienda, fill=COLOR_NEGRO)

    # Eslogan Nivelado
    f_slogan = ImageFont.truetype(FONT_PATH, 42)
    slogan = "¡APROVECHA ESTAS OFERTAS IRRESISTIBLES!"
    sw = draw.textlength(slogan, font=f_slogan)
    draw.rounded_rectangle([600 - sw//2 - 40, 400, 600 + sw//2 + 40, 500], radius=50, fill=COLOR_NEGRO)
    draw.text((600 - sw//2, 425), slogan, font=f_slogan, fill=COLOR_AMARILLO)

    # 2. PRODUCTOS
    anchos = [30, 615]
    altos = [530, 950, 1370]
    f_marca = ImageFont.truetype(FONT_PATH, 18)
    f_art = ImageFont.truetype(FONT_PATH, 22)
    f_precio = ImageFont.truetype(FONT_PATH, 48)
    f_sku = ImageFont.truetype(FONT_PATH, 20)

    for i, prod in enumerate(productos):
        if i >= 6: break
        x, y = anchos[i%2], altos[i//2]
        draw.rounded_rectangle([x, y, x+555, y+400], radius=30, fill=COLOR_BLANCO)
        
        img_p = descargar_imagen(prod['image_link'])
        if img_p:
            img_p.thumbnail((230, 230))
            flyer.paste(img_p, (x+20, y + (400-img_p.height)//2), img_p)
        
        # Textos a la derecha
        tx, ty = x + 265, y + 40
        draw.text((tx + (260 - draw.textlength(str(prod['Nombre Marca']).upper(), f_marca))//2, ty), str(prod['Nombre Marca']).upper(), font=f_marca, fill=COLOR_GRIS_TEXTO)
        
        ty += 35
        lines = textwrap.wrap(str(prod['Nombre Articulo']), width=22)
        for line in lines[:3]:
            draw.text((tx, ty), line, font=f_art, fill=COLOR_NEGRO)
            ty += 28
            
        # Bloque Precio + SKU unido
        ty_bloque = y + 240
        precio = str(prod['S/.ACTUAL']).replace("S/.", "").strip()
        draw.rectangle([tx, ty_bloque, tx+260, ty_bloque + 80], fill=COLOR_AMARILLO)
        draw.text((tx+15, ty_bloque + 15), f"S/ {precio}", font=f_precio, fill=COLOR_NEGRO)
        
        sku = str(prod['%Cod Articulo'])
        draw.rectangle([tx, ty_bloque + 80, tx+260, ty_bloque + 120], fill=COLOR_NEGRO)
        draw.text((tx+15, ty_bloque + 88), sku, font=f_sku, fill=COLOR_BLANCO)

    path = os.path.join(output_dir, f"{tienda_nombre}_{flyer_count}.jpg")
    flyer.save(path, "JPEG", quality=85)
    return flyer

# --- PROCESO PRINCIPAL ---
ss = conectar_sheets()
hoja_inv = ss.worksheet("Detalle de Inventario")
df = pd.DataFrame(hoja_inv.get_all_records())

grupos_tienda = df.groupby('Tienda Retail')
tienda_links_pdf = []



for nombre_tienda, grupo in grupos_tienda:
    print(f"Procesando Tienda: {nombre_tienda}")
    lista_img_tienda = []
    indices = grupo.index.tolist()
    
    for i in range(0, len(indices), 6):
        bloque = df.loc[indices[i:i+6]].to_dict('records')
        img_flyer = crear_flyer(bloque, str(nombre_tienda), (i//6)+1)
        lista_img_tienda.append(img_flyer.convert("RGB"))
    
    # Generar PDF
    pdf_path = os.path.join(output_dir, f"PDF_{nombre_tienda}.pdf")
    if lista_img_tienda:
        lista_img_tienda[0].save(pdf_path, save_all=True, append_images=lista_img_tienda[1:])
        url_pdf = f"https://{USUARIO_GITHUB}.github.io/{REPO_NOMBRE}/flyers/PDF_{nombre_tienda}.pdf"
        tienda_links_pdf.append([nombre_tienda, url_pdf])

# Actualizar Pestaña FLYER_TIENDA
try:
    hoja_pdf = ss.worksheet("FLYER_TIENDA")
except:
    hoja_pdf = ss.add_worksheet(title="FLYER_TIENDA", rows="100", cols="2")

hoja_pdf.clear()
hoja_pdf.update('A1', [["TIENDA RETAIL", "LINK PDF FLYERS"]] + tienda_links_pdf)

print("¡Proceso finalizado con PDFs generados!")