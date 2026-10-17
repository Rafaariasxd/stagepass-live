from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from stagepass.domain.excepciones import (
    AsientoNoDisponibleError,
    LimiteBoletosExcedidoError,
    OrdenExpiradaError,
    PagoNoVerificadoError,
    SeleccionInvalidaError,
    TransicionInvalidaError,
)
from stagepass.domain.modelo import (
    Asiento,
    Boleto,
    Cliente,
    EstadoAsiento,
    EstadoOrden,
    MedioPago,
    Orden,
)
from stagepass.domain.reglas import (
    aplicar_ocupacion,
    contar_boletos_acumulados,
    seleccionar_asientos,
    validar_limite_boletos,
)
from stagepass.domain.tarifas import CalculadoraTarifas

AHORA = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
CLIENTE = Cliente("c1", "Ana Pérez", "ana@correo.co", "+573001112233", "Colombiana")


def asientos(n, precio="100000"):
    return [Asiento(f"a{i}", "rec", f"VIP-A{i}", Decimal(precio)) for i in range(1, n + 1)]


def orden_de(n=2, ahora=AHORA):
    return Orden.crear(CLIENTE, "evt", asientos(n), MedioPago.PSE,
                       Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), ahora)


@pytest.mark.parametrize(
    "cantidad, tarifa, descuento, total",
    [
        (1, "10000.00", "0.00", "110000.00"),
        (2, "20000.00", "0.00", "220000.00"),
        (3, "24000.00", "15000.00", "309000.00"),
        (5, "40000.00", "25000.00", "515000.00"),
        (6, "30000.00", "60000.00", "570000.00"),
    ],
)
def test_tarifa_y_descuento_por_volumen(cantidad, tarifa, descuento, total):
    liquidacion = CalculadoraTarifas().calcular(asientos(cantidad))
    assert liquidacion.tarifa_servicio == Decimal(tarifa)
    assert liquidacion.descuento == Decimal(descuento)
    assert liquidacion.monto_total == Decimal(total)


def test_calculo_sin_asientos_falla():
    with pytest.raises(SeleccionInvalidaError):
        CalculadoraTarifas().calcular([])


def test_orden_bloquea_diez_minutos_y_no_altera_el_original():
    originales = asientos(2)
    orden = Orden.crear(CLIENTE, "evt", originales, MedioPago.PSE,
                        Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), AHORA)
    assert orden.expira_en == AHORA + timedelta(minutes=10)
    assert all(a.estado is EstadoAsiento.BLOQUEADO for a in orden.asientos)
    assert all(a.estado is EstadoAsiento.DISPONIBLE for a in originales)


def test_no_se_puede_bloquear_un_asiento_ya_bloqueado():
    a = asientos(1)[0]
    a.bloquear()
    with pytest.raises(AsientoNoDisponibleError):
        a.bloquear()


def test_aprobar_dentro_del_plazo_vende_los_asientos():
    orden = orden_de()
    orden.aprobar(AHORA + timedelta(minutes=9, seconds=59))
    assert orden.estado is EstadoOrden.APROBADA
    assert all(a.estado is EstadoAsiento.VENDIDO for a in orden.asientos)


def test_aprobar_despues_de_diez_minutos_falla():
    orden = orden_de()
    with pytest.raises(OrdenExpiradaError):
        orden.aprobar(AHORA + timedelta(minutes=10))


def test_expirar_libera_asientos_y_es_terminal():
    orden = orden_de()
    orden.expirar()
    assert orden.estado is EstadoOrden.EXPIRADA
    assert all(a.estado is EstadoAsiento.DISPONIBLE for a in orden.asientos)
    with pytest.raises(TransicionInvalidaError):
        orden.aprobar(AHORA)


def test_ocupacion_distingue_bloqueado_vendido_y_vencido():
    catalogo = asientos(4)
    vigente = Orden.crear(CLIENTE, "evt", [catalogo[0]], MedioPago.PSE,
                          Decimal(0), Decimal(0), Decimal(0), Decimal(0), AHORA)
    vendida = Orden.crear(CLIENTE, "evt", [catalogo[1]], MedioPago.PSE,
                          Decimal(0), Decimal(0), Decimal(0), Decimal(0), AHORA)
    vendida.aprobar(AHORA)
    vencida = Orden.crear(CLIENTE, "evt", [catalogo[2]], MedioPago.PSE,
                          Decimal(0), Decimal(0), Decimal(0), Decimal(0), AHORA - timedelta(minutes=30))
    estados = {a.id: a.estado for a in aplicar_ocupacion(catalogo, [vigente, vendida, vencida], AHORA)}
    assert estados == {
        "a1": EstadoAsiento.BLOQUEADO,
        "a2": EstadoAsiento.VENDIDO,
        "a3": EstadoAsiento.DISPONIBLE,
        "a4": EstadoAsiento.DISPONIBLE,
    }


def test_seleccion_rechaza_repetidos_desconocidos_y_ocupados():
    catalogo = asientos(2)
    with pytest.raises(SeleccionInvalidaError):
        seleccionar_asientos(catalogo, ["a1", "a1"])
    with pytest.raises(SeleccionInvalidaError):
        seleccionar_asientos(catalogo, ["zzz"])
    catalogo[0].estado = EstadoAsiento.BLOQUEADO
    with pytest.raises(AsientoNoDisponibleError):
        seleccionar_asientos(catalogo, ["a1"])


def test_limite_de_seis_boletas_acumuladas():
    previas = [orden_de(4)]
    acumuladas = contar_boletos_acumulados(previas, AHORA)
    assert acumuladas == 4
    validar_limite_boletos(acumuladas, 2)
    with pytest.raises(LimiteBoletosExcedidoError):
        validar_limite_boletos(acumuladas, 3)


def test_ordenes_vencidas_no_cuentan_para_el_limite():
    vencida = orden_de(4, ahora=AHORA - timedelta(hours=1))
    assert contar_boletos_acumulados([vencida], AHORA) == 0


def test_boleto_exige_pago_aprobado():
    orden = orden_de(1)
    with pytest.raises(PagoNoVerificadoError):
        Boleto.emitir(orden, orden.asientos[0], "clave", AHORA)


def test_firma_del_boleto_depende_de_la_clave_y_de_los_datos():
    orden = orden_de(1)
    orden.aprobar(AHORA)
    boleto = Boleto.emitir(orden, orden.asientos[0], "clave-evento", AHORA)
    assert len(boleto.codigo_redencion) == 12 and boleto.codigo_redencion.isalnum()
    assert boleto.firma_es_valida(orden, "clave-evento")
    assert not boleto.firma_es_valida(orden, "otra-clave")
    orden.monto_total = Decimal("1.00")
    assert not boleto.firma_es_valida(orden, "clave-evento")
