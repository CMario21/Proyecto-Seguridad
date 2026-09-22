# Plataforma de Monitoreo y Ciberresiliencia del Datacenter
### Operador Postal Designado — Seguridad y Auditoría de Sistemas

Plataforma web que monitorea, detecta y registra de forma auditable los
eventos de seguridad de la infraestructura de un datacenter: red (análisis de
tráfico real), y —en desarrollo— energía, ambiente y accesos. Cada evento
queda en una bitácora trazable a un control de ISO/IEC 27001 y a su norma
técnica (NFPA / IEEE).

> **Importante:** este proyecto tiene **dos partes**. El **código** (este
> repositorio) y la **infraestructura de red virtualizada** en GNS3, que se
> documenta aparte en **[GUIA_INFRAESTRUCTURA.md](GUIA_INFRAESTRUCTURA.md)**.
> La plataforma no funciona sola: necesita la red que la alimenta. Lee esa
> guía antes de intentar replicar el entorno.

---

## Componentes del código

| Archivo   | Función |
|-----------|---------|
| `main.py` | Aplicación web (FastAPI): páginas, API y tablero. |
| `red.py`  | Analizador de tráfico de red por captura pasiva + inventario. |
| `db.py`   | Base de datos SQLite: bitácora auditable e inventario. |
| `requirements.txt` | Dependencias de Python. |

La base de datos (`bitacora.db`) y el entorno virtual (`venv/`) **no** se
versionan: se generan solos en cada máquina.

---

## Requisitos

- La infraestructura de red montada según **GUIA_INFRAESTRUCTURA.md**
  (GNS3 VM, topología y puente `eth2` en 10.10.10.0/24).
- Python 3.10 o superior dentro de la GNS3 VM.
- La plataforma se ejecuta **dentro de la GNS3 VM**, no en Windows.

---

## Instalación (dentro de la GNS3 VM)

```bash
# 1. Clonar el repositorio
git clone <URL-DE-TU-REPO> plataforma-postal
cd plataforma-postal

# 2. Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecución

El analizador de red necesita permisos de captura, por eso se ejecuta con
`sudo` apuntando al uvicorn del entorno virtual:

```bash
sudo venv/bin/uvicorn main:app --host 192.168.56.101 --port 8000
```

Luego, desde el navegador del equipo anfitrión (Windows):

```
http://192.168.56.101:8000
```

> Ajusta la IP `192.168.56.101` a la de tu GNS3 VM si es distinta.

### Pestañas
- **Inicio** — panel general (dashboard de gráficas, en desarrollo).
- **Red** — analizador de tráfico en vivo y gestión de inventario.
- **Bitácora** — eventos auditables con su control ISO y norma técnica.
- **API** — documentación interactiva de la API (Swagger).

---

## Problemas comunes

| Síntoma | Causa / solución |
|---------|------------------|
| `address already in use` (puerto 8000) | Quedó otro uvicorn corriendo. `sudo pkill -f uvicorn` o `sudo lsof -i :8000` y `sudo kill -9 <PID>`. Detén siempre con **Ctrl+C**, nunca Ctrl+Z. |
| La tabla de Red aparece vacía | Los endpoints (Alpine) no están emitiendo tráfico, o el puente `eth2` no tiene tráfico. Revisa la guía de infraestructura. |
| `scapy no disponible` | Falta instalar scapy en el venv, o no se ejecutó con `sudo`. |
| El navegador no abre el tablero | Verifica que la plataforma escuche en la IP de la VM y que el equipo anfitrión la alcance por TCP. |

---

## Autores
- Gerardo Antonio Ovando Hernández — 9490-21-7
- Mario Andrés Culajay Roldán — 9490-22-5771
- Sergio Enrique Sánchez Sánchez — 9490-21-1077

Universidad Mariano Gálvez de Guatemala — 2026
