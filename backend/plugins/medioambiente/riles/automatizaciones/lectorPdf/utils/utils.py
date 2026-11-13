from collections import Counter
import io
import json
from pathlib import Path
import re
import unicodedata
from typing import Union, List, Dict, Any, Optional

import pdfplumber
from lector_pdf_config import LAB_KEYWORDS_FILE, DATA_KEYWORDS_FILE


def open_pdf(file_input: Union[str, Path, bytes, io.BytesIO]):
  """
  Abre un archivo PDF de forma agnóstica soportando:
  - Rutas de texto o Path (str, Path)
  - Bytes planos (bytes)
  - Flujos en memoria (io.BytesIO)
  """
  if isinstance(file_input, bytes):
    return pdfplumber.open(io.BytesIO(file_input))
  elif hasattr(file_input, "read") and hasattr(file_input, "seek"):
    file_input.seek(0)
    return pdfplumber.open(file_input)
  return pdfplumber.open(file_input)


# --- Carga de Configuración JSON ---

def get_lab_table_keyword(lab: str) -> str:
  """Obtiene la palabra clave de tabla asociada a un laboratorio desde el JSON."""
  with open(LAB_KEYWORDS_FILE, "r", encoding="utf-8") as f:
    keywords_data = json.load(f)
    return keywords_data[lab]["tabla"]


def get_data_keywords(data_key: str) -> List[str]:
  """Obtiene la lista de palabras clave para búsqueda de datos desde el JSON."""
  with open(DATA_KEYWORDS_FILE, "r", encoding="utf-8") as f:
    keywords_data = json.load(f)
    return keywords_data.get(data_key, [])


# --- Extracción y Búsqueda de Tablas ---

def get_tables(file_input: Union[str, Path, bytes, io.BytesIO]) -> List[List[List[str]]]:
  """Extrae todas las tablas contenidas en el PDF."""
  total_tables = []
  try:
    with open_pdf(file_input) as pdf:
      for page in pdf.pages:
        tables = page.extract_tables()
        if tables:
          total_tables.extend(tables)
  except Exception as e:
    print(f"Error al extraer tablas del PDF: {e}")
  return total_tables


def _search_tables_internal(
  file_input: Union[str, Path, bytes, io.BytesIO],
  keyword: str,
  find_all: bool = False
) -> Union[Optional[List[List[str]]], List[List[List[str]]]]:
  """
  Función interna unificada para buscar tablas que contengan una palabra clave.
  """
  matched_tables = []
  keyword_lower = keyword.lower()

  try:
    with open_pdf(file_input) as pdf:
      for page_number, page in enumerate(pdf.pages):
        tables = page.extract_tables() or []
        for table_index, table in enumerate(tables):
          if not table:
            continue
          found = False
          for row in table:
            if not row:
              continue
            for cell in row:
              if cell and keyword_lower in str(cell).lower():
                print(
                  f"Found on Page {page_number + 1}, Table #{table_index + 1}!"
                )
                if not find_all:
                  return table
                matched_tables.append(table)
                found = True
                break
            if found:
              break

    if find_all:
      return matched_tables if matched_tables else None

    print(f"The keyword '{keyword}' was not found in any table.")
    return None

  except FileNotFoundError:
    print(f"Error: El archivo '{file_input}' no fue encontrado.")
    return None
  except Exception as e:
    print(f"Error inesperado procesando el PDF: {e}")
    return None


def search_table_by_words(
  file_input: Union[str, Path, bytes, io.BytesIO], keyword: str
):
  """Busca y retorna la primera tabla que contenga la palabra clave."""
  return _search_tables_internal(file_input, keyword, find_all=False)


def search_multiple_tables_by_keyword_lab(
  file_input: Union[str, Path, bytes, io.BytesIO], keyword: str
):
  """Busca y retorna todas las tablas que contengan la palabra clave."""
  return _search_tables_internal(file_input, keyword, find_all=True)


def search_multiple_tables_by_keyword(
  file_input: Union[str, Path, bytes, io.BytesIO],
  lab: Optional[str] = None,
  kw: Optional[str] = None,
):
  """Punto de entrada para buscar múltiples tablas por laboratorio o keyword."""
  print("search_multiple_tables_by_keyword")
  if lab is not None:
    keyword = get_lab_table_keyword(lab)
    return search_multiple_tables_by_keyword_lab(file_input, keyword)
  if kw is not None:
    return search_multiple_tables_by_keyword_lab(file_input, kw)
  return None


def merge_tables(table_array: List[List[List[str]]]) -> List[List[str]]:
  """Combina una lista de tablas en una sola estructura lineal."""
  merged_table = []
  for table in table_array:
    if table:
      merged_table.extend(table)
  return merged_table


def get_pdf_table(file_input: Union[str, Path, bytes, io.BytesIO], lab: str):
  """Obtiene la primera tabla de un PDF usando el identificador del laboratorio."""
  keyword = get_lab_table_keyword(lab)
  return search_table_by_words(file_input, keyword)


# --- Extracción de Texto y Metadatos ---

def get_creation_date(
  file_input: Union[str, Path, bytes, io.BytesIO]
) -> Optional[str]:
  """Obtiene la fecha de creación desde los metadatos del PDF."""
  try:
    with open_pdf(file_input) as pdf:
      metadata = pdf.metadata or {}
      return metadata.get("CreationDate")
  except Exception as e:
    print(f"Error al obtener fecha de creación: {e}")
    return None


def extract_text_in_lines(
  file_input: Union[str, Path, bytes, io.BytesIO]
) -> List[str]:
  """Extrae todo el texto del PDF organizado en una lista de líneas."""
  total_lines = []
  try:
    with open_pdf(file_input) as pdf:
      for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
          total_lines.extend(page_text.splitlines())
  except Exception as e:
    print(f"Error al extraer texto en líneas: {e}")
  return total_lines


def extract_lines_by_text(
  file_input: Union[str, Path, bytes, io.BytesIO], substring: str
) -> List[str]:
  """Busca y retorna las líneas del PDF que contienen la subcadena especificada."""
  matching_lines = []
  sub_lower = substring.lower()
  lines = extract_text_in_lines(file_input)

  for line in lines:
    if sub_lower in line.lower():
      matching_lines.append(line)

  return matching_lines


def get_data_list(
  file_input: Union[str, Path, bytes, io.BytesIO], search_key: str
) -> List[str]:
  """Retorna las líneas que coinciden con las keywords de 'search_key'."""
  text = extract_text_in_lines(file_input)
  data_keywords = get_data_keywords(search_key)

  data_lines = [
    line
    for line in text
    if any(kw.lower() in line.lower() for kw in data_keywords)
  ]
  return data_lines


# --- Análisis de Texto y Salidas ---

def word_analysis(text_list: List[str], top_n: int = 10) -> List[tuple]:
  """Analiza la frecuencia de palabras ignorando tildes y números."""
  full_text = " ".join(text_list)

  normalized_text = unicodedata.normalize("NFKD", full_text)
  text_without_accents = "".join(
    c for c in normalized_text if unicodedata.category(c) != "Mn"
  )

  text_cleaned = re.sub(r"\d+", "", text_without_accents).lower()
  words = re.findall(r"\w+", text_cleaned)

  counter = Counter(words)
  most_common = counter.most_common(top_n)

  for word, count in most_common:
    print(f"{word}: {count}")

  return most_common


def print_pdf_results(results: Dict[str, Any]) -> None:
  """Imprime un diccionario de resultados formateado en consola."""
  if not results:
    print("No se encontraron resultados.")
    return
  for parameter, value in results.items():
    print(f"{parameter}: {value}")