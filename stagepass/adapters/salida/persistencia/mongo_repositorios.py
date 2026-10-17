from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from stagepass.domain.modelo import (
    Asiento,
    Boleto,
    Cliente,
    EstadoAsiento,
    EstadoOrden,
    MedioPago,
    Orden,
)
from stagepass.ports.salida import RepositorioBoletos, RepositorioOrdenes


def _a_bson(fecha: datetime) -> datetime:
    if fecha.tzinfo is None:
        return fecha
    return fecha.astimezone(timezone.utc).replace(tzinfo=None)


def _desde_bson(fecha: datetime) -> datetime:
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha


def orden_a_documento(orden: Orden) -> Dict[str, Any]:
    return {
        "_id": orden.id,
        "evento_id": orden.evento_id,
        "cliente": {
            "id": orden.cliente.id,
            "nombre_completo": orden.cliente.nombre_completo,
            "correo": orden.cliente.correo,
            "telefono_movil": orden.cliente.telefono_movil,
            "nacionalidad": orden.cliente.nacionalidad,
        },
        "asientos": [
            {
                "id": a.id,
                "recinto_id": a.recinto_id,
                "codigo_ubicacion": a.codigo_ubicacion,
                "precio_base": str(a.precio_base),
                "estado": a.estado.name,
            }
            for a in orden.asientos
        ],
        "medio_pago": orden.medio_pago.name,
        "subtotal": str(orden.subtotal),
        "tarifa_servicio": str(orden.tarifa_servicio),
        "descuento": str(orden.descuento),
        "monto_total": str(orden.monto_total),
        "creada_en": _a_bson(orden.creada_en),
        "expira_en": _a_bson(orden.expira_en),
        "estado": orden.estado.name,
        "referencia_pago": orden.referencia_pago,
    }


def documento_a_orden(doc: Dict[str, Any]) -> Orden:
    c = doc["cliente"]
    return Orden(
        id=doc["_id"],
        cliente=Cliente(
            c["id"], c["nombre_completo"], c["correo"], c["telefono_movil"], c["nacionalidad"]
        ),
        evento_id=doc["evento_id"],
        asientos=[
            Asiento(
                id=a["id"],
                recinto_id=a["recinto_id"],
                codigo_ubicacion=a["codigo_ubicacion"],
                precio_base=Decimal(a["precio_base"]),
                estado=EstadoAsiento[a["estado"]],
            )
            for a in doc["asientos"]
        ],
        medio_pago=MedioPago[doc["medio_pago"]],
        subtotal=Decimal(doc["subtotal"]),
        tarifa_servicio=Decimal(doc["tarifa_servicio"]),
        descuento=Decimal(doc["descuento"]),
        monto_total=Decimal(doc["monto_total"]),
        creada_en=_desde_bson(doc["creada_en"]),
        expira_en=_desde_bson(doc["expira_en"]),
        estado=EstadoOrden[doc["estado"]],
        referencia_pago=doc.get("referencia_pago"),
    )


def boleto_a_documento(boleto: Boleto) -> Dict[str, Any]:
    return {
        "_id": boleto.id,
        "orden_id": boleto.orden_id,
        "evento_id": boleto.evento_id,
        "asiento_codigo": boleto.asiento_codigo,
        "codigo_redencion": boleto.codigo_redencion,
        "firma_hash": boleto.firma_hash,
        "fecha_emision": _a_bson(boleto.fecha_emision),
    }


def documento_a_boleto(doc: Dict[str, Any]) -> Boleto:
    return Boleto(
        id=doc["_id"],
        orden_id=doc["orden_id"],
        evento_id=doc["evento_id"],
        asiento_codigo=doc["asiento_codigo"],
        codigo_redencion=doc["codigo_redencion"],
        firma_hash=doc["firma_hash"],
        fecha_emision=_desde_bson(doc["fecha_emision"]),
    )


class RepositorioOrdenesMongo(RepositorioOrdenes):
    def __init__(self, coleccion: Any) -> None:
        self._col = coleccion

    def guardar(self, orden: Orden) -> None:
        self._col.replace_one({"_id": orden.id}, orden_a_documento(orden), upsert=True)

    def obtener(self, orden_id: str) -> Optional[Orden]:
        doc = self._col.find_one({"_id": orden_id})
        return documento_a_orden(doc) if doc else None

    def buscar_ocupantes_evento(self, evento_id: str, ahora: datetime) -> List[Orden]:
        filtro = {
            "evento_id": evento_id,
            "$or": [
                {"estado": EstadoOrden.APROBADA.name},
                {"estado": EstadoOrden.PENDIENTE_PAGO.name, "expira_en": {"$gt": _a_bson(ahora)}},
            ],
        }
        return [documento_a_orden(d) for d in self._col.find(filtro)]

    def buscar_por_cliente_y_evento(self, cliente_id: str, evento_id: str) -> List[Orden]:
        filtro = {"cliente.id": cliente_id, "evento_id": evento_id}
        return [documento_a_orden(d) for d in self._col.find(filtro)]

    def buscar_pendientes_vencidas(self, ahora: datetime) -> List[Orden]:
        filtro = {
            "estado": EstadoOrden.PENDIENTE_PAGO.name,
            "expira_en": {"$lte": _a_bson(ahora)},
        }
        return [documento_a_orden(d) for d in self._col.find(filtro)]


class RepositorioBoletosMongo(RepositorioBoletos):
    def __init__(self, coleccion: Any) -> None:
        self._col = coleccion

    def guardar_todos(self, boletos: Sequence[Boleto]) -> None:
        for boleto in boletos:
            self._col.replace_one({"_id": boleto.id}, boleto_a_documento(boleto), upsert=True)

    def buscar_por_orden(self, orden_id: str) -> List[Boleto]:
        return [documento_a_boleto(d) for d in self._col.find({"orden_id": orden_id})]

    def buscar_por_codigo(self, codigo_redencion: str) -> Optional[Boleto]:
        doc = self._col.find_one({"codigo_redencion": codigo_redencion})
        return documento_a_boleto(doc) if doc else None


def crear_indices(base_datos: Any) -> None:
    ordenes = base_datos["ordenes"]
    ordenes.create_index([("evento_id", 1), ("estado", 1)])
    ordenes.create_index([("cliente.id", 1), ("evento_id", 1)])
    ordenes.create_index([("estado", 1), ("expira_en", 1)])
    boletos = base_datos["boletos"]
    boletos.create_index("codigo_redencion", unique=True)
    boletos.create_index("orden_id")
