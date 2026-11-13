from ..dto.no_desperdicio_alimentos_dto import NoDesperdicioAlimentosBaseDTO


class NoDesperdicioAlimentosService:

    def __init__(self, metadata: NoDesperdicioAlimentosBaseDTO):
        self.metadata = metadata

    @staticmethod
    def get_hola_mundo() -> str:
        return "Hola mundo"

    @staticmethod
    def post_hola_nombre(
        data: NoDesperdicioAlimentosBaseDTO
    ) -> str:
        return f"Hola {data.nombre}"