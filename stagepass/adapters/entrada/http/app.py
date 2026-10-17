from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from stagepass.adapters.entrada.http.traductores_webhook import (
    TRADUCTORES,
    PayloadInvalidoError,
)
from stagepass.bootstrap import Contenedor
from stagepass.domain.excepciones import (
    AsientoNoDisponibleError,
    DatosInvalidosError,
    DominioError,
    EntidadNoEncontradaError,
    EventoNoDisponibleError,
    LimiteBoletosExcedidoError,
    OrdenExpiradaError,
    PagoNoVerificadoError,
    SeleccionInvalidaError,
    TransicionInvalidaError,
)
from stagepass.domain.modelo import Asiento, Boleto, Cliente, MedioPago, Orden
from stagepass.ports.entrada import ConfirmarPagoCommand, IniciarCompraCommand

_STATUS_POR_ERROR = {
    EntidadNoEncontradaError: 404,
    AsientoNoDisponibleError: 409,
    TransicionInvalidaError: 409,
    OrdenExpiradaError: 409,
    EventoNoDisponibleError: 409,
    LimiteBoletosExcedidoError: 422,
    SeleccionInvalidaError: 422,
    DatosInvalidosError: 422,
    PagoNoVerificadoError: 402,
}


class ClienteIn(BaseModel):
    id: str
    nombre_completo: str
    correo: str
    telefono_movil: str
    nacionalidad: str


class CompraIn(BaseModel):
    cliente: ClienteIn
    evento_id: str
    asiento_ids: List[str]
    medio_pago: Literal["PAYPAL", "WOMPI", "PSE"]


def _asiento_a_dict(a: Asiento) -> Dict[str, Any]:
    return {
        "id": a.id,
        "codigo_ubicacion": a.codigo_ubicacion,
        "precio_base": str(a.precio_base),
        "estado": a.estado.value,
    }


def _orden_a_dict(o: Orden) -> Dict[str, Any]:
    return {
        "id": o.id,
        "evento_id": o.evento_id,
        "cliente_id": o.cliente.id,
        "asientos": [a.codigo_ubicacion for a in o.asientos],
        "medio_pago": o.medio_pago.value,
        "subtotal": str(o.subtotal),
        "tarifa_servicio": str(o.tarifa_servicio),
        "descuento": str(o.descuento),
        "monto_total": str(o.monto_total),
        "expira_en": o.expira_en.isoformat(),
        "estado": o.estado.value,
        "referencia_pago": o.referencia_pago,
    }


def _boleto_a_dict(b: Boleto) -> Dict[str, Any]:
    return {
        "id": b.id,
        "asiento": b.asiento_codigo,
        "codigo_redencion": b.codigo_redencion,
        "firma_hash": b.firma_hash,
        "fecha_emision": b.fecha_emision.isoformat(),
    }


def crear_app(contenedor: Contenedor, intervalo_expiracion_s: float | None = None) -> FastAPI:
    if intervalo_expiracion_s is None:
        intervalo_expiracion_s = float(os.getenv("STAGEPASS_INTERVALO_EXPIRACION", "30"))

    async def _bucle_expiracion() -> None:
        while True:
            await asyncio.sleep(intervalo_expiracion_s)
            await asyncio.to_thread(contenedor.expirar_ordenes.ejecutar)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        tarea = asyncio.create_task(_bucle_expiracion())
        try:
            yield
        finally:
            tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tarea

    app = FastAPI(title="StagePass Live — Event & Concert Platform", lifespan=lifespan)

    @app.exception_handler(DominioError)
    async def _errores_de_dominio(_: Request, error: DominioError) -> JSONResponse:
        status = next(
            (codigo for tipo, codigo in _STATUS_POR_ERROR.items() if isinstance(error, tipo)),
            400,
        )
        return JSONResponse(status_code=status, content={"error": str(error)})

    @app.get("/eventos/{evento_id}/asientos")
    def disponibilidad(evento_id: str) -> List[Dict[str, Any]]:
        return [_asiento_a_dict(a) for a in contenedor.consultar_disponibilidad.ejecutar(evento_id)]

    @app.post("/compras", status_code=201)
    def iniciar_compra(datos: CompraIn) -> Dict[str, Any]:
        comando = IniciarCompraCommand(
            cliente=Cliente(**datos.cliente.model_dump()),
            evento_id=datos.evento_id,
            asiento_ids=datos.asiento_ids,
            medio_pago=MedioPago[datos.medio_pago],
        )
        return _orden_a_dict(contenedor.iniciar_compra.ejecutar(comando))

    @app.post("/webhooks/pagos/{proveedor}")
    def webhook_pago(proveedor: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        traductor = TRADUCTORES.get(proveedor.lower())
        if traductor is None:
            raise HTTPException(404, f"Proveedor de pagos desconocido: {proveedor}")
        try:
            comando: ConfirmarPagoCommand = traductor.traducir(payload)
        except PayloadInvalidoError as error:
            raise HTTPException(400, str(error)) from error
        resultado = contenedor.confirmar_pago.ejecutar(comando)
        return {
            "orden_id": resultado.orden.id,
            "estado": resultado.orden.estado.value,
            "boletos_emitidos": len(resultado.boletos),
            "advertencias": resultado.advertencias,
        }

    @app.get("/ordenes/{orden_id}")
    def consultar_orden(orden_id: str) -> Dict[str, Any]:
        detalle = contenedor.consultar_orden.ejecutar(orden_id)
        return {**_orden_a_dict(detalle.orden), "boletos": [_boleto_a_dict(b) for b in detalle.boletos]}

    @app.get("/boletos/{codigo_redencion}/validar")
    def validar_boleto(codigo_redencion: str) -> Dict[str, Any]:
        resultado = contenedor.validar_boleto.ejecutar(codigo_redencion)
        return {
            "valido": resultado.valido,
            "motivo": resultado.motivo,
            "asiento": resultado.boleto.asiento_codigo if resultado.boleto else None,
        }

    return app
