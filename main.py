"""
Plataforma de Monitoreo - Operador Postal Designado.
Interfaz de tema claro con analizador de red y gestion de inventario.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

import db
import red

app = FastAPI(title="Plataforma de Monitoreo - Operador Postal")

db.init_db()
red.iniciar()

# CSS comun (tema claro, profesional).
ESTILO = """
:root{
  --bg:#eef2f7; --card:#ffffff; --tinta:#1f2937; --muted:#6b7280;
  --azul:#2563eb; --indigo:#4f46e5; --verde:#16a34a; --rojo:#dc2626;
  --ambar:#d97706; --linea:#e5e7eb;
}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--tinta)}
header{background:linear-gradient(135deg,var(--indigo),var(--azul));color:#fff;padding:18px 28px;box-shadow:0 2px 8px rgba(0,0,0,.15)}
header h1{margin:0;font-size:20px;font-weight:600}
header .sub{opacity:.85;font-size:13px;margin-top:2px}
nav{background:#fff;padding:0 28px;border-bottom:1px solid var(--linea)}
nav a{display:inline-block;padding:12px 16px;color:var(--muted);text-decoration:none;font-size:14px;font-weight:500;border-bottom:3px solid transparent}
nav a:hover{color:var(--azul)}
nav a.activo{color:var(--azul);border-bottom-color:var(--azul)}
main{padding:24px 28px;max-width:1200px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--linea);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:18px 20px;margin-bottom:20px}
.card h2{margin:0 0 14px;font-size:16px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:14px}
th{background:#f8fafc;color:#334155;text-align:left;padding:10px 12px;border-bottom:2px solid var(--linea);font-weight:600}
td{padding:10px 12px;border-bottom:1px solid var(--linea)}
tr:hover td{background:#f9fbff}
tr.noauth td{background:#fef2f2}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600}
.b-verde{background:#dcfce7;color:#166534}
.b-rojo{background:#fee2e2;color:#991b1b}
.b-ambar{background:#fef3c7;color:#92400e}
.b-gris{background:#e5e7eb;color:#374151}
.mono{font-family:ui-monospace,Consolas,monospace;font-size:13px;color:#475569}
input,select{padding:8px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;margin-right:8px}
button{padding:8px 14px;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}
.btn-azul{background:var(--azul);color:#fff}
.btn-rojo{background:#fee2e2;color:#991b1b}
.btn-verde{background:#dcfce7;color:#166534}
.btn-azul:hover{background:#1d4ed8}
.form-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.resumen span{margin-right:16px;color:var(--muted)}
"""

def _shell(titulo, activo, cuerpo, refresco_js=""):
    nav = ""
    for ruta, etq in [("/", "Inicio"), ("/red", "Red"), ("/bitacora", "Bitacora"), ("/docs", "API")]:
        cls = "activo" if ruta == activo else ""
        nav += f'<a class="{cls}" href="{ruta}">{etq}</a>'
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title><style>{ESTILO}</style></head><body>
<header><h1>Plataforma de Monitoreo del Datacenter</h1>
<div class="sub">Operador Postal Designado &middot; Seguridad y Auditoria</div></header>
<nav>{nav}</nav><main>{cuerpo}</main>{refresco_js}</body></html>"""


@app.get("/", response_class=HTMLResponse)
def inicio():
    cuerpo = """
    <div class="card">
      <h2>Bienvenido</h2>
      <p>Plataforma de monitoreo, deteccion y bitacora auditable para la
      infraestructura del datacenter. Usa el menu para ver el analizador de
      red en vivo o la bitacora de eventos.</p>
    </div>"""
    return _shell("Inicio", "/", cuerpo)


@app.get("/salud")
def salud():
    return {"estado": "ok"}


@app.get("/api/eventos")
def api_eventos():
    return db.obtener_eventos()


@app.get("/api/red")
def api_red():
    return red.estado_actual()


@app.get("/api/inventario")
def api_inventario():
    return red.inventario_listar()


@app.post("/api/inventario/agregar")
def api_inv_agregar(ip: str, nombre: str, tipo: str = "otro", switch: str = "SW-CIRC-A"):
    red.agregar(ip.strip(), nombre.strip(), tipo, switch)
    return JSONResponse({"ok": True})


@app.post("/api/inventario/eliminar")
def api_inv_eliminar(ip: str):
    red.eliminar(ip.strip())
    return JSONResponse({"ok": True})


@app.get("/red", response_class=HTMLResponse)
def pagina_red():
    cuerpo = """
    <div class="card">
      <h2>Agregar dispositivo al inventario autorizado</h2>
      <div class="form-row">
        <input id="f-ip" placeholder="IP (ej. 10.10.10.55)" size="16">
        <input id="f-nombre" placeholder="Nombre (ej. CAM-03)" size="14">
        <select id="f-tipo">
          <option value="servidor">servidor</option>
          <option value="camara">camara</option>
          <option value="lectora">lectora</option>
          <option value="otro">otro</option>
        </select>
        <select id="f-switch">
          <option value="SW-CIRC-A">SW-CIRC-A</option>
          <option value="SW-CIRC-B">SW-CIRC-B</option>
        </select>
        <button class="btn-azul" onclick="agregar()">Agregar</button>
      </div>
    </div>

    <div class="card">
      <h2>Analizador de red en vivo <span id="reloj" style="font-weight:400;color:#6b7280;font-size:13px"></span></h2>
      <table>
        <thead><tr>
          <th>Dispositivo</th><th>IP</th><th>MAC</th><th>Switch</th>
          <th>Autorizacion</th><th>Estado</th><th>Ultimo trafico</th><th>Acciones</th>
        </tr></thead>
        <tbody id="tabla"><tr><td colspan="8">Cargando...</td></tr></tbody>
      </table>
      <p style="color:#6b7280;font-size:13px;margin-top:12px;line-height:1.6">
        La plataforma lee el trafico real que llega por eth2. Conecta un equipo con IP fuera del
        inventario y aparecera como <b style="color:#dc2626">NO AUTORIZADO</b>. Apaga
        <b>SW-CIRC-B</b> para ver la cascada PoE. Elimina un dispositivo del inventario y, si sigue
        emitiendo, reaparecera como desconocido.
      </p>
    </div>
    """
    js = """<script>
    function badgeEstado(e){
      if(e==='en_linea') return '<span class="badge b-verde">en linea</span>';
      if(e==='caido') return '<span class="badge b-rojo">caido</span>';
      if(e==='sin_trafico') return '<span class="badge b-gris">sin trafico</span>';
      return '<span class="badge b-gris">'+e+'</span>';
    }
    async function cargar(){
      try{
        const hosts = await (await fetch('/api/red')).json();
        const tb = document.getElementById('tabla');
        if(!hosts.length){ tb.innerHTML='<tr><td colspan="8">Aun no se ve trafico.</td></tr>'; return; }
        tb.innerHTML = hosts.map(h=>{
          const noauth = !h.autorizado;
          const auth = noauth
            ? '<span class="badge b-rojo">NO AUTORIZADO</span>'
            : '<span class="badge b-verde">autorizado</span>';
          const visto = h.visto_hace_seg===null ? '—' : (h.visto_hace_seg+' s');
          let acciones = '';
          if(noauth){
            acciones = '<button class="btn-verde" onclick="autorizar(\\''+h.ip+'\\')">Autorizar</button>';
          }else{
            acciones = '<button class="btn-rojo" onclick="eliminar(\\''+h.ip+'\\',\\''+h.nombre+'\\')">Eliminar</button>';
          }
          return '<tr class="'+(noauth?'noauth':'')+'">'
            +'<td>'+h.nombre+'</td>'
            +'<td>'+h.ip+'</td>'
            +'<td class="mono">'+h.mac+'</td>'
            +'<td>'+h.switch+'</td>'
            +'<td>'+auth+'</td>'
            +'<td>'+badgeEstado(h.estado)+'</td>'
            +'<td>'+visto+'</td>'
            +'<td>'+acciones+'</td></tr>';
        }).join('');
        document.getElementById('reloj').textContent = '(actualizado '+new Date().toLocaleTimeString()+')';
      }catch(e){ console.error(e); }
    }
    async function agregar(){
      const ip=document.getElementById('f-ip').value.trim();
      const nombre=document.getElementById('f-nombre').value.trim();
      const tipo=document.getElementById('f-tipo').value;
      const sw=document.getElementById('f-switch').value;
      if(!ip||!nombre){ alert('IP y nombre son obligatorios'); return; }
      await fetch('/api/inventario/agregar?ip='+encodeURIComponent(ip)+'&nombre='+encodeURIComponent(nombre)+'&tipo='+tipo+'&switch='+sw,{method:'POST'});
      document.getElementById('f-ip').value=''; document.getElementById('f-nombre').value='';
      cargar();
    }
    async function eliminar(ip,nombre){
      if(!confirm('Eliminar '+nombre+' ('+ip+') del inventario?')) return;
      await fetch('/api/inventario/eliminar?ip='+encodeURIComponent(ip),{method:'POST'});
      cargar();
    }
    async function autorizar(ip){
      const nombre=prompt('Nombre para autorizar '+ip+':','EQUIPO');
      if(!nombre) return;
      await fetch('/api/inventario/agregar?ip='+encodeURIComponent(ip)+'&nombre='+encodeURIComponent(nombre)+'&tipo=otro&switch=SW-CIRC-A',{method:'POST'});
      cargar();
    }
    cargar(); setInterval(cargar, 3000);
    </script>"""
    return _shell("Red", "/red", cuerpo, js)


@app.get("/bitacora", response_class=HTMLResponse)
def bitacora():
    eventos = db.obtener_eventos()
    resumen = db.contar_por_severidad()
    badge = {"informativo": "b-gris", "advertencia": "b-ambar", "critico": "b-rojo"}

    filas = ""
    for e in eventos:
        b = badge.get(e["severidad"], "b-gris")
        filas += (
            "<tr>"
            f"<td>{e['id']}</td><td class='mono'>{e['timestamp']}</td><td>{e['modulo']}</td>"
            f"<td>{e['tipo']}</td>"
            f"<td><span class='badge {b}'>{e['severidad']}</span></td>"
            f"<td>{e['descripcion']}</td><td>{e['control_iso'] or ''}</td><td>{e['norma'] or ''}</td>"
            "</tr>"
        )
    if not filas:
        filas = "<tr><td colspan='8'>Sin eventos todavia.</td></tr>"

    resumen_txt = "".join(f"<span>{s}: <b>{t}</b></span>" for s, t in resumen.items()) or "sin eventos"

    cuerpo = f"""
    <div class="card">
      <h2>Bitacora de eventos auditable</h2>
      <div class="resumen" style="margin-bottom:12px">{resumen_txt}</div>
      <table>
        <thead><tr>
          <th>ID</th><th>Fecha y hora</th><th>Modulo</th><th>Tipo</th>
          <th>Severidad</th><th>Descripcion</th><th>Control ISO</th><th>Norma</th>
        </tr></thead>
        <tbody>{filas}</tbody>
      </table>
    </div>"""
    return _shell("Bitacora", "/bitacora", cuerpo)
