import pytest
from fastapi.testclient import TestClient

from stagepass.adapters.entrada.http.app import crear_app
from stagepass.adapters.salida.persistencia import datos_semilla as semilla
from stagepass.bootstrap import construir_contenedor

CLIENTE = {
    "id": "cli-1", "nombre_completo": "Ana Pérez", "correo": "ana@correo.co",
    "telefono_movil": "+573001112233", "nacionalidad": "Colombiana",
}


@pytest.fixture
def api(reloj):
    contenedor = construir_contenedor(modo="memoria", reloj=reloj)
    with TestClient(crear_app(contenedor, intervalo_expiracion_s=3600)) as cliente:
        yield cliente, contenedor, reloj


def comprar(cliente, asientos, medio="WOMPI", datos=CLIENTE):
    return cliente.post("/compras", json={
        "cliente": datos, "evento_id": semilla.EVENTO_CONCIERTO,
        "asiento_ids": asientos, "medio_pago": medio,
    })


def test_flujo_completo_compra_webhook_y_validacion(api):
    cliente, _, _ = api
    asientos = cliente.get(f"/eventos/{semilla.EVENTO_CONCIERTO}/asientos").json()
    assert len(asientos) == 20 and {a["estado"] for a in asientos} == {"Disponible"}

    respuesta = comprar(cliente, ["arena-VIP-A1", "arena-VIP-A2", "arena-VIP-A3"])
    assert respuesta.status_code == 201
    orden = respuesta.json()
    assert orden["estado"] == "Pendiente de Pago" and orden["monto_total"] == "1390500.00"

    bloqueados = [a for a in cliente.get(f"/eventos/{semilla.EVENTO_CONCIERTO}/asientos").json()
                  if a["estado"] == "Bloqueado"]
    assert len(bloqueados) == 3

    webhook = cliente.post("/webhooks/pagos/wompi", json={
        "event": "transaction.updated",
        "data": {"transaction": {"reference": orden["id"], "status": "APPROVED"}},
    })
    assert webhook.status_code == 200
    assert webhook.json()["estado"] == "Aprobada" and webhook.json()["boletos_emitidos"] == 3

    detalle = cliente.get(f"/ordenes/{orden['id']}").json()
    assert len(detalle["boletos"]) == 3
    codigo = detalle["boletos"][0]["codigo_redencion"]
    assert cliente.get(f"/boletos/{codigo}/validar").json()["valido"] is True
    assert cliente.get("/boletos/XXXX/validar").json()["valido"] is False


@pytest.mark.parametrize("proveedor, medio, payload", [
    ("paypal", "PAYPAL", lambda oid: {"event_type": "PAYMENT.CAPTURE.COMPLETED", "resource": {"custom_id": oid}}),
    ("pse", "PSE", lambda oid: {"transactionState": "OK", "reference": oid}),
])
def test_webhooks_de_paypal_y_pse(api, proveedor, medio, payload):
    cliente, _, _ = api
    orden = comprar(cliente, ["arena-GENERAL-01"], medio=medio).json()
    r = cliente.post(f"/webhooks/pagos/{proveedor}", json=payload(orden["id"]))
    assert r.status_code == 200 and r.json()["boletos_emitidos"] == 1


def test_errores_de_dominio_se_traducen_a_codigos_http(api):
    cliente, _, reloj = api
    assert comprar(cliente, ["arena-VIP-A1"]).status_code == 201
    assert comprar(cliente, ["arena-VIP-A1"], datos={**CLIENTE, "id": "cli-2"}).status_code == 409
    assert comprar(cliente, [f"arena-GENERAL-{n:02d}" for n in range(1, 8)]).status_code == 422
    assert comprar(cliente, ["nope"], datos={**CLIENTE, "id": "cli-3"}).status_code == 422
    assert cliente.get("/eventos/nada/asientos").status_code == 404
    assert cliente.get("/ordenes/nada").status_code == 404
    assert cliente.post("/webhooks/pagos/desconocida", json={}).status_code == 404
    assert cliente.post("/webhooks/pagos/pse", json={}).status_code == 400


def test_pago_tardio_por_webhook_devuelve_conflicto(api):
    cliente, _, reloj = api
    orden = comprar(cliente, ["arena-VIP-A5"], medio="PSE").json()
    reloj.avanzar(minutes=10, seconds=1)
    r = cliente.post("/webhooks/pagos/pse", json={"reference": orden["id"]})
    assert r.status_code == 409
    assert cliente.get(f"/ordenes/{orden['id']}").json()["estado"] == "Expirada"
