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

# Colores Corporativos
COLOR_AMARILLO = (255, 221, 0)
COLOR_NEGRO = (0, 0, 0)
COLOR_GRIS_TEXTO = (80, 80, 80)
COLOR_BLANCO = (255, 255, 255)

output_dir = "docs/flyers"
os.makedirs(output_dir, exist_ok=True)

def conectar_sheets():
    info_creds = json.loads(os.environ['GOOGLE_SHEETS_JSON'])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info_creds, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet("Detalle de Inventario")

def descargar_imagen(url):
    if not url or str(url).lower() == 'nan' or str(url).strip() == "":
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=7)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content)).convert("RGBA")
    except:
        return None

def crear_flyer(productos, tienda_nombre, flyer_count):
    # Lienzo Principal
    flyer = Image.new('RGB', (1200, 1800), color=COLOR_AMARILLO)
    draw = ImageDraw.Draw(flyer)
    
    # --- 1. CABECERA CON IMAGEN Y RECUADROS OVALADOS ---
    img_tienda_url = "https://gestion.pe/resizer/v2/N32EUI3BE5G6JPABAKRQN7A5AQ.jpg?auth=ebbfe564fe4c0de551f7879f231456528d5271c69fff869aeef04889e5ded81e&width=2212&height=1556&quality=75&smart=true"
    tienda_bg = descargar_imagen(img_tienda_url)
    if tienda_bg:
        tienda_bg = ImageOps.fit(tienda_bg, (1200, 480), method=Image.Resampling.LANCZOS)
        # Filtro oscuro
        overlay = Image.new('RGBA', (1200, 480), (0, 0, 0, 100))
        tienda_bg.paste(overlay, (0, 0), overlay)
        flyer.paste(tienda_bg, (0, 0))

    # Logo Circular
    logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRkl4lFS8XSvCHa8o1t35NE01cSQZQ2KAcVAg&s"
    logo_img = descargar_imagen(logo_url)
    if logo_img:
        logo_img.thumbnail((200, 200))
        mask = Image.new('L', logo_img.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + logo_img.size, fill=255)
        
        circulo_blanco = Image.new('RGBA', (220, 220), (0, 0, 0, 0))
        draw_circ = ImageDraw.Draw(circulo_blanco)
        draw_circ.ellipse((0, 0, 220, 220), fill="white")
        flyer.paste(circulo_blanco, (930, 30), circulo_blanco)
        flyer.paste(logo_img, (940, 40), mask)

    # Recuadro Ovalado para Nombre de Tienda
    f_tienda = ImageFont.truetype(FONT_PATH, 35)
    texto_tienda = f"TIENDA: {tienda_nombre.upper()}"
    tw = draw.textlength(texto_tienda, font=f_tienda)
    draw.rounded_rectangle([900 - tw, 260, 1150, 340], radius=40, fill=COLOR_AMARILLO)
    draw.text((1120 - tw, 275), texto_tienda, font=f_tienda, fill=COLOR_NEGRO)

    # Recuadro Ovalado para Eslogan (Centrado)
    f_slogan = ImageFont.truetype(FONT_PATH, 42)
    slogan = "¡APROVECHA ESTAS OFERTAS IRRESISTIBLES!"
    draw.rounded_rectangle([100, 390, 1100, 490], radius=50, fill=COLOR_NEGRO)
    draw.text((600 - draw.textlength(slogan, f_slogan)//2, 415), slogan, font=f_slogan, fill=COLOR_AMARILLO)

    # --- 2. PRODUCTOS (DISEÑO HORIZONTAL CON BORDES REDONDEADOS) ---
    anchos = [30, 615]
    altos = [530, 950, 1370]
    
    f_marca = ImageFont.truetype(FONT_PATH, 18)
    f_art = ImageFont.truetype(FONT_PATH, 22)
    f_precio = ImageFont.truetype(FONT_PATH, 45)
    f_sku = ImageFont.truetype(FONT_PATH, 20)

    for i, prod in enumerate(productos):
        if i >= 6: break
        col, fila = i % 2, i // 2
        x, y = anchos[col], altos[fila]
        
        # Tarjeta blanca con bordes redondeados
        draw.rounded_rectangle([x, y, x+555, y+400], radius=30, fill=COLOR_BLANCO)
        
        # Imagen del producto (A LA IZQUIERDA)
        img_p = descargar_imagen(prod['image_link'])
        if img_p:
            img_p.thumbnail((240, 240))
            flyer.paste(img_p, (x+15, y + (400 - img_p.height)//2), img_p)
        
        # Área de Texto (A LA DERECHA)
        tx = x + 265
        ty = y + 40
        
        # Marca
        draw.text((tx, ty), str(prod['Nombre Marca']).upper(), font=f_marca, fill=COLOR_GRIS_TEXTO)
        
        # Título Completo (Multilínea)
        titulo = str(prod['Nombre Articulo'])
        wrapped_art = textwrap.wrap(titulo, width=22)
        ty += 30
        for line in wrapped_art[:3]:
            draw.text((tx, ty), line, font=f_art, fill=COLOR_NEGRO)
            ty += 30
            
        # Recuadro de Precio
        precio = str(prod['S/.ACTUAL']).replace("S/.", "").strip()
        draw.rounded_rectangle([tx, ty+10, tx+260, ty+80], radius=15, fill=COLOR_AMARILLO)
        draw.text((tx+15, ty+20), f"S/ {precio}", font=f_precio, fill=COLOR_NEGRO)
        
        # Recuadro de SKU (Abajo del precio)
        codigo = str(prod['%Cod Articulo'])
        draw.rounded_rectangle([tx, ty+90, tx+200, ty+130], radius=10, fill=COLOR_NEGRO)
        draw.text((tx+15, ty+98), codigo, font=f_sku, fill=COLOR_BLANCO)

    # Guardar
    tienda_id = "".join(filter(str.isalnum, tienda_nombre))[:10]
    nombre_archivo = f"flyer_{tienda_id}_{flyer_count}.jpg"
    flyer.save(os.path.join(output_dir, nombre_archivo), "JPEG", quality=85)
    return URL_BASE_PAGES + nombre_archivo

# --- PROCESO PRINCIPAL ---
hoja = conectar_sheets()
df = pd.DataFrame(hoja.get_all_records())
grupos = df.groupby('Tienda Retail')
links_finales = [""] * len(df)

for nombre_tienda, grupo in grupos:
    indices = grupo.index.tolist()
    for i in range(0, len(indices), 6):
        bloque_idx = indices[i:i+6]
        bloque_prod = df.loc[bloque_idx].to_dict('records')
        url_flyer = crear_flyer(bloque_prod, str(nombre_tienda), (i//6)+1)
        for idx in bloque_idx:
            links_finales[idx] = url_flyer

df['link_flyer'] = links_finales
lista_final = [df.columns.tolist()] + df.values.tolist()
hoja.clear()
for i in range(0, len(lista_final), 2000):
    hoja.append_rows(lista_final[i:i+2000])
    time.sleep(2)