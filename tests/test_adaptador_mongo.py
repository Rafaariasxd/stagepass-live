from datetime import datetime, timedelta, timezone
from decimal import Decimal

import mongomock
import pytest

from stagepass.adapters.salida.persistencia.memoria import RepositorioCatalogoMemoria
from stagepass.adapters.salida.persistencia.mongo_repositorios import (
    RepositorioBoletosMongo,
    RepositorioOrdenesMongo,
    crear_indices,
)
from stagepass.bootstrap import construir_contenedor
from stagepass.domain.modelo import Asiento, Boleto, Cliente, EstadoOrden, MedioPago, Orden
from stagepass.ports.entrada import ConfirmarPagoCommand
from tests.conftest import VIP, comando

AHORA = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
CLIENTE = Cliente("c1", "Ana Pérez", "ana@correo.co", "+573001112233", "Colombiana")


@pytest.fixture
def base():
    bd = mongomock.MongoClient()["stagepass_test"]
    crear_indices(bd)
    return bd


def nueva_orden(evento="evt", ahora=AHORA, cliente=CLIENTE, n=2):
    asientos = [Asiento(f"a{i}", "rec", f"VIP-A{i}", Decimal("100000.00")) for i in range(1, n + 1)]
    return Orden.crear(cliente, evento, asientos, MedioPago.PSE,
                       Decimal("200000.00"), Decimal("20000.00"), Decimal("0.00"),
                       Decimal("220000.00"), ahora)


def test_guardar_y_recuperar_orden_conserva_todos_los_datos(base):
    repo = RepositorioOrdenesMongo(base["ordenes"])
    orden = nueva_orden()
    orden.registrar_referencia_pago("PSE-123")
    repo.guardar(orden)

    leida = repo.obtener(orden.id)
    assert leida == orden
    assert leida.expira_en.tzinfo is not None
    assert isinstance(leida.monto_total, Decimal)


def test_guardar_dos_veces_actualiza_en_vez_de_duplicar(base):
    repo = RepositorioOrdenesMongo(base["ordenes"])
    orden = nueva_orden()
    repo.guardar(orden)
    orden.aprobar(AHORA)
    repo.guardar(orden)
    assert base["ordenes"].count_documents({}) == 1
    assert repo.obtener(orden.id).estado is EstadoOrden.APROBADA


def test_consultas_por_ocupacion_cliente_y_vencimiento(base):
    repo = RepositorioOrdenesMongo(base["ordenes"])
    vigente = nueva_orden()
    aprobada = nueva_orden(); aprobada.aprobar(AHORA)
    vencida = nueva_orden(ahora=AHORA - timedelta(hours=1))
    otro_evento = nueva_orden(evento="otro")
    otra_persona = nueva_orden(cliente=Cliente("c2", "Luis", "l@correo.co", "+57300", "Colombiano"))
    rechazada = nueva_orden(); rechazada.rechazar()
    for o in (vigente, aprobada, vencida, otro_evento, otra_persona, rechazada):
        repo.guardar(o)

    ocupantes = {o.id for o in repo.buscar_ocupantes_evento("evt", AHORA)}
    assert ocupantes == {vigente.id, aprobada.id, otra_persona.id}
    assert {o.id for o in repo.buscar_pendientes_vencidas(AHORA)} == {vencida.id}
    del_cliente = {o.id for o in repo.buscar_por_cliente_y_evento("c1", "evt")}
    assert del_cliente == {vigente.id, aprobada.id, vencida.id, rechazada.id}
    assert repo.obtener("no-existe") is None


def test_boletos_se_guardan_y_se_buscan_por_orden_y_codigo(base):
    repo = RepositorioBoletosMongo(base["boletos"])
    orden = nueva_orden(); orden.aprobar(AHORA)
    boletos = [Boleto.emitir(orden, a, "clave", AHORA) for a in orden.asientos]
    repo.guardar_todos(boletos)

    assert {b.id for b in repo.buscar_por_orden(orden.id)} == {b.id for b in boletos}
    assert repo.buscar_por_codigo(boletos[0].codigo_redencion) == boletos[0]
    assert repo.buscar_por_codigo("INEXISTENTE") is None


def test_codigo_de_redencion_es_unico(base):
    from pymongo.errors import DuplicateKeyError

    repo = RepositorioBoletosMongo(base["boletos"])
    orden = nueva_orden(n=1); orden.aprobar(AHORA)
    boleto = Boleto.emitir(orden, orden.asientos[0], "clave", AHORA)
    repo.guardar_todos([boleto])
    clon = Boleto(**{**boleto.__dict__, "id": "otro-id"})
    with pytest.raises(DuplicateKeyError):
        repo.guardar_todos([clon])


def test_flujo_completo_con_ordenes_y_boletas_en_mongo(base, reloj):
    contenedor = construir_contenedor(
        reloj=reloj,
        catalogo=RepositorioCatalogoMemoria(),
        ordenes=RepositorioOrdenesMongo(base["ordenes"]),
        boletos=RepositorioBoletosMongo(base["boletos"]),
    )
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:3]))
    assert base["ordenes"].count_documents({"estado": "PENDIENTE_PAGO"}) == 1

    resultado = contenedor.confirmar_pago.ejecutar(ConfirmarPagoCommand(orden.id))
    assert resultado.orden.estado is EstadoOrden.APROBADA
    assert base["boletos"].count_documents({}) == 3
    assert all(contenedor.validar_boleto.ejecutar(b.codigo_redencion).valido for b in resultado.boletos)
