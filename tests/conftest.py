from datetime import datetime, timezone

import pytest

from stagepass.adapters.salida.persistencia import datos_semilla as semilla
from stagepass.adapters.salida.servicios.servicios_simulados import RelojFijo
from stagepass.bootstrap import construir_contenedor
from stagepass.domain.modelo import Cliente, MedioPago
from stagepass.ports.entrada import IniciarCompraCommand


@pytest.fixture
def reloj():
    return RelojFijo(datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc))


@pytest.fixture
def contenedor(reloj):
    return construir_contenedor(modo="memoria", reloj=reloj, auto_aprobar_pagos=False)


def cliente(n: int = 1) -> Cliente:
    return Cliente(f"cli-{n}", f"Cliente {n}", f"cliente{n}@correo.co", f"+57300000000{n}", "Colombiana")


def comando(asientos, cli=1, evento=semilla.EVENTO_CONCIERTO, medio=MedioPago.WOMPI):
    return IniciarCompraCommand(cliente(cli), evento, list(asientos), medio)


VIP = [f"arena-VIP-A{n}" for n in range(1, 9)]
GENERAL = [f"arena-GENERAL-{n:02d}" for n in range(1, 13)]
