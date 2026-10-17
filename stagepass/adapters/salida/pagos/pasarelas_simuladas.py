from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, Tuple

from stagepass.domain.modelo import MedioPago
from stagepass.domain.valores import (
    EstadoPago,
    ReferenciaPago,
    ResultadoPago,
    SolicitudPago,
)
from stagepass.ports.salida import PasarelaPago


class PasarelaSimulada(PasarelaPago):
    _MEDIO: MedioPago
    _PREFIJO: str
    _INSTRUCCIONES: str

    def __init__(self, auto_aprobar: bool = True) -> None:
        self._auto_aprobar = auto_aprobar
        self._pagos: Dict[str, Tuple[Decimal, EstadoPago]] = {}

    @property
    def medio(self) -> MedioPago:
        return self._MEDIO

    def registrar_pago(self, solicitud: SolicitudPago) -> ReferenciaPago:
        referencia = f"{self._PREFIJO}-{uuid.uuid4().hex[:12].upper()}"
        self._pagos[referencia] = (solicitud.monto, EstadoPago.PENDIENTE)
        return ReferenciaPago(referencia, self._INSTRUCCIONES)

    def verificar_pago(self, referencia: str) -> ResultadoPago:
        monto, estado = self._pagos[referencia]
        if self._auto_aprobar and estado is EstadoPago.PENDIENTE:
            estado = EstadoPago.APROBADO
        return ResultadoPago(referencia, estado, monto)

    def simular_estado(self, referencia: str, estado: EstadoPago) -> None:
        monto, _ = self._pagos[referencia]
        self._pagos[referencia] = (monto, estado)

    def simular_monto(self, referencia: str, monto: Decimal) -> None:
        _, estado = self._pagos[referencia]
        self._pagos[referencia] = (monto, estado)


class PasarelaPayPalMock(PasarelaSimulada):
    _MEDIO = MedioPago.PAYPAL
    _PREFIJO = "PAYPAL"
    _INSTRUCCIONES = "Aprueba el pago en la ventana de PayPal (simulado)"


class PasarelaWompiMock(PasarelaSimulada):
    _MEDIO = MedioPago.WOMPI
    _PREFIJO = "WOMPI"
    _INSTRUCCIONES = "Completa el pago en el checkout de Wompi (simulado)"


class PasarelaPSEMock(PasarelaSimulada):
    _MEDIO = MedioPago.PSE
    _PREFIJO = "PSE"
    _INSTRUCCIONES = "Selecciona tu banco para pagar por PSE (simulado)"
