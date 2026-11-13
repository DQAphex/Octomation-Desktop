import fitz  # PyMuPDF
import hashlib

def extraer_imagenes_pdf(archivo_pdf):
    # Abrir el documento PDF
    doc = fitz.open(archivo_pdf)
    
    contador = 0
    # Recorrer cada página del documento
    for num_pagina in range(len(doc)):
        page = doc[num_pagina]
        
        # Obtener la lista de todas las imágenes en la página
        image_list = page.get_images(full=True)
        
        print(f"Página {num_pagina + 1}: Se encontraron {len(image_list)} imágenes.")
        
        for img_index, img in enumerate(image_list):
            # Obtener el xref (referencia única de la imagen en el PDF)
            xref = img[0]
            
            # Extraer la información y los bytes de la imagen
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]  # Extensión original (png, jpeg, etc.)
            
            # Guardar la imagen en el disco
            nombre_archivo = f"imagen_p{num_pagina + 1}_{img_index + 1}.{image_ext}"
            with open(nombre_archivo, "wb") as f:
                f.write(image_bytes)
                
            print(f"  -> Guardada: {nombre_archivo}")
            contador += 1

    print(f"\nExtracción finalizada. Total de imágenes extraídas: {contador}")


def calcular_hash_imagen(image_bytes):
    """Calcula un hash único basado en el contenido binario de la imagen."""
    return hashlib.md5(image_bytes).hexdigest()

def buscar_imagen_especifica(pdf_path: str, imagen_referencia_path: str) -> bool:
    """
    Busca si una imagen específica (por archivo de referencia) 
    se encuentra incrustada dentro del PDF.
    """
    # 1. Leer y calcular el hash de la imagen que quieres buscar
    try:
        with open(imagen_referencia_path, "rb") as f:
            bytes_referencia = f.read()
        hash_buscado = calcular_hash_imagen(bytes_referencia)
    except FileNotFoundError:
        print(f"No se encontró la imagen de referencia en: {imagen_referencia_path}")
        return False

    # 2. Abrir el PDF y recorrer sus imágenes
    doc = fitz.open(pdf_path)
    encontrada = False

    for num_pagina, page in enumerate(doc):
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Calcular el hash de la imagen actual del PDF
            hash_actual = calcular_hash_imagen(image_bytes)
            
            # Comparar si coinciden
            if hash_actual == hash_buscado:
                print(f"¡Imagen encontrada! Está en la página {num_pagina + 1} (Índice de imagen: {img_index + 1})")
                encontrada = True
                # Puedes hacer 'break' aquí si solo te interesa saber si al menos existe una vez

    if not encontrada:
        print("La imagen específica NO se encuentra en este PDF.")
        
    return encontrada

# --- EJEMPLO DE USO ---
buscar_imagen_especifica("SURALIS_2.pdf", "Merieux.png")
extraer_imagenes_pdf("SURALIS_2.pdf")