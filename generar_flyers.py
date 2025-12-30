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

# Colores La Curacao (Negro y Amarillo)
COLOR_AMARILLO = (255, 221, 0)
COLOR_NEGRO = (0, 0, 0)
COLOR_GRIS = (100, 100, 100)

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
    
    # --- 1. FONDO DE CABECERA (IMAGEN TIENDA) ---
    img_tienda_url = "https://gestion.pe/resizer/v2/N32EUI3BE5G6JPABAKRQN7A5AQ.jpg?auth=ebbfe564fe4c0de551f7879f231456528d5271c69fff869aeef04889e5ded81e&width=2212&height=1556&quality=75&smart=true"
    tienda_bg = descargar_imagen(img_tienda_url)
    if tienda_bg:
        tienda_bg = ImageOps.fit(tienda_bg, (1200, 450), method=Image.Resampling.LANCZOS)
        # Filtro oscuro para legibilidad
        overlay = Image.new('RGBA', (1200, 450), (0, 0, 0, 130))
        tienda_bg.paste(overlay, (0, 0), overlay)
        flyer.paste(tienda_bg, (0, 0))

    # --- 2. LOGO CIRCULAR (LA CURACAO) ---
    logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRkl4lFS8XSvCHa8o1t35NE01cSQZQ2KAcVAg&s"
    logo_img = descargar_imagen(logo_url)
    if logo_img:
        logo_img.thumbnail((220, 220))
        # Máscara circular
        mask = Image.new('L', logo_img.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0) + logo_img.size, fill=255)
        
        circulo_blanco = Image.new('RGBA', (240, 240), (0, 0, 0, 0))
        draw_circ = ImageDraw.Draw(circulo_blanco)
        draw_circ.ellipse((0, 0, 240, 240), fill="white")
        
        flyer.paste(circulo_blanco, (920, 30), circulo_blanco)
        flyer.paste(logo_img, (930, 40), mask)

    # --- 3. TEXTOS CABECERA ---
    f_tienda = ImageFont.truetype(FONT_PATH, 55)
    f_slogan = ImageFont.truetype(FONT_PATH, 35)
    
    # Nombre Tienda Centrado en la zona de texto
    draw.text((60, 120), tienda_nombre.upper(), font=f_tienda, fill="white")
    
    # Slogan
    draw.text((60, 360), "¡APROVECHA ESTAS OFERTAS IRRESISTIBLES!", font=f_slogan, fill=COLOR_AMARILLO)

    # --- 4. CUADRÍCULA DE PRODUCTOS (6 espacios) ---
    anchos = [40, 620]
    altos = [480, 920, 1360]
    
    f_marca = ImageFont.truetype(FONT_PATH, 20)
    f_art = ImageFont.truetype(FONT_PATH, 26)
    f_precio = ImageFont.truetype(FONT_PATH, 50)
    f_sku = ImageFont.truetype(FONT_PATH, 22)

    for i, prod in enumerate(productos):
        if i >= 6: break
        col, fila = i % 2, i // 2
        x, y = anchos[col], altos[fila]
        
        # Tarjeta blanca
        draw.rectangle([x, y, x+540, y+420], fill="white", outline=COLOR_NEGRO, width=1)
        
        # Imagen del producto
        img_p = descargar_imagen(prod['image_link'])
        if img_p:
            img_p.thumbnail((260, 260))
            flyer.paste(img_p, (x + (540 - img_p.width)//2, y+15), img_p)
        
        # Información del producto
        draw.text((x+20, y+280), str(prod['Nombre Marca']).upper(), font=f_marca, fill=COLOR_GRIS)
        
        titulo = textwrap.shorten(str(prod['Nombre Articulo']), width=35, placeholder="...")
        draw.text((x+20, y+305), titulo, font=f_art, fill=COLOR_NEGRO)
        
        # Precio en NEGRO (S/. ACTUAL)
        precio = str(prod['S/.ACTUAL']).replace("S/.", "").strip()
        draw.text((x+20, y+335), f"S/ {precio}", font=f_precio, fill=COLOR_NEGRO)
        
        # Código de artículo (%Cod Articulo) sin texto "SKU"
        codigo = str(prod['%Cod Articulo'])
        draw.text((x+20, y+390), codigo, font=f_sku, fill=COLOR_NEGRO)

    # Guardar archivo
    tienda_id = "".join(filter(str.isalnum, tienda_nombre))[:10]
    nombre_archivo = f"flyer_{tienda_id}_{flyer_count}.jpg"
    flyer.save(os.path.join(output_dir, nombre_archivo), "JPEG", quality=85)
    return URL_BASE_PAGES + nombre_archivo

# --- PROCESO PRINCIPAL ---
print("Conectando con Google Sheets...")
hoja = conectar_sheets()
df = pd.DataFrame(hoja.get_all_records())

# Agrupar por Tienda Retail
grupos = df.groupby('Tienda Retail')
links_finales = [""] * len(df)

print(f"Generando flyers para {len(grupos)} tiendas...")
for nombre_tienda, grupo in grupos:
    indices = grupo.index.tolist()
    for i in range(0, len(indices), 6):
        bloque_idx = indices[i:i+6]
        bloque_prod = df.loc[bloque_idx].to_dict('records')
        
        url_flyer = crear_flyer(bloque_prod, str(nombre_tienda), (i//6)+1)
        
        for idx in bloque_idx:
            links_finales[idx] = url_flyer

df['link_flyer'] = links_finales

# Actualización por bloques para estabilidad
print("Sincronizando con Sheets...")
lista_final = [df.columns.tolist()] + df.values.tolist()
hoja.clear()
for i in range(0, len(lista_final), 2000):
    hoja.append_rows(lista_final[i:i+2000])
    time.sleep(2)

print("¡Proceso finalizado exitosamente!")