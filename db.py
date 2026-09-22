"""
Base de datos y bitacora auditable (SQLite).
Ahora tambien guarda el INVENTARIO de dispositivos autorizados, para que
sobreviva a los reinicios y se pueda editar desde la interfaz.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "bitacora.db"

# Inventario inicial (se carga solo la primera vez que se crea la tabla).
INVENTARIO_INICIAL = [
    ("10.10.10.51", "SRV-TRAZA", "servidor", "SW-CIRC-A"),
    ("10.10.10.52", "CAM-01",    "camara",   "SW-CIRC-A"),
    ("10.10.10.53", "CAM-02",    "camara",   "SW-CIRC-A"),
    ("10.10.10.54", "LECT-01",   "lectora",  "SW-CIRC-B"),
]


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = conectar()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS eventos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT NOT NULL,
            modulo       TEXT NOT NULL,
            tipo         TEXT NOT NULL,
            severidad    TEXT NOT NULL,
            descripcion  TEXT NOT NULL,
            control_iso  TEXT,
            norma        TEXT
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario (
            ip      TEXT PRIMARY KEY,
            nombre  TEXT NOT NULL,
            tipo    TEXT NOT NULL,
            switch  TEXT NOT NULL
        )
        """
    )
    con.commit()
    # Sembrar inventario inicial solo si esta vacio.
    n = con.execute("SELECT COUNT(*) AS c FROM inventario").fetchone()["c"]
    if n == 0:
        con.executemany(
            "INSERT INTO inventario (ip, nombre, tipo, switch) VALUES (?, ?, ?, ?)",
            INVENTARIO_INICIAL,
        )
        con.commit()
    con.close()


# ---------------------- Bitacora ----------------------
def registrar_evento(modulo, tipo, severidad, descripcion, control_iso="", norma=""):
    con = conectar()
    cur = con.execute(
        """INSERT INTO eventos (timestamp, modulo, tipo, severidad, descripcion, control_iso, norma)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now().isoformat(sep=" ", timespec="seconds"),
         modulo, tipo, severidad, descripcion, control_iso, norma),
    )
    con.commit()
    eid = cur.lastrowid
    con.close()
    return eid


def obtener_eventos(limite=200):
    con = conectar()
    filas = con.execute(
        "SELECT * FROM eventos ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()
    con.close()
    return [dict(f) for f in filas]


def contar_por_severidad():
    con = conectar()
    filas = con.execute(
        "SELECT severidad, COUNT(*) AS total FROM eventos GROUP BY severidad"
    ).fetchall()
    con.close()
    return {f["severidad"]: f["total"] for f in filas}


# ---------------------- Inventario ----------------------
def inventario_listar():
    con = conectar()
    filas = con.execute("SELECT * FROM inventario ORDER BY nombre").fetchall()
    con.close()
    return [dict(f) for f in filas]


def inventario_agregar(ip, nombre, tipo, switch):
    con = conectar()
    con.execute(
        "INSERT OR REPLACE INTO inventario (ip, nombre, tipo, switch) VALUES (?, ?, ?, ?)",
        (ip, nombre, tipo, switch),
    )
    con.commit()
    con.close()


def inventario_eliminar(ip):
    con = conectar()
    con.execute("DELETE FROM inventario WHERE ip = ?", (ip,))
    con.commit()
    con.close()
