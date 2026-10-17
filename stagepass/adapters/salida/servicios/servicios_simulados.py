from __future__ import annotations

import hashlib
import itertools
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

from stagepass.domain.modelo import Boleto, Evento, Orden
from stagepass.domain.valores import Factura, RepresentacionBoleto
from stagepass.ports.salida import (
    EmisorFacturaElectronica,
    GeneradorRepresentacionBoleto,
    Reloj,
)


class GeneradorBoletoSVGMock(GeneradorRepresentacionBoleto):
    def generar(self, boleto: Boleto, evento: Evento) -> RepresentacionBoleto:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="360" height="160">'
            '<rect width="360" height="160" fill="white" stroke="black"/>'
            f'<text x="12" y="30">{escape(evento.nombre)}</text>'
            f'<text x="12" y="60">Asiento: {escape(boleto.asiento_codigo)}</text>'
            f'<text x="12" y="90">Código: {boleto.codigo_redencion}</text>'
            f'<text x="12" y="120" font-size="9">Firma: {boleto.firma_hash[:32]}</text>'
            "</svg>"
        )
        return RepresentacionBoleto(boleto.id, svg.encode("utf-8"), "image/svg+xml")


class EmisorFacturaDIANMock(EmisorFacturaElectronica):
    def __init__(self) -> None:
        self._consecutivo = itertools.count(1)

    def emitir(self, orden: Orden) -> Factura:
        numero = f"SETP-{next(self._consecutivo):08d}"
        cufe = hashlib.sha384(f"{numero}|{orden.id}|{orden.monto_total}".encode()).hexdigest()
        return Factura(numero=numero, cufe=cufe, orden_id=orden.id)


class RelojSistema(Reloj):
    def ahora(self) -> datetime:
        return datetime.now(timezone.utc)


class RelojFijo(Reloj):
    def __init__(self, inicio: datetime) -> None:
        self._actual = inicio

    def ahora(self) -> datetime:
        return self._actual

    def avanzar(self, **delta: float) -> None:
        self._actual += timedelta(**delta)
