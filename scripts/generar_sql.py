from pathlib import Path

from stagepass.adapters.salida.persistencia import datos_semilla as semilla

ESQUEMA = """\
CREATE TABLE IF NOT EXISTS recintos (
  id        VARCHAR(40)  PRIMARY KEY,
  nombre    VARCHAR(120) NOT NULL,
  ciudad    VARCHAR(80)  NOT NULL,
  aforo     INT          NOT NULL
);

CREATE TABLE IF NOT EXISTS asientos (
  id                VARCHAR(60)   PRIMARY KEY,
  recinto_id        VARCHAR(40)   NOT NULL,
  codigo_ubicacion  VARCHAR(40)   NOT NULL,
  precio_base       DECIMAL(12,2) NOT NULL,
  UNIQUE KEY uq_asiento_recinto (recinto_id, codigo_ubicacion),
  CONSTRAINT fk_asiento_recinto FOREIGN KEY (recinto_id) REFERENCES recintos (id)
);

CREATE TABLE IF NOT EXISTS eventos (
  id             VARCHAR(40)  PRIMARY KEY,
  nombre         VARCHAR(160) NOT NULL,
  tipo           ENUM('CONCIERTO','TEATRO','FESTIVAL') NOT NULL,
  recinto_id     VARCHAR(40)  NOT NULL,
  fecha_hora     DATETIME     NOT NULL,
  estado         ENUM('PROGRAMADO','AGOTADO','CANCELADO') NOT NULL,
  clave_secreta  VARCHAR(128) NOT NULL,
  CONSTRAINT fk_evento_recinto FOREIGN KEY (recinto_id) REFERENCES recintos (id)
);
"""


def q(texto: str) -> str:
    return "'" + texto.replace("'", "''") + "'"


def main() -> None:
    lineas = [ESQUEMA]
    for r in semilla.recintos():
        lineas.append(
            f"INSERT INTO recintos (id, nombre, ciudad, aforo) VALUES "
            f"({q(r.id)}, {q(r.nombre)}, {q(r.ciudad)}, {r.aforo});"
        )
    for a in semilla.asientos():
        lineas.append(
            f"INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES "
            f"({q(a.id)}, {q(a.recinto_id)}, {q(a.codigo_ubicacion)}, {a.precio_base});"
        )
    for e in semilla.eventos():
        lineas.append(
            f"INSERT INTO eventos (id, nombre, tipo, recinto_id, fecha_hora, estado, clave_secreta) VALUES "
            f"({q(e.id)}, {q(e.nombre)}, {q(e.tipo.name)}, {q(e.recinto_id)}, "
            f"{q(e.fecha_hora.strftime('%Y-%m-%d %H:%M:%S'))}, {q(e.estado.name)}, {q(e.clave_secreta)});"
        )
    destino = Path(__file__).resolve().parents[1] / "sql" / "init.sql"
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"Escrito {destino}")


if __name__ == "__main__":
    main()
