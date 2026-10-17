from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Sequence

from stagepass.domain.modelo import (
    Asiento,
    Boleto,
    Cliente,
    Evento,
    MedioPago,
    Orden,
    Recinto,
)
from stagepass.domain.valores import (
    Factura,
    Mensaje,
    ReferenciaPago,
    RepresentacionBoleto,
    ResultadoPago,
    SolicitudPago,
)


class RepositorioCatalogo(ABC):
    @abstractmethod
    def obtener_evento(self, evento_id: str) -> Optional[Evento]: ...

    @abstractmethod
    def obtener_recinto(self, recinto_id: str) -> Optional[Recinto]: ...

    @abstractmethod
    def listar_asientos_recinto(self, recinto_id: str) -> List[Asiento]: ...


class RepositorioOrdenes(ABC):
    @abstractmethod
    def guardar(self, orden: Orden) -> None: ...

    @abstractmethod
    def obtener(self, orden_id: str) -> Optional[Orden]: ...

    @abstractmethod
    def buscar_ocupantes_evento(self, evento_id: str, ahora: datetime) -> List[Orden]:
        pass

    @abstractmethod
    def buscar_por_cliente_y_evento(self, cliente_id: str, evento_id: str) -> List[Orden]: ...

    @abstractmethod
    def buscar_pendientes_vencidas(self, ahora: datetime) -> List[Orden]: ...


class RepositorioBoletos(ABC):
    @abstractmethod
    def guardar_todos(self, boletos: Sequence[Boleto]) -> None: ...

    @abstractmethod
    def buscar_por_orden(self, orden_id: str) -> List[Boleto]: ...

    @abstractmethod
    def buscar_por_codigo(self, codigo_redencion: str) -> Optional[Boleto]: ...


class PasarelaPago(ABC):
    @property
    @abstractmethod
    def medio(self) -> MedioPago: ...

    @abstractmethod
    def registrar_pago(self, solicitud: SolicitudPago) -> ReferenciaPago:
        pass

    @abstractmethod
    def verificar_pago(self, referencia: str) -> ResultadoPago:
        pass


class NotificadorCliente(ABC):
    @property
    @abstractmethod
    def canal(self) -> str: ...

    @abstractmethod
    def enviar(self, cliente: Cliente, mensaje: Mensaje) -> None: ...


class GeneradorRepresentacionBoleto(ABC):
    @abstractmethod
    def generar(self, boleto: Boleto, evento: Evento) -> RepresentacionBoleto: ...


class EmisorFacturaElectronica(ABC):
    @abstractmethod
    def emitir(self, orden: Orden) -> Factura: ...


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime:
        pass
