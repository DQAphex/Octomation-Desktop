import cv2
import numpy as np
import fitz  # PyMuPDF

def encontrar_tabla_en_pdf(pdf_path, template_path, umbral=0.8):
    # 1. Cargar la imagen de la plantilla (la captura de la tabla)
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    t_h, t_w = template.shape[:2]
    
    # 2. Abrir el PDF
    doc = fitz.open(pdf_path)
    
    for numero_pagina in range(len(doc)):
        pagina = doc[numero_pagina]
        
        # Renderizar la página del PDF a imagen (resolución de 150 DPI para buen balance calidad/velocidad)
        pix = pagina.get_pixmap(dpi=150)
        imagen_bytes = pix.tobytes("png")
        
        # Convertir bytes a imagen de OpenCV (escala de grises)
        img_np = np.frombuffer(imagen_bytes, np.uint8)
        img_pagina = cv2.imdecode(img_np, cv2.IMREAD_GRAYSCALE)
        
        # 3. Aplicar Template Matching
        resultado = cv2.matchTemplate(img_pagina, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(resultado)
        
        # 4. Evaluar si la coincidencia supera el umbral definido
        if max_val >= umbral:
            top_left = max_loc
            bottom_right = (top_left[0] + t_w, top_left[1] + t_h)
            
            print(f"¡Tabla encontrada!")
            print(f"Página: {numero_pagina + 1}")
            print(f"Coordenadas (píxeles): Esquina superior izq {top_left}, Esquina inferior der {bottom_right}")
            print(f"Nivel de coincidencia: {max_val * 100:.2f}%")
            
            return {
                "pagina": numero_pagina + 1,
                "coordenadas": (top_left, bottom_right)
            }
            
    print("No se encontró una coincidencia exacta con la plantilla.")
    return None


resultado = encontrar_tabla_en_pdf("ScanBiodiversa.pdf", "tabla.png")