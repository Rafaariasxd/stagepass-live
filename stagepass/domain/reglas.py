from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

from stagepass.domain.excepciones import (
    AsientoNoDisponibleError,
    LimiteBoletosExcedidoError,
    SeleccionInvalidaError,
)
from stagepass.domain.modelo import (
    MAX_BOLETOS_POR_EVENTO,
    Asiento,
    EstadoAsiento,
    EstadoOrden,
    Orden,
)


def aplicar_ocupacion(
    asientos: Iterable[Asiento], ordenes_ocupantes: Iterable[Orden], ahora: datetime
) -> List[Asiento]:
    estados: Dict[str, EstadoAsiento] = {}
    for orden in ordenes_ocupantes:
        if not orden.ocupa_asientos(ahora):
            continue
        estado = (
            EstadoAsiento.VENDIDO
            if orden.estado is EstadoOrden.APROBADA
            else EstadoAsiento.BLOQUEADO
        )
        for asiento in orden.asientos:
            if estados.get(asiento.id) is not EstadoAsiento.VENDIDO:
                estados[asiento.id] = estado
    return [
        dataclasses.replace(a, estado=estados.get(a.id, EstadoAsiento.DISPONIBLE))
        for a in asientos
    ]


def seleccionar_asientos(
    asientos_con_estado: Sequence[Asiento], ids_solicitados: Sequence[str]
) -> List[Asiento]:
    if not ids_solicitados:
        raise SeleccionInvalidaError("Debe seleccionar al menos un asiento")
    if len(set(ids_solicitados)) != len(ids_solicitados):
        raise SeleccionInvalidaError("La selección contiene asientos repetidos")
    por_id = {a.id: a for a in asientos_con_estado}
    seleccion: List[Asiento] = []
    for asiento_id in ids_solicitados:
        asiento = por_id.get(asiento_id)
        if asiento is None:
            raise SeleccionInvalidaError(
                f"El asiento '{asiento_id}' no pertenece al recinto del evento"
            )
        if asiento.estado is not EstadoAsiento.DISPONIBLE:
            raise AsientoNoDisponibleError(asiento.codigo_ubicacion)
        seleccion.append(asiento)
    return seleccion


def contar_boletos_acumulados(ordenes_del_cliente: Iterable[Orden], ahora: datetime) -> int:
    return sum(o.cantidad_boletos for o in ordenes_del_cliente if o.ocupa_asientos(ahora))


def validar_limite_boletos(acumulados: int, nuevos: int) -> None:
    if acumulados + nuevos > MAX_BOLETOS_POR_EVENTO:
        raise LimiteBoletosExcedidoError(
            f"Un cliente no puede tener más de {MAX_BOLETOS_POR_EVENTO} boletas por evento "
            f"(ya tiene {acumulados} y quiere {nuevos} más)"
        )
