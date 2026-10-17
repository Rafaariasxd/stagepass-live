from __future__ import annotations

import copy
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from stagepass.adapters.salida.persistencia import datos_semilla
from stagepass.domain.modelo import Asiento, Boleto, Evento, EstadoOrden, Orden, Recinto
from stagepass.ports.salida import RepositorioBoletos, RepositorioCatalogo, RepositorioOrdenes


class RepositorioCatalogoMemoria(RepositorioCatalogo):
    def __init__(self) -> None:
        self._eventos = {e.id: e for e in datos_semilla.eventos()}
        self._recintos = {r.id: r for r in datos_semilla.recintos()}
        self._asientos = datos_semilla.asientos()

    def obtener_evento(self, evento_id: str) -> Optional[Evento]:
        return copy.deepcopy(self._eventos.get(evento_id))

    def obtener_recinto(self, recinto_id: str) -> Optional[Recinto]:
        return self._recintos.get(recinto_id)

    def listar_asientos_recinto(self, recinto_id: str) -> List[Asiento]:
        return [copy.deepcopy(a) for a in self._asientos if a.recinto_id == recinto_id]


class RepositorioOrdenesMemoria(RepositorioOrdenes):
    def __init__(self) -> None:
        self._ordenes: Dict[str, Orden] = {}

    def guardar(self, orden: Orden) -> None:
        self._ordenes[orden.id] = copy.deepcopy(orden)

    def obtener(self, orden_id: str) -> Optional[Orden]:
        return copy.deepcopy(self._ordenes.get(orden_id))

    def buscar_ocupantes_evento(self, evento_id: str, ahora: datetime) -> List[Orden]:
        return [
            copy.deepcopy(o)
            for o in self._ordenes.values()
            if o.evento_id == evento_id
            and (
                o.estado is EstadoOrden.APROBADA
                or (o.estado is EstadoOrden.PENDIENTE_PAGO and o.expira_en > ahora)
            )
        ]

    def buscar_por_cliente_y_evento(self, cliente_id: str, evento_id: str) -> List[Orden]:
        return [
            copy.deepcopy(o)
            for o in self._ordenes.values()
            if o.cliente.id == cliente_id and o.evento_id == evento_id
        ]

    def buscar_pendientes_vencidas(self, ahora: datetime) -> List[Orden]:
        return [
            copy.deepcopy(o)
            for o in self._ordenes.values()
            if o.estado is EstadoOrden.PENDIENTE_PAGO and o.expira_en <= ahora
        ]


class RepositorioBoletosMemoria(RepositorioBoletos):
    def __init__(self) -> None:
        self._boletos: Dict[str, Boleto] = {}

    def guardar_todos(self, boletos: Sequence[Boleto]) -> None:
        for boleto in boletos:
            self._boletos[boleto.id] = boleto

    def buscar_por_orden(self, orden_id: str) -> List[Boleto]:
        return [b for b in self._boletos.values() if b.orden_id == orden_id]

    def buscar_por_codigo(self, codigo_redencion: str) -> Optional[Boleto]:
        return next(
            (b for b in self._boletos.values() if b.codigo_redencion == codigo_redencion), None
        )
