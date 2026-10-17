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

INSERT INTO recintos (id, nombre, ciudad, aforo) VALUES ('rec-arena', 'Arena Bogotá', 'Bogotá', 20);
INSERT INTO recintos (id, nombre, ciudad, aforo) VALUES ('rec-teatro', 'Teatro Santander', 'Bucaramanga', 8);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A1', 'rec-arena', 'VIP-A1', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A2', 'rec-arena', 'VIP-A2', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A3', 'rec-arena', 'VIP-A3', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A4', 'rec-arena', 'VIP-A4', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A5', 'rec-arena', 'VIP-A5', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A6', 'rec-arena', 'VIP-A6', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A7', 'rec-arena', 'VIP-A7', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-VIP-A8', 'rec-arena', 'VIP-A8', 450000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-01', 'rec-arena', 'General-01', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-02', 'rec-arena', 'General-02', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-03', 'rec-arena', 'General-03', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-04', 'rec-arena', 'General-04', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-05', 'rec-arena', 'General-05', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-06', 'rec-arena', 'General-06', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-07', 'rec-arena', 'General-07', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-08', 'rec-arena', 'General-08', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-09', 'rec-arena', 'General-09', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-10', 'rec-arena', 'General-10', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-11', 'rec-arena', 'General-11', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('arena-GENERAL-12', 'rec-arena', 'General-12', 180000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-01', 'rec-teatro', 'Platea-01', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-02', 'rec-teatro', 'Platea-02', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-03', 'rec-teatro', 'Platea-03', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-04', 'rec-teatro', 'Platea-04', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-05', 'rec-teatro', 'Platea-05', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-06', 'rec-teatro', 'Platea-06', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-07', 'rec-teatro', 'Platea-07', 90000.00);
INSERT INTO asientos (id, recinto_id, codigo_ubicacion, precio_base) VALUES ('teatro-PLATEA-08', 'rec-teatro', 'Platea-08', 90000.00);
INSERT INTO eventos (id, nombre, tipo, recinto_id, fecha_hora, estado, clave_secreta) VALUES ('evt-concierto-001', 'Rock Andino en Vivo', 'CONCIERTO', 'rec-arena', '2026-12-05 20:00:00', 'PROGRAMADO', 'clave-secreta-rock-andino');
INSERT INTO eventos (id, nombre, tipo, recinto_id, fecha_hora, estado, clave_secreta) VALUES ('evt-teatro-001', 'La Casa de Bernarda Alba', 'TEATRO', 'rec-teatro', '2026-11-20 19:30:00', 'PROGRAMADO', 'clave-secreta-bernarda');
INSERT INTO eventos (id, nombre, tipo, recinto_id, fecha_hora, estado, clave_secreta) VALUES ('evt-festival-001', 'Festival de Verano', 'FESTIVAL', 'rec-arena', '2026-08-01 14:00:00', 'CANCELADO', 'clave-secreta-verano');
