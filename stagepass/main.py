from stagepass.adapters.entrada.http.app import crear_app
from stagepass.bootstrap import construir_contenedor

app = crear_app(construir_contenedor())
