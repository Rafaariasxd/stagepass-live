from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from stagepass.domain import firma
from stagepass.domain.excepciones import (
    AsientoNoDisponibleError,
    DatosInvalidosError,
    OrdenExpiradaError,
    PagoNoVerificadoError,
    TransicionInvalidaError,
)

TIEMPO_BLOQUEO = timedelta(minutes=10)
MAX_BOLETOS_POR_EVENTO = 6


class TipoEvento(Enum):
    CONCIERTO = "Concierto"
    TEATRO = "Teatro"
    FESTIVAL = "Festival"


class EstadoEvento(Enum):
    PROGRAMADO = "Programado"
    AGOTADO = "Agotado"
    CANCELADO = "Cancelado"


class EstadoAsiento(Enum):
    DISPONIBLE = "Disponible"
    BLOQUEADO = "Bloqueado"
    VENDIDO = "Vendido"


class EstadoOrden(Enum):
    PENDIENTE_PAGO = "Pendiente de Pago"
    APROBADA = "Aprobada"
    RECHAZADA = "Rechazada"
    EXPIRADA = "Expirada"


class MedioPago(Enum):
    PAYPAL = "PayPal"
    WOMPI = "Wompi"
    PSE = "PSE"


@dataclass(frozen=True)
class Recinto:
    id: str
    nombre: str
    ciudad: str
    aforo: int


@dataclass
class Evento:
    id: str
    nombre: str
    tipo: TipoEvento
    recinto_id: str
    fecha_hora: datetime
    estado: EstadoEvento
    clave_secreta: str

    def admite_ventas(self) -> bool:
        return self.estado is EstadoEvento.PROGRAMADO


@dataclass
class Asiento:
    id: str
    recinto_id: str
    codigo_ubicacion: str
    precio_base: Decimal
    estado: EstadoAsiento = EstadoAsiento.DISPONIBLE

    def bloquear(self) -> None:
        if self.estado is not EstadoAsiento.DISPONIBLE:
            raise AsientoNoDisponibleError(self.codigo_ubicacion)
        self.estado = EstadoAsiento.BLOQUEADO

    def vender(self) -> None:
        if self.estado is not EstadoAsiento.BLOQUEADO:
            raise TransicionInvalidaError(
                f"Solo un asiento bloqueado puede venderse ({self.codigo_ubicacion})"
            )
        self.estado = EstadoAsiento.VENDIDO

    def liberar(self) -> None:
        if self.estado is EstadoAsiento.VENDIDO:
            raise TransicionInvalidaError(
                f"Un asiento vendido no puede liberarse ({self.codigo_ubicacion})"
            )
        self.estado = EstadoAsiento.DISPONIBLE


@dataclass(frozen=True)
class Cliente:
    id: str
    nombre_completo: str
    correo: str
    telefono_movil: str
    nacionalidad: str

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.nombre_completo.strip():
            raise DatosInvalidosError("El cliente requiere identificador y nombre")
        if "@" not in self.correo:
            raise DatosInvalidosError("Correo electrónico inválido")


@dataclass
class Orden:
    id: str
    cliente: Cliente
    evento_id: str
    asientos: List[Asiento]
    medio_pago: MedioPago
    subtotal: Decimal
    tarifa_servicio: Decimal
    descuento: Decimal
    monto_total: Decimal
    creada_en: datetime
    expira_en: datetime
    estado: EstadoOrden = EstadoOrden.PENDIENTE_PAGO
    referencia_pago: Optional[str] = None

    @classmethod
    def crear(
        cls,
        cliente: Cliente,
        evento_id: str,
        asientos: List[Asiento],
        medio_pago: MedioPago,
        subtotal: Decimal,
        tarifa_servicio: Decimal,
        descuento: Decimal,
        monto_total: Decimal,
        ahora: datetime,
        orden_id: Optional[str] = None,
    ) -> "Orden":
        copias = [dataclasses.replace(a) for a in asientos]
        for asiento in copias:
            asiento.bloquear()
        return cls(
            id=orden_id or str(uuid.uuid4()),
            cliente=cliente,
            evento_id=evento_id,
            asientos=copias,
            medio_pago=medio_pago,
            subtotal=subtotal,
            tarifa_servicio=tarifa_servicio,
            descuento=descuento,
            monto_total=monto_total,
            creada_en=ahora,
            expira_en=ahora + TIEMPO_BLOQUEO,
        )

    @property
    def cantidad_boletos(self) -> int:
        return len(self.asientos)

    def esta_vigente(self, ahora: datetime) -> bool:
        return self.estado is EstadoOrden.PENDIENTE_PAGO and ahora < self.expira_en

    def ocupa_asientos(self, ahora: datetime) -> bool:
        return self.estado is EstadoOrden.APROBADA or self.esta_vigente(ahora)

    def registrar_referencia_pago(self, referencia: str) -> None:
        self.referencia_pago = referencia

    def aprobar(self, ahora: datetime) -> None:
        self._exigir_pendiente()
        if ahora >= self.expira_en:
            raise OrdenExpiradaError(
                f"La orden {self.id} venció el {self.expira_en.isoformat()}"
            )
        for asiento in self.asientos:
            asiento.vender()
        self.estado = EstadoOrden.APROBADA

    def rechazar(self) -> None:
        self._exigir_pendiente()
        self._liberar_asientos()
        self.estado = EstadoOrden.RECHAZADA

    def expirar(self) -> None:
        self._exigir_pendiente()
        self._liberar_asientos()
        self.estado = EstadoOrden.EXPIRADA

    def _liberar_asientos(self) -> None:
        for asiento in self.asientos:
            asiento.liberar()

    def _exigir_pendiente(self) -> None:
        if self.estado is not EstadoOrden.PENDIENTE_PAGO:
            raise TransicionInvalidaError(
                f"La orden {self.id} está '{self.estado.value}' y ya no admite cambios"
            )


@dataclass(frozen=True)
class Boleto:
    id: str
    orden_id: str
    evento_id: str
    asiento_codigo: str
    codigo_redencion: str
    firma_hash: str
    fecha_emision: datetime

    @classmethod
    def emitir(
        cls,
        orden: Orden,
        asiento: Asiento,
        clave_evento: str,
        ahora: datetime,
    ) -> "Boleto":
        if orden.estado is not EstadoOrden.APROBADA:
            raise PagoNoVerificadoError(
                "Una boleta solo puede generarse si el pago fue exitoso y verificado"
            )
        codigo = firma.generar_codigo_redencion()
        hash_seguridad = firma.calcular_firma(
            clave_evento,
            orden.id,
            orden.cliente.id,
            orden.evento_id,
            asiento.codigo_ubicacion,
            orden.monto_total,
            codigo,
        )
        return cls(
            id=str(uuid.uuid4()),
            orden_id=orden.id,
            evento_id=orden.evento_id,
            asiento_codigo=asiento.codigo_ubicacion,
            codigo_redencion=codigo,
            firma_hash=hash_seguridad,
            fecha_emision=ahora,
        )

    def firma_es_valida(self, orden: Orden, clave_evento: str) -> bool:
        esperada = firma.calcular_firma(
            clave_evento,
            orden.id,
            orden.cliente.id,
            orden.evento_id,
            self.asiento_codigo,
            orden.monto_total,
            self.codigo_redencion,
        )
        return firma.firmas_coinciden(esperada, self.firma_hash)
