from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class AnalisisAguaDTO:
    empresa: Optional[str] = None
    local_id:Optional[str] = None
    local_nombre:Optional[str] = None
    local_region:Optional[str] = None
    local_comuna:Optional[str] = None
    local_direccion:Optional[str] = None
    local_rpm:Optional[str] = None
    local_convenio:Optional[str] = None
    laboratorio:Optional[str] = None
    fecha_emision: Optional[datetime] = None
    fecha_muestreo: Optional[datetime] = None
    tipo_muestreo: Optional[str] = None
    aceites_grasas: Optional[str] = None
    ph:Optional[str] = None
    dbo5: Optional[str] = None
    dqo: Optional[str] = None
    fosforo: Optional[str] = None
    nitrogeno_amoniacal: Optional[str] = None
    poder_espumogeno: Optional[str] = None
    solidos_sedimentables: Optional[str] = None
    solidos_suspendidos_totales: Optional[str] = None
    volumen_de_descarga_diaria: Optional[str] = None
    volumen_de_descarga_mensual: Optional[str] = None
    aluminio: Optional[str] = None
    arsenico: Optional[str] = None
    boro: Optional[str] = None
    cadmio: Optional[str] = None
    cianuro: Optional[str] = None
    zinc: Optional[str] = None
    cobre: Optional[str] = None
    cromo_total: Optional[str] = None
    cromo_hexavalente: Optional[str] = None
    hidrocarburos_totales: Optional[str] = None
    manganeso: Optional[str] = None
    mercurio: Optional[str] = None
    niquel: Optional[str] = None
    plomo: Optional[str] = None
    sulfatos: Optional[str] = None
    sulfuros: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
        