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
    return client.open_by_key(SHEET_ID)

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
    
    # 1. CABECERA
    img_tienda_url = "https://gestion.pe/resizer/v2/N32EUI3BE5G6JPABAKRQN7A5AQ.jpg?auth=ebbfe564fe4c0de551f7879f231456528d5271c69fff869aeef04889e5ded81e&width=2212&height=1556&quality=75&smart=true"
    tienda_bg = descargar_imagen(img_tienda_url)
    if tienda_bg:
        tienda_bg = ImageOps.fit(tienda_bg, (1200, 450), method=Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', (1200, 450), (0, 0, 0, 80))
        tienda_bg.paste(overlay, (0, 0), overlay)
        flyer.paste(tienda_bg, (0, 0))

    # Logo (Separado del recuadro de tienda)
    logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRkl4lFS8XSvCHa8o1t35NE01cSQZQ2KAcVAg&s"
    logo_img = descargar_imagen(logo_url)
    if logo_img:
        size = 210
        logo_img = ImageOps.fit(logo_img, (size, size), method=Image.Resampling.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        circ_size = 230
        circulo = Image.new('RGBA', (circ_size, circ_size), (0,0,0,0))
        ImageDraw.Draw(circulo).ellipse((0, 0, circ_size, circ_size), fill="white")
        flyer.paste(circulo, (940, 20), circulo)
        flyer.paste(logo_img, (940 + (circ_size-size)//2, 20 + (circ_size-size)//2), mask)

    # Recuadro Tienda Adaptativo (Bajado para evitar al logo)
    f_tienda = ImageFont.truetype(FONT_PATH, 35)
    txt_tienda = f"TIENDA: {tienda_nombre.upper()}"
    tw = draw.textlength(txt_tienda, font=f_tienda)
    padding_h = 25
    # Definimos el recuadro a la derecha, pero con margen superior respecto al logo
    draw.rounded_rectangle([1170 - tw - (padding_h*2), 280, 1170, 360], radius=40, fill=COLOR_AMARILLO)
    draw.text((1170 - tw - padding_h, 295), txt_tienda, font=f_tienda, fill=COLOR_NEGRO)

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
    f_simbolo = ImageFont.truetype(FONT_PATH, 28) # Símbolo S/ más pequeño
    f_sku = ImageFont.truetype(FONT_PATH, 20)

    for i, prod in enumerate(productos):
        if i >= 6: break
        x, y = anchos[i%2], altos[i//2]
        draw.rounded_rectangle([x, y, x+555, y+400], radius=30, fill=COLOR_BLANCO)
        
        img_p = descargar_imagen(prod['image_link'])
        if img_p:
            img_p.thumbnail((230, 230))
            flyer.paste(img_p, (x+20, y + (400-img_p.height)//2), img_p)
        
        tx, ty = x + 265, y + 60 # Bajamos el inicio del texto
        
        # Marca
        marca_txt = str(prod['Nombre Marca']).upper()
        draw.text((tx + (260 - draw.textlength(marca_txt, f_marca))//2, ty), marca_txt, font=f_marca, fill=COLOR_GRIS_TEXTO)
        
        ty += 35
        # Título
        lines = textwrap.wrap(str(prod['Nombre Articulo']), width=22)
        for line in lines[:2]: # Limitado a 2 para dejar espacio abajo
            draw.text((tx, ty), line, font=f_art, fill=COLOR_NEGRO)
            ty += 28
            
        # Bloque Precio + SKU Centrados y Redondeados
        ty_bloque = y + 230 # Espacio entre título y recuadros
        
        # Procesar Precio (Corrección de coma)
        raw_price = str(prod['S/.ACTUAL']).replace("S/.", "").strip()
        if "," in raw_price and "." not in raw_price:
            raw_price = raw_price.replace(",", ".")
        
        # Dibujar Recuadro Precio (Amarillo)
        draw.rounded_rectangle([tx, ty_bloque, tx+265, ty_bloque + 80], radius=20, fill=COLOR_AMARILLO)
        # Centrar "S/ 00.00"
        full_p_txt = f"S/ {raw_price}"
        tw_p = draw.textlength(full_p_txt, font=f_precio) # Aproximación para centrado
        # Dibujamos S/ pequeño y luego el precio
        draw.text((tx + 25, ty_bloque + 25), "S/", font=f_simbolo, fill=COLOR_NEGRO)
        draw.text((tx + 65, ty_bloque + 12), raw_price, font=f_precio, fill=COLOR_NEGRO)
        
        # Dibujar Recuadro SKU (Negro)
        sku_val = str(prod['%Cod Articulo'])
        draw.rounded_rectangle([tx, ty_bloque + 85, tx+265, ty_bloque + 125], radius=15, fill=COLOR_NEGRO)
        tw_sku = draw.textlength(sku_val, font=f_sku)
        draw.text((tx + (265 - tw_sku)//2, ty_bloque + 93), sku_val, font=f_sku, fill=COLOR_BLANCO)

    path = os.path.join(output_dir, f"{tienda_nombre}_{flyer_count}.jpg")
    flyer.save(path, "JPEG", quality=85)
    return flyer

# --- PROCESO ---
spreadsheet = conectar_sheets()
df = pd.DataFrame(spreadsheet.worksheet("Detalle de Inventario").get_all_records())
grupos_tienda = df.groupby('Tienda Retail')
tienda_links_pdf = []

for nombre_tienda, grupo in grupos_tienda:
    if str(nombre_tienda).strip() == "": continue
    print(f"Generando PDF para: {nombre_tienda}")
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

# Actualizar Pestaña FLYER_TIENDA
try:
    hoja_pdf = spreadsheet.worksheet("FLYER_TIENDA")
except:
    hoja_pdf = spreadsheet.add_worksheet(title="FLYER_TIENDA", rows="100", cols="2")

hoja_pdf.clear()
hoja_pdf.update('A1', [["TIENDA RETAIL", "LINK PDF FLYERS"]] + tienda_links_pdf)
print("¡Todo listo!")