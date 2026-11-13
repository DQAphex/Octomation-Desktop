from datetime import datetime, timezone
from typing import Annotated
from pydantic import (
  BaseModel,
  ConfigDict,
  EmailStr,
  Field,
  StringConstraints,
  ValidationError,
)

restrictions = {
  "espacios": "[NO USAR ESPACIOS]",
  "version": "[0.00.000]"
}

# Tipo reutilizable para cadenas estrictas sin espacios en blanco
NoSpacesStr = Annotated[
  str,
  StringConstraints(
    pattern=r"^\S+$",
    strip_whitespace=True,
  ),
]


class PluginBaseDTO(BaseModel):
  model_config = ConfigDict(
    extra="forbid",
    populate_by_name=True,
    json_schema_extra={
      "example": {
        "plugin_name": "GeneradorDePlugins",
        "plugin_category": "General",
        "version": "0.0.1",
        "created_at": "2026-09-08T10:30:00Z",
        "author": "Diego Quioza",
        "email": "dquioza@smu.cl",
      }
    },
  )

  plugin_name: NoSpacesStr = Field(
    ...,
    min_length=5,
    max_length=50,
    description=f"{restrictions['espacios']} Nombre del plugin, nombre de carpeta con la que se guardará el proyecto",
    examples=["GeneradorDePlugins"],
  )

  plugin_category: NoSpacesStr | None = Field(
    default=None,
    description="Categoría del plugin (opcional, sin espacios si se especifica)",
    examples=["Medioambiente"],
  )

  version: str = Field(
    ...,
    pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$",
    description=f"{restrictions['espacios']}{restrictions['version']} Versión del plugin en formato MAJOR.MINOR.PATCH",
    examples=["0.0.1"],
  )

  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    description="Fecha y hora de creación del plugin en formato ISO 8601",
  )

  author: str = Field(
    ...,
    min_length=2,
    max_length=100,
    description="Nombre completo del autor",
    examples=["Diego Quioza"],
  )

  email: EmailStr = Field(
    ...,
    description="Correo electrónico válido del autor",
    examples=["dquioza@smu.cl"],
  )