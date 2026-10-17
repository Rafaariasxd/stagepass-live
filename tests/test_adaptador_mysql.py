from datetime import datetime
from decimal import Decimal

from stagepass.adapters.salida.persistencia.mysql_catalogo import RepositorioCatalogoMySQL
from stagepass.domain.modelo import EstadoEvento, TipoEvento


class CursorFalso:
    def __init__(self, filas, registro):
        self._filas, self._registro = filas, registro

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros):
        self._registro.append((" ".join(sql.split()), tuple(parametros)))

    def fetchall(self):
        return self._filas


class ConexionFalsa:
    def __init__(self, filas, registro):
        self._filas, self._registro, self.cerrada = filas, registro, False

    def cursor(self):
        return CursorFalso(self._filas, self._registro)

    def close(self):
        self.cerrada = True


def repo_con(filas):
    registro, conexiones = [], []

    def fabrica():
        conexiones.append(ConexionFalsa(filas, registro))
        return conexiones[-1]

    return RepositorioCatalogoMySQL(fabrica), registro, conexiones


def test_obtener_evento_mapea_fila_a_dominio():
    fila = {"id": "e1", "nombre": "Rock", "tipo": "CONCIERTO", "recinto_id": "r1",
            "fecha_hora": datetime(2026, 12, 5, 20, 0), "estado": "PROGRAMADO", "clave_secreta": "k"}
    repo, registro, conexiones = repo_con([fila])
    evento = repo.obtener_evento("e1")
    assert evento.tipo is TipoEvento.CONCIERTO and evento.estado is EstadoEvento.PROGRAMADO
    assert evento.clave_secreta == "k"
    assert registro[0][1] == ("e1",)
    assert "%s" in registro[0][0] and "e1" not in registro[0][0]
    assert conexiones[0].cerrada


def test_evento_o_recinto_inexistente_devuelve_none():
    repo, _, _ = repo_con([])
    assert repo.obtener_evento("x") is None
    assert repo.obtener_recinto("x") is None


def test_listar_asientos_convierte_precios_a_decimal():
    filas = [
        {"id": "a1", "recinto_id": "r1", "codigo_ubicacion": "VIP-A1", "precio_base": Decimal("450000.00")},
        {"id": "a2", "recinto_id": "r1", "codigo_ubicacion": "VIP-A2", "precio_base": 450000.5},
    ]
    repo, registro, _ = repo_con(filas)
    asientos = repo.listar_asientos_recinto("r1")
    assert [a.codigo_ubicacion for a in asientos] == ["VIP-A1", "VIP-A2"]
    assert asientos[1].precio_base == Decimal("450000.5")
    assert registro[0][1] == ("r1",)


def test_obtener_recinto():
    repo, _, _ = repo_con([{"id": "r1", "nombre": "Arena", "ciudad": "Bogotá", "aforo": 20}])
    recinto = repo.obtener_recinto("r1")
    assert (recinto.nombre, recinto.aforo) == ("Arena", 20)
