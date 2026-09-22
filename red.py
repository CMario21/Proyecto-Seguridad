"""
Modulo de RED: analizador de trafico por captura pasiva en eth2.

Lee los paquetes reales, extrae MAC + IP de cada equipo que habla en la red
y detecta: conexion, dispositivo NO autorizado (IP fuera del inventario),
suplantacion (una IP conocida cambia de MAC), desconexion y cascada PoE.

El INVENTARIO de dispositivos autorizados se guarda en la base de datos y se
puede editar en caliente desde la interfaz (agregar / eliminar). La
clasificacion se calcula en vivo contra el inventario actual, de modo que si
eliminas un dispositivo y sigue emitiendo, aparece como DESCONOCIDO.
"""

import threading
import time

import db

INTERFAZ = "eth2"
UMBRAL_DESCONEXION = 8
INTERVALO_REVISION = 3
IGNORAR_IPS = {None, "", "0.0.0.0", "10.10.10.1"}

# Inventario autorizado en memoria: ip -> {nombre, tipo, switch}
INVENTARIO = {}

# Hosts vistos en vivo: mac -> {mac, ip, primera, ultima, estado}
_hosts = {}
_ip_mac = {}
_lock = threading.Lock()


def recargar_inventario():
    """Carga el inventario desde la base de datos a memoria."""
    global INVENTARIO
    INVENTARIO = {d["ip"]: {"nombre": d["nombre"], "tipo": d["tipo"], "switch": d["switch"]}
                  for d in db.inventario_listar()}


def _clasificar(ip):
    """(nombre, tipo, switch, autorizado) segun el inventario actual."""
    d = INVENTARIO.get(ip)
    if d:
        return d["nombre"], d["tipo"], d["switch"], True
    return f"desconocido ({ip})", "desconocido", "?", False


def _ver_host(mac, ip):
    if ip in IGNORAR_IPS or not mac:
        return
    ahora = time.time()
    with _lock:
        prev = _ip_mac.get(ip)
        if prev and prev != mac:
            db.registrar_evento(
                "red", "suplantacion", "critico",
                f"La IP {ip} cambio de MAC {prev} a {mac} (posible sustitucion de equipo)",
                "7.2", "IEEE 802.1AR",
            )
        _ip_mac[ip] = mac

        if mac not in _hosts:
            _, _, _, autorizado = _clasificar(ip)
            _hosts[mac] = {"mac": mac, "ip": ip, "primera": ahora,
                           "ultima": ahora, "estado": "en_linea"}
            nombre, _, _, _ = _clasificar(ip)
            if not autorizado:
                db.registrar_evento(
                    "red", "dispositivo_no_autorizado", "critico",
                    f"Dispositivo NO autorizado conectado a la red: IP {ip}, MAC {mac}",
                    "7.2", "IEEE 802.1X",
                )
            else:
                db.registrar_evento(
                    "red", "dispositivo_conectado", "informativo",
                    f"Dispositivo conectado: {nombre} (IP {ip}, MAC {mac})",
                    "7.2", "IEEE 802.1X",
                )
        else:
            h = _hosts[mac]
            h["ultima"] = ahora
            if ip and h["ip"] != ip:
                h["ip"] = ip
            if h["estado"] == "caido":
                h["estado"] = "en_linea"
                nombre, _, _, _ = _clasificar(ip)
                db.registrar_evento(
                    "red", "dispositivo_reconectado", "informativo",
                    f"{nombre} (IP {ip}, MAC {mac}) volvio a la red",
                    "7.2", "IEEE 802.1X",
                )


def _iniciar_sniffer():
    try:
        from scapy.all import sniff, ARP, IP, Ether
    except Exception as e:
        print(f"[red] scapy no disponible ({e}); el sniffer no arranca.")
        return

    def procesar(pkt):
        mac = pkt[Ether].src if pkt.haslayer(Ether) else None
        ip = None
        if pkt.haslayer(ARP):
            ip = pkt[ARP].psrc
            mac = mac or pkt[ARP].hwsrc
        elif pkt.haslayer(IP):
            ip = pkt[IP].src
        if mac and ip:
            _ver_host(mac, ip)

    print(f"[red] Analizador de trafico escuchando en {INTERFAZ} ...")
    sniff(iface=INTERFAZ, prn=procesar, store=0)


def _iniciar_evaluador():
    print("[red] Evaluador de desconexiones iniciado.")
    while True:
        time.sleep(INTERVALO_REVISION)
        ahora = time.time()
        caidos = []
        with _lock:
            for mac, h in _hosts.items():
                if h["estado"] == "en_linea" and ahora - h["ultima"] > UMBRAL_DESCONEXION:
                    h["estado"] = "caido"
                    nombre, tipo, switch, autorizado = _clasificar(h["ip"])
                    caidos.append({**h, "nombre": nombre, "switch": switch, "autorizado": autorizado})
        if caidos:
            _reportar_desconexiones(caidos)


def _reportar_desconexiones(caidos):
    total_por_switch = {}
    for d in INVENTARIO.values():
        total_por_switch[d["switch"]] = total_por_switch.get(d["switch"], 0) + 1

    conocidos_caidos = {}
    desconocidos = []
    for h in caidos:
        if h["autorizado"] and h["switch"] != "?":
            conocidos_caidos.setdefault(h["switch"], []).append(h)
        else:
            desconocidos.append(h)

    for sw, lista in conocidos_caidos.items():
        if len(lista) == total_por_switch.get(sw, 0) and total_por_switch.get(sw, 0) > 1:
            nombres = ", ".join(h["nombre"] for h in lista)
            db.registrar_evento(
                "red", "cascada_poe", "critico",
                f"Caida del conmutador {sw}: sin PoE quedaron {nombres}",
                "7.8", "IEEE 802.3bt",
            )
        else:
            for h in lista:
                db.registrar_evento(
                    "red", "dispositivo_desconectado", "advertencia",
                    f"{h['nombre']} (IP {h['ip']}, MAC {h['mac']}) dejo de emitir",
                    "7.8", "IEEE 802.3bt",
                )

    for h in desconocidos:
        db.registrar_evento(
            "red", "dispositivo_desconectado", "informativo",
            f"El equipo no autorizado {h['ip']} (MAC {h['mac']}) dejo de emitir",
            "7.2", "IEEE 802.1X",
        )


# ---------------------- API para el tablero ----------------------
def estado_actual():
    """Vista combinada: hosts vistos + dispositivos del inventario sin trafico."""
    ahora = time.time()
    salida = []
    ips_vistas = set()
    with _lock:
        for h in _hosts.values():
            nombre, tipo, switch, autorizado = _clasificar(h["ip"])
            ips_vistas.add(h["ip"])
            salida.append({
                "mac": h["mac"], "ip": h["ip"], "nombre": nombre, "tipo": tipo,
                "switch": switch, "autorizado": autorizado, "estado": h["estado"],
                "visto_hace_seg": round(ahora - h["ultima"], 1),
            })
    # Dispositivos del inventario que no se han visto (sin trafico).
    for ip, d in INVENTARIO.items():
        if ip not in ips_vistas:
            salida.append({
                "mac": "—", "ip": ip, "nombre": d["nombre"], "tipo": d["tipo"],
                "switch": d["switch"], "autorizado": True, "estado": "sin_trafico",
                "visto_hace_seg": None,
            })
    salida.sort(key=lambda x: (x["autorizado"], x["nombre"]))
    return salida


def inventario_listar():
    return db.inventario_listar()


def agregar(ip, nombre, tipo, switch):
    db.inventario_agregar(ip, nombre, tipo, switch)
    recargar_inventario()
    db.registrar_evento(
        "red", "inventario_alta", "informativo",
        f"Dispositivo agregado al inventario autorizado: {nombre} (IP {ip})",
        "7.2", "IEEE 802.1AR",
    )
    return True


def eliminar(ip):
    """Quita la IP del inventario y limpia sus hosts vistos.
    Si el equipo sigue emitiendo, reaparecera como DESCONOCIDO."""
    d = INVENTARIO.get(ip)
    db.inventario_eliminar(ip)
    recargar_inventario()
    with _lock:
        macs = [m for m, h in _hosts.items() if h["ip"] == ip]
        for m in macs:
            _hosts.pop(m, None)
        _ip_mac.pop(ip, None)
    if d:
        db.registrar_evento(
            "red", "inventario_baja", "advertencia",
            f"Dispositivo retirado del inventario: {d['nombre']} (IP {ip}). "
            f"Si sigue emitiendo se marcara como no autorizado.",
            "7.2", "IEEE 802.1AR",
        )
    return True


def iniciar():
    recargar_inventario()
    threading.Thread(target=_iniciar_sniffer, daemon=True).start()
    threading.Thread(target=_iniciar_evaluador, daemon=True).start()
