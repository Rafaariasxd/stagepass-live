from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Sequence

from stagepass.domain.excepciones import SeleccionInvalidaError
from stagepass.domain.modelo import Asiento

_CENTAVOS = Decimal("0.01")


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class TramoTarifa:
    minimo: int
    maximo: Optional[int]
    porcentaje_tarifa: Decimal
    porcentaje_descuento: Decimal

    def aplica_a(self, cantidad: int) -> bool:
        return cantidad >= self.minimo and (self.maximo is None or cantidad <= self.maximo)


@dataclass(frozen=True)
class Liquidacion:
    subtotal: Decimal
    tarifa_servicio: Decimal
    descuento: Decimal
    monto_total: Decimal
    porcentaje_tarifa: Decimal
    porcentaje_descuento: Decimal


TRAMOS_POR_DEFECTO = (
    TramoTarifa(1, 2, Decimal("0.10"), Decimal("0.00")),
    TramoTarifa(3, 5, Decimal("0.08"), Decimal("0.05")),
    TramoTarifa(6, None, Decimal("0.05"), Decimal("0.10")),
)


class CalculadoraTarifas:
    def __init__(self, tramos: Sequence[TramoTarifa] = TRAMOS_POR_DEFECTO) -> None:
        self._tramos = tuple(tramos)

    def calcular(self, asientos: Sequence[Asiento]) -> Liquidacion:
        cantidad = len(asientos)
        if cantidad < 1:
            raise SeleccionInvalidaError("Debe seleccionar al menos un asiento")
        tramo = next(t for t in self._tramos if t.aplica_a(cantidad))
        subtotal = _redondear(sum((a.precio_base for a in asientos), Decimal("0")))
        tarifa = _redondear(subtotal * tramo.porcentaje_tarifa)
        descuento = _redondear(subtotal * tramo.porcentaje_descuento)
        return Liquidacion(
            subtotal=subtotal,
            tarifa_servicio=tarifa,
            descuento=descuento,
            monto_total=subtotal - descuento + tarifa,
            porcentaje_tarifa=tramo.porcentaje_tarifa,
            porcentaje_descuento=tramo.porcentaje_descuento,
        )
