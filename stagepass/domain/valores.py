from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Tuple

from stagepass.domain.modelo import Cliente


class EstadoPago(Enum):
    PENDIENTE = "Pendiente"
    APROBADO = "Aprobado"
    RECHAZADO = "Rechazado"


@dataclass(frozen=True)
class SolicitudPago:
    orden_id: str
    monto: Decimal
    moneda: str
    cliente: Cliente
    descripcion: str


@dataclass(frozen=True)
class ReferenciaPago:
    referencia: str
    instrucciones: str


@dataclass(frozen=True)
class ResultadoPago:
    referencia: str
    estado: EstadoPago
    monto: Decimal


@dataclass(frozen=True)
class Factura:
    numero: str
    cufe: str
    orden_id: str


@dataclass(frozen=True)
class RepresentacionBoleto:
    boleto_id: str
    contenido: bytes
    tipo_mime: str


@dataclass(frozen=True)
class Mensaje:
    asunto: str
    cuerpo: str
    adjuntos: Tuple[RepresentacionBoleto, ...] = field(default_factory=tuple)
