from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from stagepass.domain.modelo import Asiento, Boleto, Cliente, MedioPago, Orden
from stagepass.domain.valores import Factura


@dataclass(frozen=True)
class IniciarCompraCommand:
    cliente: Cliente
    evento_id: str
    asiento_ids: List[str]
    medio_pago: MedioPago


@dataclass(frozen=True)
class ConfirmarPagoCommand:
    orden_id: str


@dataclass(frozen=True)
class ResultadoConfirmacion:
    orden: Orden
    boletos: List[Boleto] = field(default_factory=list)
    factura: Optional[Factura] = None
    advertencias: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DetalleOrden:
    orden: Orden
    boletos: List[Boleto]


@dataclass(frozen=True)
class ResultadoValidacion:
    valido: bool
    motivo: str
    boleto: Optional[Boleto] = None


class ConsultarDisponibilidadUseCase(ABC):
    @abstractmethod
    def ejecutar(self, evento_id: str) -> List[Asiento]: ...


class IniciarCompraUseCase(ABC):
    @abstractmethod
    def ejecutar(self, comando: IniciarCompraCommand) -> Orden: ...


class ConfirmarPagoUseCase(ABC):
    @abstractmethod
    def ejecutar(self, comando: ConfirmarPagoCommand) -> ResultadoConfirmacion: ...


class ExpirarOrdenesUseCase(ABC):
    @abstractmethod
    def ejecutar(self) -> int:
        pass


class ConsultarOrdenUseCase(ABC):
    @abstractmethod
    def ejecutar(self, orden_id: str) -> DetalleOrden: ...


class ValidarBoletoUseCase(ABC):
    @abstractmethod
    def ejecutar(self, codigo_redencion: str) -> ResultadoValidacion: ...
