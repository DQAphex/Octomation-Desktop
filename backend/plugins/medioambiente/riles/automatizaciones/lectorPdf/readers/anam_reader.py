import io
from pathlib import Path
import re
from typing import Union, Dict, Any

from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import get_data_list, print_pdf_results, get_pdf_table, open_pdf


def _get_fecha_analisis(col):
  fecha_fin = col.split("\n")[1].split(" ")[1]
  return fecha_fin


def _get_nombre_param(col):
  nombre = col.split("\n")
  return nombre


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
      "inicio",
      "#"
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


def _read_pdf_file(file_input: Union[str, Path, bytes, io.BytesIO]):
  dates = mapping_sendDate(file_input)
  address = get_address(file_input)
  mapeo = AnalisisAguaDTO()

  with open_pdf(file_input) as pdf:
    registros = []
    for page in pdf.pages:
      tablas = page.extract_tables()
      for tabla in tablas:
        for fila in tabla:
          if fila not in [tabla[0], tabla[1]]:
            registros.append([_get_fecha_analisis(fila[1]), remove_symbol(fila[3])])

  mapeo.fecha_muestreo = dates["muestreo"]
  mapeo.fecha_emision = dates["emision"]
  mapeo.aceites_grasas = registros[0][1]
  mapeo.dbo = registros[1][1]
  mapeo.dqo = registros[2][1]
  mapeo.fosforo = registros[3][1]
  mapeo.nitrogeno_amoniacal = registros[4][1]
  mapeo.poder_espumogeno = registros[5][1]
  mapeo.solidos_sedimentables = registros[6][1]
  mapeo.solidos_suspendidos_totales = registros[7][1]
  mapeo.laboratorio = "ANAM"

  if address:
    for atributo, valor in address.items():
      if hasattr(mapeo, atributo):
        setattr(mapeo, atributo, valor)

  return mapeo.to_dict()


def anam_reader(file_input: Union[str, Path, bytes, io.BytesIO]):
  results = _read_pdf_file(file_input)
  return results