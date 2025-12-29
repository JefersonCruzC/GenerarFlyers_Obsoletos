import pandas as pd
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import gspread
import json
import textwrap
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
SHEET_ID = "10_VQTvW_Dkpg1rQ-nq2vkATwTwxmoFhqfUIKqxv6Aow"
USUARIO_GITHUB = "JefersonCruzC" 
REPO_NOMBRE = "GenerarFlyers_Juntoz" # Nombre de tu nuevo repo
URL_BASE_PAGES = f"https://{USUARIO_GITHUB}.github.io/{REPO_NOMBRE}/flyers/"
FONT_PATH = "LiberationSans-Bold.ttf"

output_dir = "docs/flyers"
os.makedirs(output_dir, exist_ok=True)

def conectar_sheets():
    info_creds = json.loads(os.environ['GOOGLE_SHEETS_JSON'])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(info_creds, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def descargar_imagen(url):
    if not url or str(url) == 'nan':
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return Image.open(BytesIO(res.content)).convert("RGBA")
        return None
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return None

def crear_flyer(productos, flyer_id):
    # Lienzo: 1200 ancho x 1800 alto
    flyer = Image.new('RGB', (1200, 1800), color='white')
    draw = ImageDraw.Draw(flyer)
    
    # --- CABECERA ---
    # Dibujar fondo morado arriba
    draw.rectangle([0, 0, 1200, 400], fill=(102, 0, 153))
    # Logo
    logo_img = descargar_imagen("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQfE4betnoplLem-rHmrOt2gqS7zMBYV8D3aw&s")
    if logo_img:
        logo_img.thumbnail((300, 150))
        flyer.paste(logo_img, (450, 50), logo_img)
    
    # Texto Cabecera
    f_header = ImageFont.truetype(FONT_PATH, 60)
    draw.text((350, 200), "BOMBAS DEL MES", font=f_header, fill="white")
    
    # --- CUADRÍCULA DE PRODUCTOS (2 columnas x 3 filas) ---
    anchos = [50, 625] # X para col 1 y col 2
    altos = [450, 900, 1350] # Y para fila 1, 2 y 3
    
    f_marca = ImageFont.truetype(FONT_PATH, 22)
    f_promo = ImageFont.truetype(FONT_PATH, 40)
    f_precio = ImageFont.truetype(FONT_PATH, 25)

    for i, prod in enumerate(productos):
        col = i % 2
        fila = i // 2
        x = anchos[col]
        y = altos[fila]
        
        # Marco del producto
        draw.rectangle([x, y, x+520, y+420], outline=(230, 230, 230), width=2)
        
        # Imagen
        img_prod = descargar_imagen(prod['image_link'])
        if img_prod:
            img_prod.thumbnail((250, 250))
            flyer.paste(img_prod, (x+135, y+20), img_prod)
        
        # Datos: Marca y Título
        draw.text((x+20, y+280), str(prod['brand'])[:20], font=f_marca, fill="gray")
        titulo_corto = textwrap.shorten(str(prod['title']), width=35, placeholder="...")
        draw.text((x+20, y+310), titulo_corto, font=f_marca, fill="black")
        
        # Precios
        p_sale = str(prod['sale_price']).replace(" PEN", "")
        draw.text((x+20, y+350), f"S/ {p_sale}", font=f_promo, fill="red")
        
        p_reg = "S/ " + str(prod['price']).replace(" PEN", "")
        draw.text((x+300, y+365), p_reg, font=f_precio, fill="gray")
        draw.line([x+300, y+375, x+450, y+375], fill="gray", width=2)

    # Guardar
    nombre_archivo = f"flyer_{flyer_id}.jpg"
    flyer.save(os.path.join(output_dir, nombre_archivo), "JPEG", quality=85)
    return URL_BASE_PAGES + nombre_archivo

# --- PROCESO ---
hoja = conectar_sheets()
df = pd.DataFrame(hoja.get_all_records())

print(f"Leídos {len(df)} productos. Generando flyers...")

links_generados = ["" for _ in range(len(df))]

# Procesar en grupos de 6
for i in range(0, len(df), 6):
    grupo = df.iloc[i : i+6].to_dict('records')
    # flyer_id usamos el ID del primer producto del grupo
    flyer_url = crear_flyer(grupo, grupo[0]['id'])
    
    # Asignar el mismo link a los 6 espacios correspondientes
    for j in range(len(grupo)):
        links_generados[i + j] = flyer_url

# Actualizar Google Sheets con la nueva columna
df['link_flyer'] = links_generados
lista_final = [df.columns.tolist()] + df.values.tolist()
hoja.clear()
hoja.update('A1', lista_final)
print("¡Flyers generados y Sheets actualizado!")