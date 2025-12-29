import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont
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

output_dir = "docs/flyers"
os.makedirs(output_dir, exist_ok=True)

def conectar_sheets():
    info_creds = json.loads(os.environ['GOOGLE_SHEETS_JSON'])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info_creds, scope)
    client = gspread.authorize(creds)
    # Seleccionamos específicamente la hoja por nombre
    return client.open_by_key(SHEET_ID).worksheet("Detalle de Inventario")

def descargar_imagen(url):
    if not url or str(url).lower() == 'nan' or str(url).strip() == "":
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content)).convert("RGBA")
    except:
        return None

def crear_flyer(productos, tienda_nombre, flyer_count):
    flyer = Image.new('RGB', (1200, 1800), color='white')
    draw = ImageDraw.Draw(flyer)
    
    # CABECERA
    draw.rectangle([0, 0, 1200, 400], fill=(102, 0, 153))
    logo_img = descargar_imagen("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQfE4betnoplLem-rHmrOt2gqS7zMBYV8D3aw&s")
    if logo_img:
        logo_img.thumbnail((300, 150))
        flyer.paste(logo_img, (450, 40), logo_img)
    
    # Título dinámico con nombre de tienda
    f_header = ImageFont.truetype(FONT_PATH, 50)
    # Ajustar texto largo de tienda
    wrapped_tienda = textwrap.wrap(tienda_nombre.upper(), width=30)
    y_header = 180
    for line in wrapped_tienda[:2]:
        draw.text((600 - draw.textlength(line, f_header)//2, y_header), line, font=f_header, fill="white")
        y_header += 70

    # CUADRÍCULA
    anchos = [50, 625]
    altos = [450, 900, 1350]
    
    f_marca = ImageFont.truetype(FONT_PATH, 22)
    f_titulo = ImageFont.truetype(FONT_PATH, 24)
    f_promo = ImageFont.truetype(FONT_PATH, 45)
    f_codigo = ImageFont.truetype(FONT_PATH, 28)

    for i, prod in enumerate(productos):
        if i >= 6: break
        col, fila = i % 2, i // 2
        x, y = anchos[col], altos[fila]
        
        draw.rectangle([x, y, x+520, y+420], outline=(230, 230, 230), width=2)
        
        img_prod = descargar_imagen(prod['image_link'])
        if img_prod:
            img_prod.thumbnail((250, 250))
            flyer.paste(img_prod, (x + (520 - img_prod.width)//2, y+20), img_prod)
        
        # Datos
        draw.text((x+20, y+280), str(prod['Nombre Marca'])[:30], font=f_marca, fill="gray")
        titulo = textwrap.shorten(str(prod['Nombre Articulo']), width=35, placeholder="...")
        draw.text((x+20, y+310), titulo, font=f_titulo, fill="black")
        
        # Precio y Código Articulo debajo
        p_sale = str(prod['S/.ACTUAL']).replace("S/.", "").strip()
        draw.text((x+20, y+345), f"S/ {p_sale}", font=f_promo, fill="red")
        
        cod_art = f"SKU: {prod['%Cod Articulo']}"
        draw.text((x+20, y+395), cod_art, font=f_codigo, fill=(102, 0, 153))

    # Nombre archivo: Tienda + correlativo
    tienda_clean = "".join(x for x in tienda_nombre if x.isalnum())[:15]
    nombre_archivo = f"flyer_{tienda_clean}_{flyer_count}.jpg"
    flyer.save(os.path.join(output_dir, nombre_archivo), "JPEG", quality=80, optimize=True)
    return URL_BASE_PAGES + nombre_archivo

# --- PROCESO PRINCIPAL ---
hoja = conectar_sheets()
data = hoja.get_all_records()
df = pd.DataFrame(data)

# Agrupar por Tienda Retail
grupos_tienda = df.groupby('Tienda Retail')
links_resultado = [""] * len(df)

print(f"Procesando {len(grupos_tienda)} tiendas...")

for nombre_tienda, group in grupos_tienda:
    indices = group.index.tolist()
    # Procesar productos de esta tienda en bloques de 6
    for i in range(0, len(indices), 6):
        bloque_indices = indices[i:i+6]
        bloque_productos = df.loc[bloque_indices].to_dict('records')
        
        # Crear flyer
        url_flyer = crear_flyer(bloque_productos, str(nombre_tienda), i//6 + 1)
        
        # Asignar URL a cada producto del bloque
        for idx in bloque_indices:
            links_resultado[idx] = url_flyer

df['link_flyer'] = links_resultado

# Actualizar Google Sheets por bloques (Resistencia para 10k filas)
print("Actualizando Google Sheets...")
lista_final = [df.columns.tolist()] + df.values.tolist()
hoja.clear()

for i in range(0, len(lista_final), 2000):
    hoja.append_rows(lista_final[i:i+2000])
    print(f"Sincronizados {i+2000} registros...")
    time.sleep(2)

print("¡Todo listo!")