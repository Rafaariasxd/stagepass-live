# StagePass Live

Plataforma de venta de boletería con arquitectura hexagonal (puertos y adaptadores) en Python.

## Estructura

```
stagepass/
  domain/         entidades, reglas de negocio, excepciones
  ports/          entrada.py (puertos primarios), salida.py (puertos secundarios)
  application/    casos de uso
  adapters/
    entrada/http/          API FastAPI y traductores de webhook
    salida/persistencia/   MySQL, MongoDB y memoria
    salida/pagos/          PayPal, Wompi y PSE
    salida/notificaciones/ SendGrid y WhatsApp
    salida/servicios/      imagen del boleto, DIAN y reloj
  bootstrap.py    composición de puertos y adaptadores
tests/
sql/init.sql      esquema y datos del catálogo MySQL
```

## Ejecución

```bash
pip install -r requirements.txt
python -m pytest
uvicorn stagepass.main:app --reload
```

Con MySQL y MongoDB:

```bash
docker compose up -d
STAGEPASS_MODO=real uvicorn stagepass.main:app
```

Variables opcionales: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `MONGO_URI`, `MONGO_DATABASE`.

## Endpoints

| Método | Ruta |
|---|---|
| GET | `/eventos/{evento_id}/asientos` |
| POST | `/compras` |
| POST | `/webhooks/pagos/{paypal\|wompi\|pse}` |
| GET | `/ordenes/{orden_id}` |
| GET | `/boletos/{codigo}/validar` |

Eventos de ejemplo: `evt-concierto-001`, `evt-teatro-001`.
