from decimal import Decimal

import pytest

from stagepass.adapters.salida.persistencia import datos_semilla as semilla
from stagepass.domain.excepciones import (
    AsientoNoDisponibleError,
    EntidadNoEncontradaError,
    EventoNoDisponibleError,
    LimiteBoletosExcedidoError,
    OrdenExpiradaError,
    TransicionInvalidaError,
)
from stagepass.domain.modelo import EstadoAsiento, EstadoOrden, MedioPago
from stagepass.domain.valores import EstadoPago
from stagepass.ports.entrada import ConfirmarPagoCommand

from tests.conftest import GENERAL, VIP, comando


def estados(contenedor):
    return {a.id: a.estado for a in contenedor.consultar_disponibilidad.ejecutar(semilla.EVENTO_CONCIERTO)}


def pagar(contenedor, orden, estado=EstadoPago.APROBADO):
    contenedor.pasarelas[orden.medio_pago].simular_estado(orden.referencia_pago, estado)
    return contenedor.confirmar_pago.ejecutar(ConfirmarPagoCommand(orden.id))


def test_iniciar_compra_liquida_y_bloquea(contenedor):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:3]))
    assert orden.estado is EstadoOrden.PENDIENTE_PAGO
    assert orden.subtotal == Decimal("1350000.00")
    assert orden.tarifa_servicio == Decimal("108000.00")
    assert orden.descuento == Decimal("67500.00")
    assert orden.monto_total == Decimal("1390500.00")
    assert orden.referencia_pago.startswith("WOMPI-")
    est = estados(contenedor)
    assert all(est[a] is EstadoAsiento.BLOQUEADO for a in VIP[:3])
    assert est[VIP[3]] is EstadoAsiento.DISPONIBLE


def test_asiento_bloqueado_no_se_puede_comprar_dos_veces(contenedor):
    contenedor.iniciar_compra.ejecutar(comando(VIP[:2], cli=1))
    with pytest.raises(AsientoNoDisponibleError):
        contenedor.iniciar_compra.ejecutar(comando([VIP[1], VIP[4]], cli=2))


def test_bloqueo_vence_a_los_diez_minutos_y_libera_asientos(contenedor, reloj):
    contenedor.iniciar_compra.ejecutar(comando(VIP[:2], cli=1))
    reloj.avanzar(minutes=10)
    assert estados(contenedor)[VIP[0]] is EstadoAsiento.DISPONIBLE
    otra = contenedor.iniciar_compra.ejecutar(comando(VIP[:2], cli=2))
    assert otra.estado is EstadoOrden.PENDIENTE_PAGO


def test_job_de_expiracion_marca_ordenes_vencidas(contenedor, reloj):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    assert contenedor.expirar_ordenes.ejecutar() == 0
    reloj.avanzar(minutes=11)
    assert contenedor.expirar_ordenes.ejecutar() == 1
    assert contenedor.consultar_orden.ejecutar(orden.id).orden.estado is EstadoOrden.EXPIRADA


def test_limite_de_seis_boletas_por_evento_acumulado(contenedor):
    contenedor.iniciar_compra.ejecutar(comando(VIP[:4], cli=1))
    contenedor.iniciar_compra.ejecutar(comando(VIP[4:6], cli=1))
    with pytest.raises(LimiteBoletosExcedidoError):
        contenedor.iniciar_compra.ejecutar(comando(GENERAL[:1], cli=1))
    contenedor.iniciar_compra.ejecutar(comando(GENERAL[:1], cli=2))


def test_evento_cancelado_o_inexistente(contenedor):
    with pytest.raises(EventoNoDisponibleError):
        contenedor.iniciar_compra.ejecutar(comando(VIP[:1], evento=semilla.EVENTO_FESTIVAL_CANCELADO))
    with pytest.raises(EntidadNoEncontradaError):
        contenedor.iniciar_compra.ejecutar(comando(VIP[:1], evento="no-existe"))


def test_asiento_de_otro_recinto_se_rechaza(contenedor):
    from stagepass.domain.excepciones import SeleccionInvalidaError

    with pytest.raises(SeleccionInvalidaError):
        contenedor.iniciar_compra.ejecutar(comando(["teatro-PLATEA-01"]))


def test_pago_aprobado_emite_boletas_notifica_y_factura(contenedor):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:2]))
    resultado = pagar(contenedor, orden)

    assert resultado.orden.estado is EstadoOrden.APROBADA
    assert len(resultado.boletos) == 2
    assert resultado.factura is not None and resultado.factura.numero.startswith("SETP-")
    assert resultado.advertencias == []
    assert all(len(n.enviados) == 1 for n in contenedor.notificadores)
    assert estados(contenedor)[VIP[0]] is EstadoAsiento.VENDIDO
    for boleto in resultado.boletos:
        assert contenedor.validar_boleto.ejecutar(boleto.codigo_redencion).valido


def test_confirmacion_es_idempotente(contenedor):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    primera = pagar(contenedor, orden)
    segunda = contenedor.confirmar_pago.ejecutar(ConfirmarPagoCommand(orden.id))
    assert [b.id for b in primera.boletos] == [b.id for b in segunda.boletos]
    assert len(contenedor.notificadores[0].enviados) == 1


def test_pago_rechazado_libera_los_asientos(contenedor):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:2]))
    resultado = pagar(contenedor, orden, EstadoPago.RECHAZADO)
    assert resultado.orden.estado is EstadoOrden.RECHAZADA and resultado.boletos == []
    assert estados(contenedor)[VIP[0]] is EstadoAsiento.DISPONIBLE


def test_pago_pendiente_no_cambia_nada(contenedor):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    resultado = contenedor.confirmar_pago.ejecutar(ConfirmarPagoCommand(orden.id))
    assert resultado.orden.estado is EstadoOrden.PENDIENTE_PAGO and resultado.boletos == []


def test_pago_tardio_expira_la_orden_y_no_emite_boletas(contenedor, reloj):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    reloj.avanzar(minutes=10, seconds=1)
    with pytest.raises(OrdenExpiradaError):
        pagar(contenedor, orden)
    detalle = contenedor.consultar_orden.ejecutar(orden.id)
    assert detalle.orden.estado is EstadoOrden.EXPIRADA and detalle.boletos == []


def test_monto_distinto_al_de_la_orden_no_se_acepta(contenedor):
    from stagepass.domain.excepciones import PagoNoVerificadoError

    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    contenedor.pasarelas[MedioPago.WOMPI].simular_monto(orden.referencia_pago, Decimal("1"))
    with pytest.raises(PagoNoVerificadoError):
        contenedor.confirmar_pago.ejecutar(ConfirmarPagoCommand(orden.id))


def test_orden_expirada_no_puede_confirmarse(contenedor, reloj):
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    reloj.avanzar(minutes=11)
    contenedor.expirar_ordenes.ejecutar()
    with pytest.raises(TransicionInvalidaError):
        pagar(contenedor, orden)


def test_fallo_en_notificacion_no_revierte_la_emision(contenedor):
    class Roto:
        canal = "roto"

        def enviar(self, *_):
            raise RuntimeError("sin servicio")

    contenedor.notificadores.append(Roto())
    orden = contenedor.iniciar_compra.ejecutar(comando(VIP[:1]))
    resultado = pagar(contenedor, orden)
    assert len(resultado.boletos) == 1
    assert any("roto" in a for a in resultado.advertencias)


def test_validar_boleto_inexistente(contenedor):
    assert not contenedor.validar_boleto.ejecutar("NOEXISTE0000").valido
