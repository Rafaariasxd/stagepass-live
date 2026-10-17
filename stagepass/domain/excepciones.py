class DominioError(Exception):
    pass


class DatosInvalidosError(DominioError):
    pass


class EntidadNoEncontradaError(DominioError):
    def __init__(self, entidad: str, identificador: str) -> None:
        super().__init__(f"{entidad} '{identificador}' no existe")
        self.entidad = entidad
        self.identificador = identificador


class EventoNoDisponibleError(DominioError):
    pass


class SeleccionInvalidaError(DominioError):
    pass


class AsientoNoDisponibleError(DominioError):
    def __init__(self, codigo_ubicacion: str) -> None:
        super().__init__(f"El asiento {codigo_ubicacion} no está disponible")
        self.codigo_ubicacion = codigo_ubicacion


class LimiteBoletosExcedidoError(DominioError):
    pass


class OrdenExpiradaError(DominioError):
    pass


class TransicionInvalidaError(DominioError):
    pass


class PagoNoVerificadoError(DominioError):
    pass
