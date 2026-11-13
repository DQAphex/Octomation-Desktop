# Lector Aguas Patagonia
import io
from pathlib import Path
import re
from typing import Union, Dict, Any, List, Optional

from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import (
  get_data_list,
  print_pdf_results,
  get_pdf_table,
  merge_tables,
  search_multiple_tables_by_keyword
)


def get_adress(file_input: Union[str, Path, bytes, io.BytesIO]):
  def ignore_words(line):
    words_to_ignore = ["lugar", "direccion", "dirección", "muestreo"]
    formated_line = line.lower()
    if formated_line.find(",") >= 0:
      formated_line = formated_line.split(",")[0]
    if formated_line.find("-") >= 0:
      formated_line = formated_line.split("-")[0]

    for wti in words_to_ignore:
      formated_line = formated_line.replace(wti.lower(), "")

    return formated_line

  address_lines = get_data_list(file_input, "store_address")
  addresses = []
  for al in address_lines:
    al_formated = ignore_words(al)
    store_data = search_store_id(al_formated)
    if store_data:
      addresses.append(store_data)
  print(addresses)
  return addresses


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
    if emisionCounter == 0 and actualDate.lower().find("emisión") > 0:
      numeros = re.findall(patron, actualDate)
      if not numeros:
        numeros = re.findall(patron2, actualDate)
      fechaFinal = "/".join(numeros)
      fechas["emision"] = fechaFinal
      emisionCounter += 1

    if muestreoCounter == 0 and actualDate.lower().find("muestreo") > 0:
      numeros = re.findall(patron, actualDate)
      if not numeros:
        numeros = re.findall(patron2, actualDate)
      fechaFinal = "/".join(numeros)
      fechas["muestreo"] = fechaFinal
      muestreoCounter += 1

  return fechas


def _mappingParametros(tabla, date=None, address=None):
  mapeo = AnalisisAguaDTO()
  mapeo.fecha_emision = date["emision"] if date else ""
  mapeo.fecha_muestreo = date["muestreo"] if date else ""
  mapeo.aceites_grasas = full_parsing(tabla[3][2])
  mapeo.dbo = full_parsing(tabla[11][2])
  # mapeo.dqo = full_parsing(tabla[3][2])
  mapeo.fosforo = full_parsing(tabla[21][2])
  mapeo.nitrogeno_amoniacal = full_parsing(tabla[15][2])
  mapeo.poder_espumogeno = full_parsing(tabla[17][2])
  mapeo.solidos_sedimentables = full_parsing(tabla[23][2])
  mapeo.solidos_suspendidos_totales = full_parsing(tabla[24][2])
  mapeo.laboratorio = "AGUASPATAGONIA"
  return mapeo.to_dict()


def ap_reader(file_input: Union[str, Path, bytes, io.BytesIO]):
  print("USANDO AP READER")
  tables = search_multiple_tables_by_keyword(file_input, lab="aguas_patagonia")
  finalTable = merge_tables(tables) if tables else []
  get_adress(file_input)
  fechas = mapping_sendDate(file_input)
  print(fechas)
  return _mappingParametros(finalTable, date=fechas)