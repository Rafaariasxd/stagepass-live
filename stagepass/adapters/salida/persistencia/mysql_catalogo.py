from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Sequence

from stagepass.domain.modelo import (
    Asiento,
    EstadoEvento,
    Evento,
    Recinto,
    TipoEvento,
)
from stagepass.ports.salida import RepositorioCatalogo

FabricaConexion = Callable[[], Any]


def crear_fabrica_conexion(
    host: str, puerto: int, usuario: str, clave: str, base_datos: str
) -> FabricaConexion:
    import pymysql
    import pymysql.cursors

    def fabrica() -> Any:
        return pymysql.connect(
            host=host,
            port=puerto,
            user=usuario,
            password=clave,
            database=base_datos,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

    return fabrica


class RepositorioCatalogoMySQL(RepositorioCatalogo):
    def __init__(self, fabrica_conexion: FabricaConexion) -> None:
        self._fabrica = fabrica_conexion

    def obtener_evento(self, evento_id: str) -> Optional[Evento]:
        filas = self._consultar(
            "SELECT id, nombre, tipo, recinto_id, fecha_hora, estado, clave_secreta "
            "FROM eventos WHERE id = %s",
            (evento_id,),
        )
        return _fila_a_evento(filas[0]) if filas else None

    def obtener_recinto(self, recinto_id: str) -> Optional[Recinto]:
        filas = self._consultar(
            "SELECT id, nombre, ciudad, aforo FROM recintos WHERE id = %s", (recinto_id,)
        )
        return _fila_a_recinto(filas[0]) if filas else None

    def listar_asientos_recinto(self, recinto_id: str) -> List[Asiento]:
        filas = self._consultar(
            "SELECT id, recinto_id, codigo_ubicacion, precio_base "
            "FROM asientos WHERE recinto_id = %s ORDER BY codigo_ubicacion",
            (recinto_id,),
        )
        return [_fila_a_asiento(f) for f in filas]

    def _consultar(self, sql: str, parametros: Sequence[Any]) -> List[Dict[str, Any]]:
        conexion = self._fabrica()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(sql, parametros)
                return list(cursor.fetchall())
        finally:
            conexion.close()


def _fila_a_evento(fila: Dict[str, Any]) -> Evento:
    return Evento(
        id=fila["id"],
        nombre=fila["nombre"],
        tipo=TipoEvento[fila["tipo"]],
        recinto_id=fila["recinto_id"],
        fecha_hora=fila["fecha_hora"],
        estado=EstadoEvento[fila["estado"]],
        clave_secreta=fila["clave_secreta"],
    )


def _fila_a_recinto(fila: Dict[str, Any]) -> Recinto:
    return Recinto(fila["id"], fila["nombre"], fila["ciudad"], int(fila["aforo"]))


def _fila_a_asiento(fila: Dict[str, Any]) -> Asiento:
    return Asiento(
        id=fila["id"],
        recinto_id=fila["recinto_id"],
        codigo_ubicacion=fila["codigo_ubicacion"],
        precio_base=Decimal(str(fila["precio_base"])),
    )
