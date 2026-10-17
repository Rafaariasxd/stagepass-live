from __future__ import annotations

import logging
from typing import List, Tuple

from stagepass.domain.modelo import Cliente
from stagepass.domain.valores import Mensaje
from stagepass.ports.salida import NotificadorCliente

logger = logging.getLogger(__name__)


class _NotificadorSimulado(NotificadorCliente):
    def __init__(self) -> None:
        self.enviados: List[Tuple[str, Mensaje]] = []

    def _destino(self, cliente: Cliente) -> str:
        raise NotImplementedError

    def enviar(self, cliente: Cliente, mensaje: Mensaje) -> None:
        destino = self._destino(cliente)
        self.enviados.append((destino, mensaje))
        logger.info("[%s simulado] a %s: %s", self.canal, destino, mensaje.asunto)


class NotificadorEmailSendGridMock(_NotificadorSimulado):
    @property
    def canal(self) -> str:
        return "correo (SendGrid)"

    def _destino(self, cliente: Cliente) -> str:
        return cliente.correo


class NotificadorWhatsAppMock(_NotificadorSimulado):
    @property
    def canal(self) -> str:
        return "WhatsApp"

    def _destino(self, cliente: Cliente) -> str:
        return cliente.telefono_movil
