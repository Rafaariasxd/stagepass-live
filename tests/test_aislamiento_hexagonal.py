import ast
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1] / "stagepass"
PERMITIDO = {
    "domain": {"domain"},
    "ports": {"domain", "ports"},
    "application": {"domain", "ports", "application"},
}


def _importaciones(archivo: Path):
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            yield nodo.module


CASOS = [
    (capa, archivo)
    for capa in PERMITIDO
    for archivo in sorted((RAIZ / capa).glob("*.py"))
    if archivo.name != "__init__.py"
]


@pytest.mark.parametrize("capa, archivo", CASOS, ids=[f"{c}/{a.name}" for c, a in CASOS])
def test_el_hexagono_no_depende_de_infraestructura(capa, archivo):
    for modulo in _importaciones(archivo):
        raiz = modulo.split(".")[0]
        if raiz == "stagepass":
            destino = modulo.split(".")[1]
            assert destino in PERMITIDO[capa], f"{archivo.name} ({capa}) importa {modulo}"
        else:
            assert raiz in sys.stdlib_module_names or raiz == "__future__", (
                f"{archivo.name} ({capa}) depende de la librería externa '{raiz}'"
            )
