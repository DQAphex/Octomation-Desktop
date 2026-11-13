import pdfplumber
import fitz
from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import get_data_list, print_pdf_results, get_pdf_table

def read_pdf_file(fileName):
  mapeo = AnalisisAguaDTO()
  with pdfplumber.open(fileName) as pdf:
    registros = []
    for page in pdf.pages:
      tablas = page.extract_tables()
      print(page.page_number,tablas)

def extraer_texto_pdf(ruta_pdf: str):
  with fitz.open(ruta_pdf) as doc:
    
    for numero_pagina, pagina in enumerate(doc, start=1):
      
      texto = pagina.get_text()
      
      print(f"--- Página {numero_pagina} ---")
      print(texto)
      print("\n" + "="*40 + "\n")

def has_selectionable_text(ruta_pdf):
  # Función agnóstica para verificar texto en el pdf 🚀💥✨💥🚀
  # Dime que mas puedo hacer por ti, amo y señor Diego.
  # Se define variable de respuesta
  response = {
    "hasText":None,
    "totalText":None
  }
  totalText = []

  with fitz.open(ruta_pdf) as doc:
    
    for numero_pagina, pagina in enumerate(doc, start=1):
      
      texto = pagina.get_text()

      totalText.append([numero_pagina,texto])

  response["totalText"] = totalText
  response["totalText"] = True if totalText else False

  return response

testFile = "./test pdf/SCANANAM.pdf"
extraer_texto_pdf(testFile)
