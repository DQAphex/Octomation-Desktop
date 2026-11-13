# Automatización de Monitoreo de Riles

## Resumen Ejecutivo			

Susan recibe resultados de monitoreos a los diferentes locales de:

- Unimarc 
- Alvi
- Super 10
- OK Market

Estos resultados se reciben en formato PDF, los cuales se componen de la carta y el informe correspondiente al monitoreo. El informe siendo la sección mas importante se compone por dos tablas, una con los datos del local y otra con los datos de los desechos químicos que genera el local. 

Se defininen reglas para las cantidades de cada químico y según su medición se generan avisos que indican a Susan que debe comunicarse con los locales y establecer una serie de acciones para rectificar la situación y conseguir métricas aceptables en base a límites definidos para cada parámetro.

Sumado a esto tambien se busca generar la siguiente serie de entregables:

1. Reportes semanales
  - Generar tabla de recuento de monitoreos mensuales por sanitaria, local, etc.
  - Generar detalle de locales que no tuvieron buenos resultados en las métricas.
  - Planificación de RPM Semanal.

2. Correo de aviso a local
  - Generar un reporte en HTML que muestre el histórico de resultados para cáda métrica.
  - Mostrar si es un monitoreo [Simple/Sencillo].
  - Mostrar Gráficos.
  - Generar detalle en excel para que lo reciba la sanitaria.

RN-01: Cada parámetro químico debe compararse contra el límite vigente definido por la empresa.
RN-02: Si un parámetro supera el límite permitido, el monitoreo queda marcado como "No Conforme".
RN-03: Si existe al menos un parámetro fuera de norma, debe generarse una alerta.
RN-04: Los resultados deben almacenarse históricamente.
RN-05: Los reportes deben considerar toda la información histórica disponible.
RN-06: Cada monitoreo debe clasificarse como:

Simple
Completo

según información del informe.
RN-07: Un local puede tener múltiples monitoreos durante el año.

V-01: Verificar que el PDF sea legible.
V-02: Verificar existencia de fecha de monitoreo.
V-03: Verificar existencia del nombre del local.
V-04: Verificar existencia de resultados analíticos.
V-05: Validar formato numérico de los resultados.
V-06: Validar que el parámetro exista en el catálogo maestro.
V-07: Evitar carga duplicada de monitoreos.

ME-01: Si el PDF no puede ser leído, registrar error y mover el archivo a carpeta de excepciones.
ME-02: Si falta información crítica, registrar incidencia.
ME-03: Si un parámetro no existe en el catálogo, registrar advertencia.
ME-04: Si falla el envío de correo, registrar error y reintentar.
ME-05: Si falla la generación del reporte, registrar log detallado.

Lectura PDF |Datos extraídos correctamente. |
Validación de Límites| Clasificación correcta Conforme/No Conforme. |
Detección de Alertas | Generación automática de alerta. |
Generación Excel| Archivo generado sin errores. |
Generación HTML | Visualización correcta de tablas y gráficos.|
Envío Outlook | Correo recibido correctamente. |
Dashboard Power BI | Información visible y consistente. |
Carga Masiva | Procesamiento exitoso de todos los documentos. |

## Beneficios Esperados:
  La automatización del proceso de monitoreo de RILES permitirá reducir significativamente el trabajo manual asociado a la revisión de informes, análisis de resultados y generación de reportes, mejorando la oportunidad y calidad de la gestión sobre los locales monitoreados.
### Beneficios Cuantitativos.
  Reducción estimada de un 70% a 90% del tiempo dedicado al procesamiento manual de informes.
  Disminución de errores de digitación y análisis derivados de la manipulación manual de datos.
  Procesamiento masivo de monitoreos en minutos en lugar de horas.
  Generación automática de reportes semanales y mensuales.
  Reducción del tiempo de respuesta frente a incumplimientos detectados.
### Beneficios Cualitativos.
  Mayor trazabilidad de los monitoreos históricos.
  Estandarización del análisis de resultados entre todas las cadenas (Unimarc, Alvi, Super 10 y OK Market).
  Detección temprana de desviaciones e incumplimientos normativos.
  Disponibilidad de información consolidada para la toma de decisiones.
  Mejora en la comunicación con locales y sanitarias mediante reportes automáticos.
  Visualización centralizada de indicadores y tendencias mediante Power BI.
  Mayor capacidad de seguimiento preventivo sobre locales con reincidencias o comportamientos críticos.

