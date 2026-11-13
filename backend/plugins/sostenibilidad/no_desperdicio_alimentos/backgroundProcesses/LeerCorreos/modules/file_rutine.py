import fitz
import io
import re
import pdfplumber

class File_Runtime():

  def __init__(self,pdf_bytes: bytes):
    self.pdf_bytes=pdf_bytes
    self.tables = []
    self.folio = None
    self.folios_gd = None
    self.fecha_emision = None
    self.nombre_razon_social = None
    self.rut_razon_social = None
    self.excel_export = []
  def obtener_tablas(self):
    with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
      for pagina in pdf.pages:
        self.tables = pagina.extract_tables()
        return self.tables
        
  def buscar_tablas(self, palabra_clave):

    for tabla in self.tables:
      for fila in tabla:
        for celda in fila:
          if celda == palabra_clave:
            return tabla  

  def obtener_folios_gd(self) -> list[str]:
    tabla = self.buscar_tablas("FOLIO") #fila = ['TIPO GUÍA DESPACHO', 'FOLIO', 'FECHA DE EMISIÓN', 'FECHA DE RECEPCIÓN']
    folios = tabla[2][1]
    self.folios_gd = folios.split("\n")
    return folios.split("\n")
  
  def obtener_folio_certificado(self) -> list[str]:
    tabla = self.buscar_tablas("Nº FOLIO:") #fila = ['TIPO GUÍA DESPACHO', 'FOLIO', 'FECHA DE EMISIÓN', 'FECHA DE RECEPCIÓN']
    folio = tabla[0][2].split(" ")[1]
    self.folio = folio
    return folio
  
  def obtener_fecha_emision(self) -> list[str]:
    tabla = self.buscar_tablas("Nº FOLIO:") #fila 3 = ['SANTIAGO', '07-09-2026', None]]
    fecha_emision = tabla[2][1]
    self.fecha_emision = fecha_emision
    return fecha_emision
  
  def obtener_razon_social(self) -> list[str]:
    tabla = self.buscar_tablas("INFORMACIÓN DE INSTITUCIÓN QUE ENTREGA PRODUCTOS")
    fila_datos = tabla[1][1] #fila = ['NOMBRE O RAZÓN SOCIAL', 'RENDIC HERMANOS S.A.\n81537600-5\nCERRO EL PLOMO 5680, LAS CONDES\nJORGE SAEZ CORREA\n10034176-K']
    lista_datos_importantes = fila_datos.split("\n")
    nombre_razon_social = lista_datos_importantes[0]
    rut_razon_social = lista_datos_importantes[1]
    self.nombre_razon_social = nombre_razon_social
    self.rut_razon_social = rut_razon_social
    return [self.nombre_razon_social,self.rut_razon_social]

  def generar_tabla_excel(self):
    print(self.folios_gd)
    for folio_gd in self.folios_gd:
      self.excel_export.append([self.folio,folio_gd,self.rut_razon_social,self.nombre_razon_social,self.fecha_emision])
    return self.excel_export
  
  def orchestrator_extract_data(self):

    self.obtener_tablas()
    self.obtener_folio_certificado()
    self.obtener_fecha_emision()
    self.obtener_razon_social()
    self.obtener_folios_gd()
    self.generar_tabla_excel()

    return 