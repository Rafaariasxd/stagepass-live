from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from stagepass.adapters.salida.notificaciones.notificadores_simulados import (
    NotificadorEmailSendGridMock,
    NotificadorWhatsAppMock,
)
from stagepass.adapters.salida.pagos.pasarelas_simuladas import (
    PasarelaPayPalMock,
    PasarelaPSEMock,
    PasarelaWompiMock,
)
from stagepass.adapters.salida.persistencia.memoria import (
    RepositorioBoletosMemoria,
    RepositorioCatalogoMemoria,
    RepositorioOrdenesMemoria,
)
from stagepass.adapters.salida.servicios.servicios_simulados import (
    EmisorFacturaDIANMock,
    GeneradorBoletoSVGMock,
    RelojSistema,
)
from stagepass.application.casos_uso import (
    ServicioConfirmarPago,
    ServicioConsultaDisponibilidad,
    ServicioConsultaOrden,
    ServicioExpirarOrdenes,
    ServicioIniciarCompra,
    ServicioValidarBoleto,
)
from stagepass.domain.modelo import MedioPago
from stagepass.domain.tarifas import CalculadoraTarifas
from stagepass.ports.entrada import (
    ConfirmarPagoUseCase,
    ConsultarDisponibilidadUseCase,
    ConsultarOrdenUseCase,
    ExpirarOrdenesUseCase,
    IniciarCompraUseCase,
    ValidarBoletoUseCase,
)
from stagepass.ports.salida import (
    NotificadorCliente,
    PasarelaPago,
    Reloj,
    RepositorioBoletos,
    RepositorioCatalogo,
    RepositorioOrdenes,
)


@dataclass
class Contenedor:
    consultar_disponibilidad: ConsultarDisponibilidadUseCase
    iniciar_compra: IniciarCompraUseCase
    confirmar_pago: ConfirmarPagoUseCase
    expirar_ordenes: ExpirarOrdenesUseCase
    consultar_orden: ConsultarOrdenUseCase
    validar_boleto: ValidarBoletoUseCase
    pasarelas: Dict[MedioPago, PasarelaPago]
    notificadores: List[NotificadorCliente]


def _repositorios_reales():
    from pymongo import MongoClient

    from stagepass.adapters.salida.persistencia.mongo_repositorios import (
        RepositorioBoletosMongo,
        RepositorioOrdenesMongo,
        crear_indices,
    )
    from stagepass.adapters.salida.persistencia.mysql_catalogo import (
        RepositorioCatalogoMySQL,
        crear_fabrica_conexion,
    )

    fabrica = crear_fabrica_conexion(
        host=os.getenv("MYSQL_HOST", "localhost"),
        puerto=int(os.getenv("MYSQL_PORT", "3306")),
        usuario=os.getenv("MYSQL_USER", "stagepass"),
        clave=os.getenv("MYSQL_PASSWORD", "stagepass"),
        base_datos=os.getenv("MYSQL_DATABASE", "stagepass_legacy"),
    )
    cliente_mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    base = cliente_mongo[os.getenv("MONGO_DATABASE", "stagepass")]
    crear_indices(base)
    return (
        RepositorioCatalogoMySQL(fabrica),
        RepositorioOrdenesMongo(base["ordenes"]),
        RepositorioBoletosMongo(base["boletos"]),
    )


def construir_contenedor(
    modo: Optional[str] = None,
    reloj: Optional[Reloj] = None,
    auto_aprobar_pagos: bool = True,
    catalogo: Optional[RepositorioCatalogo] = None,
    ordenes: Optional[RepositorioOrdenes] = None,
    boletos: Optional[RepositorioBoletos] = None,
) -> Contenedor:
    modo = modo or os.getenv("STAGEPASS_MODO", "memoria")
    if catalogo is None or ordenes is None or boletos is None:
        if modo == "real":
            catalogo, ordenes, boletos = _repositorios_reales()
        elif modo == "memoria":
            catalogo = catalogo or RepositorioCatalogoMemoria()
            ordenes = ordenes or RepositorioOrdenesMemoria()
            boletos = boletos or RepositorioBoletosMemoria()
        else:
            raise ValueError(f"Modo desconocido: {modo!r} (use 'memoria' o 'real')")
    reloj = reloj or RelojSistema()

    pasarelas: Dict[MedioPago, PasarelaPago] = {
        MedioPago.PAYPAL: PasarelaPayPalMock(auto_aprobar_pagos),
        MedioPago.WOMPI: PasarelaWompiMock(auto_aprobar_pagos),
        MedioPago.PSE: PasarelaPSEMock(auto_aprobar_pagos),
    }
    notificadores: List[NotificadorCliente] = [
        NotificadorEmailSendGridMock(),
        NotificadorWhatsAppMock(),
    ]

    return Contenedor(
        consultar_disponibilidad=ServicioConsultaDisponibilidad(catalogo, ordenes, reloj),
        iniciar_compra=ServicioIniciarCompra(
            catalogo, ordenes, pasarelas, CalculadoraTarifas(), reloj
        ),
        confirmar_pago=ServicioConfirmarPago(
            catalogo,
            ordenes,
            boletos,
            pasarelas,
            GeneradorBoletoSVGMock(),
            notificadores,
            EmisorFacturaDIANMock(),
            reloj,
        ),
        expirar_ordenes=ServicioExpirarOrdenes(ordenes, reloj),
        consultar_orden=ServicioConsultaOrden(ordenes, boletos),
        validar_boleto=ServicioValidarBoleto(catalogo, ordenes, boletos),
        pasarelas=pasarelas,
        notificadores=notificadores,
    )
