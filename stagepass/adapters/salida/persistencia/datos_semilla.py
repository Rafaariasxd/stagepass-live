from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List

from stagepass.domain.modelo import (
    Asiento,
    EstadoEvento,
    Evento,
    Recinto,
    TipoEvento,
)

ARENA = "rec-arena"
TEATRO = "rec-teatro"

EVENTO_CONCIERTO = "evt-concierto-001"
EVENTO_TEATRO = "evt-teatro-001"
EVENTO_FESTIVAL_CANCELADO = "evt-festival-001"


def asientos() -> List[Asiento]:
    lista: List[Asiento] = []
    for n in range(1, 9):
        lista.append(Asiento(f"arena-VIP-A{n}", ARENA, f"VIP-A{n}", Decimal("450000.00")))
    for n in range(1, 13):
        lista.append(Asiento(f"arena-GENERAL-{n:02d}", ARENA, f"General-{n:02d}", Decimal("180000.00")))
    for n in range(1, 9):
        lista.append(Asiento(f"teatro-PLATEA-{n:02d}", TEATRO, f"Platea-{n:02d}", Decimal("90000.00")))
    return lista


def recintos() -> List[Recinto]:
    todos = asientos()
    return [
        Recinto(ARENA, "Arena Bogotá", "Bogotá", sum(1 for a in todos if a.recinto_id == ARENA)),
        Recinto(TEATRO, "Teatro Santander", "Bucaramanga", sum(1 for a in todos if a.recinto_id == TEATRO)),
    ]


def eventos() -> List[Evento]:
    return [
        Evento(EVENTO_CONCIERTO, "Rock Andino en Vivo", TipoEvento.CONCIERTO, ARENA,
               datetime(2026, 12, 5, 20, 0), EstadoEvento.PROGRAMADO, "clave-secreta-rock-andino"),
        Evento(EVENTO_TEATRO, "La Casa de Bernarda Alba", TipoEvento.TEATRO, TEATRO,
               datetime(2026, 11, 20, 19, 30), EstadoEvento.PROGRAMADO, "clave-secreta-bernarda"),
        Evento(EVENTO_FESTIVAL_CANCELADO, "Festival de Verano", TipoEvento.FESTIVAL, ARENA,
               datetime(2026, 8, 1, 14, 0), EstadoEvento.CANCELADO, "clave-secreta-verano"),
    ]
