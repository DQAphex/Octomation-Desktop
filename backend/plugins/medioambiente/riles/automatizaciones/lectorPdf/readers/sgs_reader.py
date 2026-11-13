import io
from pathlib import Path
import re
from typing import Union, Dict, Any, Optional

from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import get_data_list, print_pdf_results, get_pdf_table


def mapping_sendDate(file_input: Union[str, Path, bytes, io.BytesIO]):
  dateArray = get_data_list(file_input, "date_keywords")
  patron = r"\d{2}-\d{2}-\d{4}"
  patron2 = r"\d{2}/\d{2}/\d{4}"
  fechas = {
    "emision": "",
    "muestreo": ""
  }
  muestreoCounter = 0
  emisionCounter = 0

  for date in dateArray:
    actualDate: str = date
    actualDate = actualDate.lower().split("fecha", 1)[1] if len(actualDate.lower().split("fecha", 1)) > 1 else actualDate
    if muestreoCounter == 0 and actualDate.lower().find("compuesta") > 0:
      actualDate = actualDate.split("hasta", 1)[1] if len(actualDate.split("hasta", 1)) > 1 else actualDate
      numeros = re.findall(patron, actualDate)
      if not numeros:
        numeros = re.findall(patron2, actualDate)
      fechaFinal = "/".join(numeros)
      fechas["muestreo"] = fechaFinal
      muestreoCounter += 1

  return fechas


def get_address(file_input: Union[str, Path, bytes, io.BytesIO]):
  def ignore_words(line):
    words_to_ignore = [
      "lugar",
      "direccion",
      "dirección",
      "muestreo",
      ":",
      "-",
      ",",
      "Unimarc",
      "inicio"
    ]
    formated_line = line.lower()
    formated_line = formated_line.split("fecha")[0]
    for wti in words_to_ignore:
      formated_line = formated_line.replace(wti.lower(), "")

    return formated_line

  address_lines = get_data_list(file_input, "store_address")
  print(address_lines)
  for al in address_lines:
    al_formated = ignore_words(al)
    print(al_formated)
    store_data = search_store_id(al_formated)
    print("store_data: ", store_data)
    if store_data:
      return store_data


def _mapping_parametros(tabla, address, dates):
  mapeo_etiquetas = {
    'Aceites y Grasas': 'aceites_grasas',
    'DBO5 a 20°C': 'dbo',
    'Fósforo': 'fosforo',
    'Nitrógeno Amoniacal': 'nitrogeno_amoniacal',
    'Poder Espumógeno': 'poder_espumogeno',
    'Sólidos Sedimentables': 'solidos_sedimentables',
    'Sólidos Suspendidos Totales': 'solidos_suspendidos_totales',
    'Aluminio': 'aluminio',
    'Arsénico': 'arsenico',
    'Boro': 'boro',
    'Cadmio': 'cadmio',
    'Cianuro Total': 'cianuro',
    'Cinc': 'zinc',
    'Cobre': 'cobre',
    'Cromo Hexavalente': 'cromo_hexavalente',
    'Cromo Total': 'cromo_total',
    'Hidrocarburos Totales': 'hidrocarburos_totales',
    'Manganeso': 'manganeso',
    'Mercurio': 'mercurio',
    'Níquel': 'niquel',
    'pH 25°C Laboratorio': 'ph',
    'Plomo': 'plomo',
    'Sulfato': 'sulfatos',
    'Sulfuro Total': 'sulfuros',
  }

  mapeo = AnalisisAguaDTO()
  valores_encontrados = {}

  if tabla:
    for fila in tabla:
      etiqueta = fila[0]
      if etiqueta in mapeo_etiquetas:
        valores_encontrados[mapeo_etiquetas[etiqueta]] = fila[3]

  for atributo, valor in valores_encontrados.items():
    setattr(mapeo, atributo, full_parsing(valor))

  if address:
    for atributo, valor in address.items():
      if hasattr(mapeo, atributo):
        setattr(mapeo, atributo, valor)

  mapeo.laboratorio = "SGS"
  mapeo.fecha_muestreo = dates["muestreo"] if dates else ""
  return mapeo.to_dict()


def sgs_reader(file_input: Union[str, Path, bytes, io.BytesIO], lab: str):
  table = get_pdf_table(file_input, lab)
  address = get_address(file_input)
  dates = mapping_sendDate(file_input)
  print(dates)
  results = _mapping_parametros(table, address, dates)
  print_pdf_results(results)
  return results  