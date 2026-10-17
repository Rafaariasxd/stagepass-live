from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from stagepass.domain.modelo import MedioPago
from stagepass.ports.entrada import ConfirmarPagoCommand


class PayloadInvalidoError(ValueError):
    pass


class TraductorWebhook(ABC):
    medio: MedioPago

    @abstractmethod
    def traducir(self, payload: Dict[str, Any]) -> ConfirmarPagoCommand: ...


def _exigir(valor: Any, descripcion: str) -> str:
    if not valor:
        raise PayloadInvalidoError(f"Payload sin {descripcion}")
    return str(valor)


class TraductorWebhookPayPal(TraductorWebhook):
    medio = MedioPago.PAYPAL

    def traducir(self, payload: Dict[str, Any]) -> ConfirmarPagoCommand:
        orden_id = _exigir((payload.get("resource") or {}).get("custom_id"), "resource.custom_id")
        return ConfirmarPagoCommand(orden_id)


class TraductorWebhookWompi(TraductorWebhook):
    medio = MedioPago.WOMPI

    def traducir(self, payload: Dict[str, Any]) -> ConfirmarPagoCommand:
        transaccion = (payload.get("data") or {}).get("transaction") or {}
        return ConfirmarPagoCommand(_exigir(transaccion.get("reference"), "data.transaction.reference"))


class TraductorWebhookPSE(TraductorWebhook):
    medio = MedioPago.PSE

    def traducir(self, payload: Dict[str, Any]) -> ConfirmarPagoCommand:
        return ConfirmarPagoCommand(_exigir(payload.get("reference"), "reference"))


TRADUCTORES: Dict[str, TraductorWebhook] = {
    "paypal": TraductorWebhookPayPal(),
    "wompi": TraductorWebhookWompi(),
    "pse": TraductorWebhookPSE(),
}
