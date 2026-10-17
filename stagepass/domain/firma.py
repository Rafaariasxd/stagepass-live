from __future__ import annotations

import hashlib
import hmac
import secrets
from decimal import Decimal


def generar_codigo_redencion() -> str:
    return secrets.token_hex(6).upper()


def calcular_firma(
    clave_evento: str,
    orden_id: str,
    cliente_id: str,
    evento_id: str,
    asiento_codigo: str,
    monto_total: Decimal,
    codigo_redencion: str,
) -> str:
    mensaje = "|".join(
        [orden_id, cliente_id, evento_id, asiento_codigo, f"{monto_total:.2f}", codigo_redencion]
    ).encode("utf-8")
    return hmac.new(clave_evento.encode("utf-8"), mensaje, hashlib.sha256).hexdigest()


def firmas_coinciden(firma_a: str, firma_b: str) -> bool:
    return hmac.compare_digest(firma_a, firma_b)
