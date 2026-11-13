import io
from pathlib import Path
from typing import Union, Dict, Any

from utils.dtos import AnalisisAguaDTO
from utils.data_cleaning import full_parsing, remove_symbol
from utils.models import search_store_id
from utils.utils import (
  get_data_list,
  print_pdf_results,
  get_pdf_table,
  search_table_by_words
)

mapeo = AnalisisAguaDTO()


def _mapping_parametros(tabla):
  mapeo.aceites_grasas = full_parsing(tabla[1][2])
  mapeo.dbo = full_parsing(tabla[2][2])
  mapeo.dqo = full_parsing(tabla[3][2])
  mapeo.fosforo = full_parsing(tabla[4][2])
  mapeo.nitrogeno_amoniacal = full_parsing(tabla[5][2])
  mapeo.poder_espumogeno = full_parsing(tabla[6][2])
  # mapeo.solidos_sedimentables = full_parsing(tabla[7][2])
  mapeo.solidos_suspendidos_totales = full_parsing(tabla[7][2])
  mapeo.laboratorio = "BIODIVERSA"
  return mapeo.to_dict()


def biodiversa_reader(
  file_input: Union[str, Path, bytes, io.BytesIO], lab: str
) -> Dict[str, Any]:
  table = get_pdf_table(file_input, lab)
  if table:
    _mapping_parametros(table)

  table2 = search_table_by_words(file_input, "Sedimentables")
  if table2 and len(table2) > 1:
    mapeo.solidos_sedimentables = full_parsing(table2[1][2])

  return mapeo.to_dict()