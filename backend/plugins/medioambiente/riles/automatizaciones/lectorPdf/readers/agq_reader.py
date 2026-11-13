import io
from pathlib import Path
import re
from typing import Union, Dict, Any, List

from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import get_data_list, print_pdf_results, get_pdf_table, open_pdf


def _mapping_parametros(table):
  oil = table[1][3]

  if table[1][0] == "A":
    oil = table[1][4]
  elif table[1][3] == "*":
    oil = table[1][5]
  else:
    print(oil)

  mapping = AnalisisAguaDTO()
  mapping.fecha_emision
  mapping.aceites_grasas = oil
  mapping.dbo = table[2][1]
  mapping.poder_espumogeno = table[3][2]
  mapping.solidos_suspendidos_totales = table[4][3]
  mapping.solidos_sedimentables = table[5][2]
  mapping.nitrogeno_amoniacal = table[7][2]
  mapping.fosforo = table[9][2]
  return mapping.to_dict()


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
      "unimarc",
      "inicio",
      "SUPERMERCADO"
    ]
    formated_line = line.lower()
    formated_line = formated_line.split(":")[1]
    for wti in words_to_ignore:
      formated_line = formated_line.replace(wti.lower(), "")

    return formated_line

  address_lines = get_data_list(file_input, "store_address")
  print(address_lines)
  for al in address_lines:
    match = re.search(r"([A-ZÁÉÍÓÚÑ\s]+N[°º]\s*\d+)", al)
    direccion = al
    if match:
      direccion = match.group(1).strip()
      print(direccion)

    store_data = search_store_id(direccion)
    print("store_data: ", store_data)
    if store_data:
      return store_data


def mapping_send_date(file_input: Union[str, Path, bytes, io.BytesIO]):
  send_date_array = get_data_list(file_input, "date_keywords")
  dates = []
  sampling_counter = 0
  for date_line in range(len(send_date_array)):
    if "emisión" in send_date_array[date_line].lower():
      dates.append(send_date_array[date_line].lower())
    if sampling_counter == 0 and "muestreo:" in send_date_array[date_line].lower():
      dates.append(send_date_array[date_line].lower())
      sampling_counter += 1
  print(dates)
  return dates


def mapping_parametros_desde_texto(line_list: List[str], address):
  mapping = AnalisisAguaDTO()
  text_str = "\n".join(line_list)
  issue_date = ""
  sampling_date = ""
  for line in line_list:
    if "emisión" in line:
      fe = re.findall(r"\d{2}/\d{2}/\d{4}", line)
      issue_date = fe[0]
    if "muestreo" in line:
      fe = re.findall(r"\d{2}/\d{2}/\d{4}", line)
      sampling_date = fe[0]

  def extract_value(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
      return full_parsing(match.group(1))
    return None

  mapping.aceites_grasas = extract_value(
    r"Aceites y Grasas.*?([<]?\s*[\d,\.]+)\s*mg/L", text_str
  )
  mapping.nitrogeno_amoniacal = extract_value(
    r"Nitrógeno Amoniacal.*?([<]?\s*[\d,\.]+)\s*mg/L", text_str
  )
  mapping.dbo = extract_value(r"DBO5.*?([<]?\s*[\d,\.]+)\s*mg/L", text_str)
  mapping.solidos_sedimentables = extract_value(
    r"Sólidos Sedimentables.*?([<]?\s*[\d,\.]+)\s*mL/L", text_str
  )
  mapping.solidos_suspendidos_totales = extract_value(
    r"Sólidos en Suspensión.*?([<]?\s*[\d,\.]+)\s*mg/L", text_str
  )
  mapping.poder_espumogeno = extract_value(
    r"Poder Espumógeno.*?([<]?\s*[\d,\.]+)\s*mm", text_str
  )
  mapping.fosforo = extract_value(
    r"Fósforo Total.*?([<]?\s*[\d,\.]+)\s*mg/L", text_str
  )
  mapping.fecha_emision = issue_date
  mapping.fecha_muestreo = sampling_date
  mapping.laboratorio = "AGQ"
  mapping.local_comuna

  if address:
    for atributo, valor in address.items():
      if hasattr(mapping, atributo):
        setattr(mapping, atributo, valor)

  return mapping.to_dict()


def _extraer_texto_pdfplumber(file_input: Union[str, Path, bytes, io.BytesIO]):
  delimiters = {
    "start": "Parámetros Físico-Químicos",
    "end": "METALES TOTALES",
    "extra-line": 1,
  }
  total_text = []
  capture = False
  remaining_extra_lines = 0

  with open_pdf(file_input) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
      page_text = page.extract_text()

      if page_text:
        lines = page_text.splitlines()

        for line in lines:
          if delimiters["start"] in line:
            capture = True

          if capture:
            total_text.append(line)

          if (
            delimiters["end"] in line
            and capture
            and remaining_extra_lines == 0
          ):
            remaining_extra_lines = delimiters["extra-line"]

          elif remaining_extra_lines > 0:
            total_text.append(line)
            remaining_extra_lines -= 1
            if remaining_extra_lines == 0:
              capture = False

  return total_text


def agq_reader(file_input: Union[str, Path, bytes, io.BytesIO]):
  dates = mapping_send_date(file_input)
  address = get_address(file_input)
  text_list = _extraer_texto_pdfplumber(file_input)
  for i in dates:
    text_list.append(i)
  return mapping_parametros_desde_texto(text_list, address)