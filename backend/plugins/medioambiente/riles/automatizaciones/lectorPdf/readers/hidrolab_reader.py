import io
from pathlib import Path
import re

from typing import Union, Dict, Any, Optional

from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import (
    get_data_list,
    print_pdf_results,
    get_pdf_table,
    open_pdf,
)
import unicodedata

# ============================================================
# DEBUG
# ============================================================

DEBUG = True


def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)




def _normalize_text(value: Any) -> str:
  if value is None:
    return ""
  value = str(value).strip().lower()
  value = unicodedata.normalize("NFD", value)
  value = "".join(char for char in value if unicodedata.category(char) != "Mn")
  value = re.sub(r"\s+", " ", value)
  return value


def _parse_values(value: Any) -> str:
  if value is None:
    return ""
  value = str(value).strip()
  if not value:
    return ""
  value = re.sub(r"^\s*[<>]\s*", "", value)
  partes = value.split()
  if not partes:
    return ""
  return partes[0].strip()


def _format_address_line(line: str) -> str:
  words_to_ignore = ["lugar", "direccion", "dirección", "muestreo"]
  formated_line = str(line).lower().strip()
  if "," in formated_line:
    formated_line = formated_line.split(",")[0]
  if "-" in formated_line:
    formated_line = formated_line.split("-")[0]
  for word in words_to_ignore:
    formated_line = formated_line.replace(word.lower(), "")
  formated_line = re.sub(r"\s+", " ", formated_line).strip()
  return formated_line


def get_address(file_input) -> Optional[Dict[str, Any]]:
  address_lines = get_data_list(file_input, "store_address")
  print("#################### address_lines:", address_lines)
  for line in address_lines:
    if not line:
      continue
    texto = str(line).strip()
    texto_normalizado = _normalize_text(texto)
    if "direccion de muestreo:" not in texto_normalizado:
      continue
    print("Línea de dirección de muestreo encontrada:", texto)
    partes = re.split(r"dirección\s+de\s+muestreo\s*:", texto, flags=re.IGNORECASE)
    if len(partes) < 2:
      partes = re.split(r"direccion\s+de\s+muestreo\s*:", texto, flags=re.IGNORECASE)
    direccion = partes[1].strip() if len(partes) > 1 else ""
    if not direccion:
      print("No se pudo extraer la dirección de muestreo.")
      return None
    direccion = re.split(r"\b(proyecto|observaciones?|comuna|punto de muestreo)\s*:", direccion, flags=re.IGNORECASE)[0].strip()
    direccion = re.sub(r"\s+", " ", direccion)
    print("Dirección real del local:", direccion)
    try:
      store_data = search_store_id(direccion.lower())
    except Exception as error:
      print("Error buscando dirección:", error)
      return None
    print("store_data:", store_data)
    if not isinstance(store_data, dict):
      print("Resultado de búsqueda no válido:", store_data)
      return None
    return store_data
  print("No se encontró una línea 'Dirección de muestreo:'.")
  return None


def mapping_sendDate(file_input) -> Dict[str, str]:
  date_array = get_data_list(file_input, "date_keywords")
  fechas = {"emision": "", "muestreo": ""}
  patron = r"\d{2}[-/]\d{2}[-/]\d{4}"
  for actual_date in date_array:
    if not actual_date:
      continue
    texto = str(actual_date)
    texto_normalizado = _normalize_text(texto)
    numeros = re.findall(patron, texto)
    if not numeros:
      continue
    if not fechas["emision"] and "emision" in texto_normalizado:
      fechas["emision"] = numeros[0].replace("-", "/")
    if not fechas["muestreo"] and "termino de muestreo" in texto_normalizado:
      fechas["muestreo"] = numeros[0].replace("-", "/")
    elif not fechas["muestreo"] and "muestreo" in texto_normalizado:
      fechas["muestreo"] = numeros[0].replace("-", "/")
  if not fechas["emision"]:
    for actual_date in date_array:
      if not actual_date:
        continue
      texto = str(actual_date)
      texto_normalizado = _normalize_text(texto)
      numeros = re.findall(patron, texto)
      if numeros and "emision" in texto_normalizado:
        fechas["emision"] = numeros[0].replace("-", "/")
        break
  if not fechas["muestreo"]:
    for actual_date in date_array:
      if not actual_date:
        continue
      texto = str(actual_date)
      texto_normalizado = _normalize_text(texto)
      numeros = re.findall(patron, texto)
      if numeros and "muestreo" in texto_normalizado:
        fechas["muestreo"] = numeros[0].replace("-", "/")
        break
  print("Fechas encontradas:", fechas)
  return fechas


def _find_results_table(pdf) -> Optional[list]:
  for page in pdf.pages:
    try:
      tablas = page.extract_tables()
    except Exception as error:
      print(f"Error extrayendo tablas de página {page.page_number}: {error}")
      continue
    print(f"PÁGINA {page.page_number}: {len(tablas)} tabla(s)")
    for table_index, tabla in enumerate(tablas):
      if not tabla:
        continue
      texto_tabla = " ".join(str(celda) for fila in tabla for celda in fila if celda is not None)
      texto_normalizado = _normalize_text(texto_tabla)
      indicadores = ["aceites y grasas", "nitrógeno amoniacal", "poder espumógeno"]
      encontrados = sum(1 for indicador in indicadores if _normalize_text(indicador) in texto_normalizado)
      if encontrados >= 2:
        print(f"Tabla de resultados encontrada en página {page.page_number}, tabla {table_index}.")
        return tabla
  print("No se encontró la tabla de resultados.")
  return None


def _find_parameter_value(rows: Dict[str, str], aliases: list) -> Optional[str]:
  for alias in aliases:
    alias_normalizado = _normalize_text(alias)
    for parametro, valor in rows.items():
      parametro_normalizado = _normalize_text(parametro)
      if parametro_normalizado == alias_normalizado:
        return valor
  for alias in aliases:
    alias_normalizado = _normalize_text(alias)
    for parametro, valor in rows.items():
      parametro_normalizado = _normalize_text(parametro)
      if alias_normalizado in parametro_normalizado:
        return valor
  return None


def _extract_result_values(tabla: list) -> Dict[str, str]:
  valores = {}
  for fila in tabla:
    if not fila or len(fila) < 2:
      continue
    parametro = fila[0]
    resultado = fila[1]
    if parametro is None or resultado is None:
      continue
    parametro = str(parametro).strip()
    resultado = _parse_values(resultado)
    if not parametro or not resultado:
      continue
    valores[parametro] = resultado
    print(f"Parámetro encontrado: {parametro} -> {resultado}")
  return valores


def _parse_sampling_date(date: Optional[str]) -> str:
  if not date:
    return ""
  partes = str(date).split("/")
  if len(partes) == 1:
    return partes[0]
  return partes[0]


def _read_pdf_file(file_input, address, date) -> Dict[str, Any]:
  with open_pdf(file_input) as pdf:
    mapeo = AnalisisAguaDTO()
    tabla_resultados = _find_results_table(pdf)
    if tabla_resultados is None:
      print("HIDROLAB: no fue posible encontrar la tabla de resultados.")
      return mapeo.to_dict()
    valores = _extract_result_values(tabla_resultados)
    mapeo.aceites_grasas = _find_parameter_value(valores, ["Aceites y grasas"])
    mapeo.dbo5 = _find_parameter_value(valores, ["DBO5", "DBO", "Demanda bioquímica de oxígeno", "Demanda bioquimica de oxigeno"])
    mapeo.fosforo = _find_parameter_value(valores, ["Fósforo", "Fosforo", "Fósforo total", "Fosforo total"])
    mapeo.nitrogeno_amoniacal = _find_parameter_value(valores, ["Nitrógeno amoniacal", "Nitrogeno amoniacal"])
    mapeo.ph = _find_parameter_value(valores, ["pH", "pH unidad de pH"])
    mapeo.poder_espumogeno = _find_parameter_value(valores, ["Poder espumógeno", "Poder espumogeno"])
    mapeo.solidos_sedimentables = _find_parameter_value(valores, ["Sólidos sedimentables", "Solidos sedimentables"])
    mapeo.solidos_suspendidos_totales = _find_parameter_value(valores, ["Sólidos suspendidos totales", "Solidos suspendidos totales", "SST"])
    mapeo.laboratorio = "HIDROLAB"
    mapeo.fecha_emision = date.get("emision", "") if isinstance(date, dict) else ""
    mapeo.fecha_muestreo = _parse_sampling_date(date.get("muestreo", "")) if isinstance(date, dict) else ""
    if isinstance(address, dict):
      for atributo, valor in address.items():
        if hasattr(mapeo, atributo):
          setattr(mapeo, atributo, valor)
    else:
      print("HIDROLAB: address no es un diccionario:", address)
    resultado_final = mapeo.to_dict()
    print("DTO HIDROLAB FINAL:", resultado_final)
    return resultado_final


def hidrolab_reader(file_input):
  direcciones = get_address(file_input)
  fechas = mapping_sendDate(file_input)
  return _read_pdf_file(file_input, direcciones, fechas)