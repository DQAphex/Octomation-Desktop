import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import StreamingResponse
from thefuzz import process


class ExcelTransformService:
  # Mapeo de columnas esperadas -> nombre destino
  COLUMN_MAPPING = {
      'EMPRESA': 'empresa',
      'TIENDA': 'local_id',
      'NOMBRE ESTABLECIMIENTO': 'local_nombre',
      'REGIÓN': 'local_region',
      'COMUNA': 'local_comuna',
      'DIRECCIÓN LOCAL': 'local_direccion',
      'RPM': 'local_rpm',
      'CONVENIO': 'local_convenio',
      'LABORATORIO': 'laboratorio',
      'FECHA DE MUESTREO': 'fecha_muestreo',
      'PARÁMETROS MONITOREADOS': 'tipo_muestreo',
      'TIPO DE MONITOREO': 'tipo_monitoreo',
      'ACEITES Y GRASAS (MG/L) (LM150)': 'aceites_grasas',
      'PH': 'ph',
      'DBO5 (MG/L) (300)': 'dbo5',
      'FOSFORO (MG/L) (15)': 'fosforo',
      'NITROGENO AMONIACAL (MG/L) (80)': 'nitrogeno_amoniacal',
      'PODER ESPUMÓGENO (MM) (7)': 'poder_espumogeno',
      'S. SEDIMENTABLES (MM/L) (20)': 'solidos_sedimentables',
      'SOLIDOS SUSPENDIDOS TOTALES (MG/L) (300)': 'solidos_suspendidos_totales',
      'VOLUMEN DE DESCARGA DIARIA (M3/D)': 'volumen_de_descarga_diaria',
      'VOLUMEN DE DESCARGA MENSUAL (M3/M)': 'volumen_de_descarga_mensual',
      'ALUMINIO (MG/L)': 'aluminio',
      'ARSÉNICO (MG/L)': 'arsenico',
      'BORO (MG/L)': 'boro',
      'CADMIO (MG/L)': 'cadmio',
      'CIANURO (MG/L)': 'cianuro',
      'ZINC (MG/L)': 'zinc',
      'COBRE (MG/L)': 'cobre',
      'CROMO TOTAL (MG/L)': 'cromo_total',
      'CROMO HEXAVALENTE (MG/L)': 'cromo_hexavalente',
      'HIDROCARBUROS TOTALES (MG/L)': 'hidrocarburos_totales',
      'MANGANESO (MG/L)': 'manganeso',
      'MERCURIO (MG/L)': 'mercurio',
      'NIQUEL (MG/L)': 'niquel',
      'PLOMO (MG/L)': 'plomo',
      'SULFATOS (MG/L)': 'sulfatos',
      'SULFUROS (MG/L)': 'sulfuros',
      'TEMPERATURA (C°)': 'temperatura',
  }

  @classmethod
  async def transform_excel_to_csv_buffer(
      cls, file: UploadFile,
  ) -> io.BytesIO:
    # Validar extensión del archivo
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail='El archivo debe ser un Excel (.xlsx o .xls)',
      )

    # Leer el contenido del UploadFile en memoria
    content = await file.read()
    excel_buffer = io.BytesIO(content)

    try:
      df = pd.read_excel(excel_buffer)
    except Exception as e:
      raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail=f'Error al procesar la planilla Excel: {str(e)}',
      )

    # Mapeo difuso (Fuzzy Matching) para tolerar espacios extra o variaciones en las cabeceras
    matched_columns = {}
    actual_columns = [str(col).strip() for col in df.columns]

    for expected_col, target_name in cls.COLUMN_MAPPING.items():
      # Busca la columna más parecida en el Excel cargado
      match, score = process.extractOne(expected_col, actual_columns)
      if score >= 80:  # Umbral de coincidencia
        matched_columns[match] = target_name

    # Filtrar y renombrar
    df_renamed = df.rename(columns=lambda x: str(x).strip())
    cols_to_keep = [col for col in matched_columns.keys() if col in df_renamed]

    new_df = df_renamed[cols_to_keep].rename(columns=matched_columns)

    # Insertar las columnas faltantes en sus posiciones requeridas
    if 'fecha_emision' not in new_df.columns:
      new_df.insert(
          loc=min(9, len(new_df.columns)), column='fecha_emision', value=None
      )

    if 'dqo' not in new_df.columns:
      new_df.insert(loc=min(16, len(new_df.columns)), column='dqo', value=None)

    # Convertir a CSV en un Stream de texto/bytes
    csv_buffer = io.StringIO()
    new_df.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
    csv_buffer.seek(0)

    # Retornar como BytesIO para ser compatible con StreamingResponse
    return io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig'))

