from __future__ import annotations

import logging
from typing import List, Mapping, Sequence

from stagepass.domain.excepciones import (
    EntidadNoEncontradaError,
    EventoNoDisponibleError,
    OrdenExpiradaError,
    PagoNoVerificadoError,
    TransicionInvalidaError,
)
from stagepass.domain.modelo import (
    Asiento,
    Boleto,
    Evento,
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
from stagepass.domain.valores import EstadoPago, Mensaje, SolicitudPago
from stagepass.ports.entrada import (
    ConfirmarPagoCommand,
    ConfirmarPagoUseCase,
    ConsultarDisponibilidadUseCase,
    ConsultarOrdenUseCase,
    DetalleOrden,
    ExpirarOrdenesUseCase,
    IniciarCompraCommand,
    IniciarCompraUseCase,
    ResultadoConfirmacion,
    ResultadoValidacion,
    ValidarBoletoUseCase,
)
from stagepass.ports.salida import (
    EmisorFacturaElectronica,
    GeneradorRepresentacionBoleto,
    NotificadorCliente,
    PasarelaPago,
    Reloj,
    RepositorioBoletos,
    RepositorioCatalogo,
    RepositorioOrdenes,
)

logger = logging.getLogger(__name__)

MONEDA = "COP"


def _obtener_evento(catalogo: RepositorioCatalogo, evento_id: str) -> Evento:
    evento = catalogo.obtener_evento(evento_id)
    if evento is None:
        raise EntidadNoEncontradaError("Evento", evento_id)
    return evento


def _obtener_orden(ordenes: RepositorioOrdenes, orden_id: str) -> Orden:
    orden = ordenes.obtener(orden_id)
    if orden is None:
        raise EntidadNoEncontradaError("Orden", orden_id)
    return orden


class ServicioConsultaDisponibilidad(ConsultarDisponibilidadUseCase):
    def __init__(
        self, catalogo: RepositorioCatalogo, ordenes: RepositorioOrdenes, reloj: Reloj
    ) -> None:
        self._catalogo = catalogo
        self._ordenes = ordenes
        self._reloj = reloj

    def ejecutar(self, evento_id: str) -> List[Asiento]:
        evento = _obtener_evento(self._catalogo, evento_id)
        ahora = self._reloj.ahora()
        asientos = self._catalogo.listar_asientos_recinto(evento.recinto_id)
        ocupantes = self._ordenes.buscar_ocupantes_evento(evento.id, ahora)
        return aplicar_ocupacion(asientos, ocupantes, ahora)


class ServicioIniciarCompra(IniciarCompraUseCase):
    def __init__(
        self,
        catalogo: RepositorioCatalogo,
        ordenes: RepositorioOrdenes,
        pasarelas: Mapping[MedioPago, PasarelaPago],
        calculadora: CalculadoraTarifas,
        reloj: Reloj,
    ) -> None:
        self._catalogo = catalogo
        self._ordenes = ordenes
        self._pasarelas = pasarelas
        self._calculadora = calculadora
        self._reloj = reloj

    def ejecutar(self, comando: IniciarCompraCommand) -> Orden:
        evento = _obtener_evento(self._catalogo, comando.evento_id)
        if not evento.admite_ventas():
            raise EventoNoDisponibleError(
                f"El evento '{evento.nombre}' está {evento.estado.value}"
            )
        pasarela = self._pasarelas.get(comando.medio_pago)
        if pasarela is None:
            raise EntidadNoEncontradaError("Pasarela de pago", comando.medio_pago.value)

        ahora = self._reloj.ahora()

        catalogo = self._catalogo.listar_asientos_recinto(evento.recinto_id)
        ocupantes = self._ordenes.buscar_ocupantes_evento(evento.id, ahora)
        seleccion = seleccionar_asientos(
            aplicar_ocupacion(catalogo, ocupantes, ahora), comando.asiento_ids
        )

        previas = self._ordenes.buscar_por_cliente_y_evento(comando.cliente.id, evento.id)
        validar_limite_boletos(contar_boletos_acumulados(previas, ahora), len(seleccion))

        liquidacion = self._calculadora.calcular(seleccion)

        orden = Orden.crear(
            cliente=comando.cliente,
            evento_id=evento.id,
            asientos=seleccion,
            medio_pago=comando.medio_pago,
            subtotal=liquidacion.subtotal,
            tarifa_servicio=liquidacion.tarifa_servicio,
            descuento=liquidacion.descuento,
            monto_total=liquidacion.monto_total,
            ahora=ahora,
        )
        self._ordenes.guardar(orden)

        try:
            referencia = pasarela.registrar_pago(
                SolicitudPago(
                    orden_id=orden.id,
                    monto=orden.monto_total,
                    moneda=MONEDA,
                    cliente=orden.cliente,
                    descripcion=f"{evento.nombre} x{orden.cantidad_boletos}",
                )
            )
        except Exception:
            orden.rechazar()
            self._ordenes.guardar(orden)
            raise
        orden.registrar_referencia_pago(referencia.referencia)
        self._ordenes.guardar(orden)
        return orden


class ServicioConfirmarPago(ConfirmarPagoUseCase):
    def __init__(
        self,
        catalogo: RepositorioCatalogo,
        ordenes: RepositorioOrdenes,
        boletos: RepositorioBoletos,
        pasarelas: Mapping[MedioPago, PasarelaPago],
        generador: GeneradorRepresentacionBoleto,
        notificadores: Sequence[NotificadorCliente],
        facturador: EmisorFacturaElectronica,
        reloj: Reloj,
    ) -> None:
        self._catalogo = catalogo
        self._ordenes = ordenes
        self._boletos = boletos
        self._pasarelas = pasarelas
        self._generador = generador
        self._notificadores = notificadores
        self._facturador = facturador
        self._reloj = reloj

    def ejecutar(self, comando: ConfirmarPagoCommand) -> ResultadoConfirmacion:
        orden = _obtener_orden(self._ordenes, comando.orden_id)

        if orden.estado is EstadoOrden.APROBADA:
            return ResultadoConfirmacion(orden, self._boletos.buscar_por_orden(orden.id))
        if orden.estado is not EstadoOrden.PENDIENTE_PAGO:
            raise TransicionInvalidaError(
                f"La orden {orden.id} está '{orden.estado.value}' y no puede confirmarse"
            )

        pasarela = self._pasarelas[orden.medio_pago]
        if orden.referencia_pago is None:
            raise PagoNoVerificadoError("La orden no tiene un pago registrado")
        resultado = pasarela.verificar_pago(orden.referencia_pago)
        if resultado.monto != orden.monto_total:
            raise PagoNoVerificadoError(
                f"El monto pagado ({resultado.monto}) no coincide con la orden ({orden.monto_total})"
            )

        if resultado.estado is EstadoPago.PENDIENTE:
            return ResultadoConfirmacion(orden)
        if resultado.estado is EstadoPago.RECHAZADO:
            orden.rechazar()
            self._ordenes.guardar(orden)
            return ResultadoConfirmacion(orden)

        ahora = self._reloj.ahora()
        try:
            orden.aprobar(ahora)
        except OrdenExpiradaError:
            orden.expirar()
            self._ordenes.guardar(orden)
            raise

        evento = _obtener_evento(self._catalogo, orden.evento_id)
        boletos = [
            Boleto.emitir(orden, asiento, evento.clave_secreta, ahora)
            for asiento in orden.asientos
        ]
        self._ordenes.guardar(orden)
        self._boletos.guardar_todos(boletos)

        factura, advertencias = self._efectos_posteriores(orden, evento, boletos)
        return ResultadoConfirmacion(orden, boletos, factura, advertencias)

    def _efectos_posteriores(self, orden: Orden, evento: Evento, boletos: List[Boleto]):
        advertencias: List[str] = []
        representaciones = []
        for boleto in boletos:
            try:
                representaciones.append(self._generador.generar(boleto, evento))
            except Exception as error:
                logger.exception("No se pudo generar la representación del boleto %s", boleto.id)
                advertencias.append(f"representación de {boleto.asiento_codigo}: {error}")

        mensaje = Mensaje(
            asunto=f"Tus boletas para {evento.nombre}",
            cuerpo=_cuerpo_confirmacion(orden, evento, boletos),
            adjuntos=tuple(representaciones),
        )
        for notificador in self._notificadores:
            try:
                notificador.enviar(orden.cliente, mensaje)
            except Exception as error:
                logger.exception("Falló la notificación por %s", notificador.canal)
                advertencias.append(f"notificación {notificador.canal}: {error}")

        factura = None
        try:
            factura = self._facturador.emitir(orden)
        except Exception as error:
            logger.exception("Falló la factura electrónica de la orden %s", orden.id)
            advertencias.append(f"factura electrónica: {error}")
        return factura, advertencias


def _cuerpo_confirmacion(orden: Orden, evento: Evento, boletos: List[Boleto]) -> str:
    lineas = [
        f"Hola {orden.cliente.nombre_completo}, tu pago fue aprobado.",
        f"Evento: {evento.nombre} ({evento.fecha_hora:%Y-%m-%d %H:%M})",
        f"Total pagado: {orden.monto_total} COP",
        "Tus boletas:",
    ]
    lineas += [f"  - {b.asiento_codigo}: código {b.codigo_redencion}" for b in boletos]
    return "\n".join(lineas)


class ServicioExpirarOrdenes(ExpirarOrdenesUseCase):
    def __init__(self, ordenes: RepositorioOrdenes, reloj: Reloj) -> None:
        self._ordenes = ordenes
        self._reloj = reloj

    def ejecutar(self) -> int:
        vencidas = self._ordenes.buscar_pendientes_vencidas(self._reloj.ahora())
        for orden in vencidas:
            orden.expirar()
            self._ordenes.guardar(orden)
        return len(vencidas)


class ServicioConsultaOrden(ConsultarOrdenUseCase):
    def __init__(self, ordenes: RepositorioOrdenes, boletos: RepositorioBoletos) -> None:
        self._ordenes = ordenes
        self._boletos = boletos

    def ejecutar(self, orden_id: str) -> DetalleOrden:
        orden = _obtener_orden(self._ordenes, orden_id)
        return DetalleOrden(orden, self._boletos.buscar_por_orden(orden.id))


class ServicioValidarBoleto(ValidarBoletoUseCase):
    def __init__(
        self,
        catalogo: RepositorioCatalogo,
        ordenes: RepositorioOrdenes,
        boletos: RepositorioBoletos,
    ) -> None:
        self._catalogo = catalogo
        self._ordenes = ordenes
        self._boletos = boletos

    def ejecutar(self, codigo_redencion: str) -> ResultadoValidacion:
        boleto = self._boletos.buscar_por_codigo(codigo_redencion)
        if boleto is None:
            return ResultadoValidacion(False, "El código de redención no existe")
        orden = self._ordenes.obtener(boleto.orden_id)
        evento = self._catalogo.obtener_evento(boleto.evento_id)
        if orden is None or evento is None:
            return ResultadoValidacion(False, "Datos de la boleta incompletos", boleto)
        if orden.estado is not EstadoOrden.APROBADA:
            return ResultadoValidacion(False, "La orden de la boleta no está aprobada", boleto)
        if not boleto.firma_es_valida(orden, evento.clave_secreta):
            return ResultadoValidacion(False, "La firma de seguridad no coincide", boleto)
        return ResultadoValidacion(True, "Boleta válida", boleto)
