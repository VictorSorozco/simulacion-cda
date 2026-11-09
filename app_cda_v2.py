import streamlit as st
import pandas as pd
import datetime as dt
import random
import string
import time
import io
import pulp

st.set_page_config(page_title="CDA Simulación & Optimización Completa", layout="wide", initial_sidebar_state="expanded")

st.markdown('''
<style>
    .main-header { font-size: 26px; font-weight: 800; color: #1E293B; margin-bottom: 0px; }
    .kpi-card { background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%); border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); text-align: center; }
    .kpi-title { font-size: 11px; font-weight: 700; color: #64748B; text-transform: uppercase; }
    .kpi-value { font-size: 22px; font-weight: 800; color: #0F172A; margin-top: 4px; }
    .reloj-card { background: #0F172A; color: #38BDF8; border-radius: 12px; padding: 10px; text-align: center; font-family: 'Courier New', monospace; font-size: 24px; font-weight: bold; }
    .reloj-card small { font-size: 12px; color: #94A3B8; }
    .estacion-box { background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 8px; margin-bottom: 10px; text-align: center; color: #0F172A; }
    .vehiculo-card { background-color: #FFFFFF; border-left: 5px solid #0EA5E9; padding: 6px 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.06); border-radius: 6px; margin-top: 6px; text-align: left; font-size: 13px; color: #0F172A; }
    .fuera-horario { background:#FEF3C7; color:#92400E; border-radius:8px; padding:6px 10px; font-weight:600; text-align:center; margin-top:6px; font-size: 13px;}
</style>
''', unsafe_allow_html=True)

# ------------------------------------------------------------------ CONSTANTES
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
RANGO_TOTAL = {"Moto": (35, 45), "Liviano": (45, 60), "Pesado": (45, 60)}
EMOJI = {"Moto": "🏍️", "Liviano": "🚗", "Pesado": "🚚"}
INCIDENTES = {
    0: ["Falla del equipo de gases", "Calibración del sonómetro", "Vehículo no enciende / prueba repetida"],
    1: ["Documentos incompletos", "Inspección sensorial adicional", "Discrepancia en número de motor/chasis"],
    2: ["Reinspección de frenos", "Falla del banco de suspensión", "Espera del ingeniero por concepto técnico"],
}
ESTACIONES = ["1. Gases / Sonometría", "2. Inspección Sensorial", "3. Mecanizada / Frenos"]
INSPECTORES_DEF = ["Carlos Ramírez", "Andrea Gómez", "Luis Martínez", "Diana Torres", "Jorge Herrera",
                   "Paola Castillo", "Andrés Mejía", "Natalia Ortiz", "Felipe Rojas", "Camila Vargas"]
INGENIEROS_DEF = ["Ing. Sofía Pardo", "Ing. Mauricio León", "Ing. Laura Benítez", "Ing. Daniel Cruz", "Ing. Valentina Ruiz"]
RECEP_DEF = ["Marcela Díaz", "Juan Pablo Soto", "Katherine Mora"]

# ------------------------------------------------------------------ ESTADO GLOBAL
ss = st.session_state
hoy = dt.date.today()
if 'vehiculos' not in ss: ss.vehiculos = []
if 'id_counter' not in ss: ss.id_counter = 1
if 'simulando' not in ss: ss.simulando = False
if 'historial' not in ss: ss.historial = []
if 'apertura_dt' not in ss: ss.apertura_dt = dt.datetime.combine(hoy, dt.time(7, 0))
if 'cierre_dt' not in ss: ss.cierre_dt = dt.datetime.combine(hoy, dt.time(18, 0))
if 'reloj' not in ss: ss.reloj = ss.apertura_dt
if 'dist_activa' not in ss: ss.dist_activa = "Triangular (Probabilística)"
if 'inspectores_activos' not in ss: ss.inspectores_activos = INSPECTORES_DEF
if 'caps' not in ss: ss.caps = (6, 8, 8)
if 'jornada_activa' not in ss: ss.jornada_activa = True
if 'cal_params' not in ss: ss.cal_params = (20, 0.6, 10)
if 'inc_params' not in ss: ss.inc_params = (0.12, 15, 60)
if 'msg_opt' not in ss: ss.msg_opt = None

# ------------------------------------------------------------------ SIDEBAR
st.sidebar.title("🎛️ Configuración de la Jornada")

with st.sidebar.expander("📅 Día y horario de operación", expanded=True):
    fecha = st.date_input("Fecha de la jornada", hoy)
    dias_lab = st.multiselect("Días laborales de la semana", DIAS, default=DIAS[:6])
    festivo = st.checkbox("Marcar esta fecha como festivo / no laboral", value=False)
    hora_ap = st.time_input("Hora de apertura (entrada)", dt.time(7, 0), step=900)
    hora_ci = st.time_input("Hora de cierre (última llegada)", dt.time(18, 0), step=900)
    nombre_dia = DIAS[fecha.weekday()]
    laborable = (nombre_dia in dias_lab) and not festivo
    if laborable:
        st.success(f"{nombre_dia} {fecha:%d/%m/%Y}: día laborable")
    else:
        st.error(f"{nombre_dia} {fecha:%d/%m/%Y}: NO se labora")
    if hora_ci <= hora_ap:
        st.error("El cierre debe ser posterior a la apertura.")

with st.sidebar.expander("👥 Personal (un nombre por línea)"):
    txt_insp = st.text_area("Inspectores", "\n".join(INSPECTORES_DEF), height=180)
    txt_ing = st.text_area("Ingenieros", "\n".join(INGENIEROS_DEF), height=100)
    txt_rec = st.text_area("Recepcionistas", "\n".join(RECEP_DEF), height=80)
lista_insp = [x.strip() for x in txt_insp.splitlines() if x.strip()]
lista_ing = [x.strip() for x in txt_ing.splitlines() if x.strip()]
lista_rec = [x.strip() for x in txt_rec.splitlines() if x.strip()] or ["Recepción"]

with st.sidebar.expander("🏗️ Capacidades de pistas"):
    cap1 = st.number_input("Pista 1 (Motos)", 1, 20, 6)
    cap2 = st.number_input("Pista 2 (Livianos)", 1, 20, 8)
    cap3 = st.number_input("Pista 3 (Mixta, pesado = 2 cupos)", 2, 20, 8)

with st.sidebar.expander("🎲 Llegadas y tiempos"):
    rango = st.slider("Cantidad de vehículos del día (rango aleatorio)", 1, 300, (30, 100))
    patron = st.selectbox("Patrón de llegadas", ["Uniforme", "Con picos (mañana y tarde)"])
    dist = st.selectbox("Distribución del tiempo total por vehículo",
                        ["Triangular (Probabilística)", "Uniforme en el rango", "Fija (punto medio)"], index=0)

with st.sidebar.expander("⭐ Satisfacción del cliente"):
    min_por_estrella = st.slider("Minutos de espera en fila que le quitan 1 estrella", 5, 60, 20)
    min_por_demora = st.slider("Minutos de demora extra en pista que le quitan 1 estrella", 5, 60, 10)
    ruido_cal = st.slider("Variabilidad de la opinión del cliente (0 = igual para todos)", 0.0, 1.5, 0.6, 0.1)

with st.sidebar.expander("⚠️ Contratiempos (demoras sobre el promedio)"):
    prob_inc = st.slider("% de vehículos con contratiempo", 0, 50, 12)
    rango_extra = st.slider("Minutos extra por contratiempo (mín – máx)", 5, 120, (15, 60))


def tiempos_estaciones(tipo, distribucion):
    lo, hi = RANGO_TOTAL[tipo]
    mid = (lo + hi) / 2
    if distribucion.startswith("Fija"):
        total, pesos = mid, [1, 1, 1]
    else:
        total = random.uniform(lo, hi) if distribucion.startswith("Uniforme") else random.triangular(lo, hi, mid)
        pesos = [random.uniform(0.28, 0.38) for _ in range(3)]
    sp = sum(pesos)
    tiempos = [round(total * p / sp, 1) for p in pesos]
    p_inc, e_min, e_max = ss.inc_params
    if random.random() < p_inc:
        est = random.randrange(3)
        extra = round(random.uniform(e_min, e_max), 1)
        tiempos[est] = round(tiempos[est] + extra, 1)
        return tiempos, (f"{random.choice(INCIDENTES[est])} (Est. {est + 1})", extra)
    return tiempos, (None, 0.0)


def calificar(espera_min, tiempo_pista, tipo, min_x_estrella, ruido, min_x_demora):
    demora = max(0.0, tiempo_pista - RANGO_TOTAL[tipo][1])
    puntaje = 5 - espera_min / min_x_estrella - demora / min_x_demora + random.gauss(0, ruido)
    return int(min(5, max(0, round(puntaje))))


def estrellas(n):
    return "★" * n + "☆" * (5 - n)


def nueva_placa():
    return f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{''.join(random.choices(string.digits, k=3))}"


def crear_vehiculo(placa, tipo, llegada, estado, recep):
    tiempos, inc = tiempos_estaciones(tipo, ss.dist_activa)
    v = {
        'id': ss.id_counter, 'placa': placa, 'tipo': tipo, 'llegada': llegada,
        'estado': estado, 'pista': None, 'inicio': None, 'fin': None,
        'inspector': None, 'recepcionista': recep,
        'tiempos_estaciones': tiempos, 'incidente': inc[0], 'min_extra': inc[1],
        'estacion_actual': 0, 'calificacion': None,
    }
    ss.id_counter += 1
    ss.vehiculos.append(v)


def generar_jornada():
    ss.apertura_dt = dt.datetime.combine(fecha, hora_ap)
    ss.cierre_dt = dt.datetime.combine(fecha, hora_ci)
    ss.reloj = ss.apertura_dt
    ss.vehiculos, ss.historial, ss.id_counter = [], [], 1
    ss.simulando = False
    ss.dist_activa = dist
    ss.cal_params = (min_por_estrella, ruido_cal, min_por_demora)
    ss.inc_params = (prob_inc / 100, rango_extra[0], rango_extra[1])
    ss.inspectores_activos = lista_insp
    ss.caps = (cap1, cap2, cap3)
    ss.jornada_activa = laborable
    ss.msg_opt = None
    if not laborable:
        return
    span = (ss.cierre_dt - ss.apertura_dt).total_seconds()
    n = random.randint(rango[0], rango[1])
    segundos = []
    while len(segundos) < n:
        if patron.startswith("Con picos"):
            s = random.gauss(random.choice([0.25, 0.7]) * span, span * 0.12)
        else:
            s = random.uniform(0, span)
        if 0 <= s < span:
            segundos.append(s)
    for s in sorted(segundos):
        crear_vehiculo(nueva_placa(), random.choice(["Moto", "Liviano", "Pesado"]),
                       ss.apertura_dt + dt.timedelta(seconds=int(s)), 'Por llegar', random.choice(lista_rec))


if st.sidebar.button("📅 Generar jornada (aplica horario y llegadas)", type="primary", use_container_width=True):
    generar_jornada()
    st.rerun()

# ------------------------------------------------------------------ MODELO MATEMÁTICO MILP (FLOW SHOP)
def optimizar_fila_actual():
    """Toma los vehículos en estado 'En Espera' y optimiza su orden de atención usando un modelo MILP (Flow Shop)"""
    en_espera = [v for v in ss.vehiculos if v['estado'] == 'En Espera']
    
    if len(en_espera) < 2:
        return False, "⚠️ Se necesitan al menos 2 vehículos en fila para optimizar."
    
    lote_a_optimizar = en_espera[:8]
    vehiculos_ids = [v['id'] for v in lote_a_optimizar]
    estaciones = [1, 2, 3]
    
    p = {}
    for v in lote_a_optimizar:
        p[v['id']] = {
            1: v['tiempos_estaciones'][0],
            2: v['tiempos_estaciones'][1],
            3: v['tiempos_estaciones'][2]
        }
        
    M = 10000 
    
    prob = pulp.LpProblem("Secuenciacion_Fila_CDA", pulp.LpMinimize)
    
    # Sintaxis de variables compatible con todas las versiones de PuLP
    C = {(i, k): pulp.LpVariable(f"C_{i}_{k}", lowBound=0, cat='Continuous') 
         for i in vehiculos_ids for k in estaciones}
         
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat='Binary') 
         for i in vehiculos_ids for j in vehiculos_ids}
         
    Cmax = pulp.LpVariable("Cmax", lowBound=0, cat='Continuous')
    
    # Función Objetivo
    prob += Cmax
    
    # Restricciones
    for i in vehiculos_ids:
        prob += Cmax >= C[(i, 3)]
        prob += C[(i, 1)] >= p[i][1]
        prob += C[(i, 2)] >= C[(i, 1)] + p[i][2]
        prob += C[(i, 3)] >= C[(i, 2)] + p[i][3]
        
    for i in vehiculos_ids:
        for j in vehiculos_ids:
            if i < j:
                for k in estaciones:
                    prob += C[(j, k)] >= C[(i, k)] + p[j][k] - M * (1 - x[(i, j)])
                    prob += C[(i, k)] >= C[(j, k)] + p[i][k] - M * x[(i, j)]
                    
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=30))
    
    if prob.status == 1:
        tiempos_inicio = {i: pulp.value(C[(i, 1)]) - p[i][1] for i in vehiculos_ids}
        orden_optimo_ids = sorted(tiempos_inicio.keys(), key=lambda i: tiempos_inicio[i])
        
        tiempo_base = ss.reloj
        for idx, v_id in enumerate(orden_optimo_ids):
            for v in ss.vehiculos:
                if v['id'] == v_id:
                    v['llegada'] = tiempo_base + dt.timedelta(seconds=idx)
                    break
        
        ss.vehiculos = sorted(ss.vehiculos, key=lambda x: (x['llegada'], x['id']))
        makespan = round(pulp.value(Cmax), 1)
        return True, f"🎯 Fila de {len(lote_a_optimizar)} vehículos reordenada con MILP. Makespan óptimo: {makespan} min."
    else:
        return False, "❌ El solver no encontró solución óptima."

st.sidebar.divider()
st.sidebar.subheader("▶️ Controles de Simulación")
b1, b2 = st.sidebar.columns(2)
with b1:
    if st.button("▶️ Iniciar", use_container_width=True): ss.simulando = True
with b2:
    if st.button("⏸️ Pausar", use_container_width=True): ss.simulando = False

vel = st.sidebar.slider("Velocidad (min simulados / seg real)", 1, 30, 5)
salto = st.sidebar.button("⏩ +30 min manual", use_container_width=True)

st.sidebar.divider()
st.sidebar.subheader("🧠 Modelo de Optimización (IO)")
if st.sidebar.button("⚡ OPTIMIZAR FILA ACTUAL (MILP)", use_container_width=True, type="primary"):
    exito, msg = optimizar_fila_actual()
    ss.msg_opt = (exito, msg)
    st.rerun()

# ------------------------------------------------------------------ LÓGICA DE SIMULACIÓN Y ASIGNACIÓN
def ocupacion():
    ep = [v for v in ss.vehiculos if v['estado'] == 'En Pista']
    c1 = sum(1 for v in ep if v['pista'] == 1)
    c2 = sum(1 for v in ep if v['pista'] == 2)
    c3 = sum(2 if v['tipo'] == 'Pesado' else 1 for v in ep if v['pista'] == 3)
    return c1, c2, c3, len(ep)


def procesar():
    now = ss.reloj
    for v in ss.vehiculos:
        if v['estado'] == 'Por llegar' and v['llegada'] <= now:
            v['estado'] = 'En Espera'
        elif v['estado'] == 'En Pista':
            el = (now - v['inicio']).total_seconds() / 60
            total = sum(v['tiempos_estaciones'])
            if el >= total:
                v['estado'] = 'Finalizado'
                v['fin'] = v['inicio'] + dt.timedelta(minutes=total)
                v['estacion_actual'] = 0
                v['calificacion'] = calificar(mins(v['llegada'], v['inicio']), total, v['tipo'],
                                              ss.cal_params[0], ss.cal_params[1], ss.cal_params[2])
            else:
                acum, est = 0, 1
                for t in v['tiempos_estaciones']:
                    acum += t
                    if el < acum:
                        break
                    est += 1
                v['estacion_actual'] = min(est, 3)

    c1, c2, c3, _ = ocupacion()
    usados = {v['inspector'] for v in ss.vehiculos if v['estado'] == 'En Pista'}
    libres = [n for n in ss.inspectores_activos if n not in usados]
    k1, k2, k3 = ss.caps
    cola = sorted([v for v in ss.vehiculos if v['estado'] == 'En Espera'], key=lambda x: (x['llegada'], x['id']))
    for v in cola:
        if not libres:
            break
        pista = None
        if v['tipo'] == 'Moto' and c1 < k1:
            pista = 1; c1 += 1
        elif v['tipo'] == 'Liviano':
            if c2 < k2: pista = 2; c2 += 1
            elif c3 < k3: pista = 3; c3 += 1
        elif v['tipo'] == 'Pesado' and c3 + 2 <= k3:
            pista = 3; c3 += 2
        if pista:
            v['pista'] = pista
            v['inspector'] = libres.pop(0)
            v['inicio'] = now
            v['estado'] = 'En Pista'
            v['estacion_actual'] = 1


def avanzar(minutos):
    for _ in range(minutos):
        ss.reloj += dt.timedelta(minutes=1)
        procesar()
    c1, c2, c3, n = ocupacion()
    ss.historial.append({
        "Hora": ss.reloj,
        "En Espera": sum(1 for v in ss.vehiculos if v['estado'] == 'En Espera'),
        "Inspectores Ocupados": n,
        "Utilización Pista 1 (%)": c1 / ss.caps[0] * 100,
        "Utilización Pista 2 (%)": c2 / ss.caps[1] * 100,
        "Utilización Pista 3 (%)": c3 / ss.caps[2] * 100,
    })


def jornada_terminada():
    if not ss.vehiculos or ss.reloj < ss.cierre_dt:
        return False
    return all(v['estado'] == 'Finalizado' for v in ss.vehiculos)


fmt = lambda d: d.strftime("%I:%M %p") if d else "-"
mins = lambda a, b: (b - a).total_seconds() / 60

if salto and not jornada_terminada():
    avanzar(30)

# ------------------------------------------------------------------ CABECERA / KPIs
st.markdown('<div class="main-header">🛡️ CDA Control Center — Simulación & Optimización MILP</div>', unsafe_allow_html=True)

if ss.msg_opt:
    exito, msg = ss.msg_opt
    if exito:
        st.success(msg)
    else:
        st.warning(msg)

if not ss.jornada_activa:
    st.warning("La fecha seleccionada no es laborable. Cambia la fecha o los días laborales y pulsa «Generar jornada».")

V = ss.vehiculos
llegados = [v for v in V if v['estado'] != 'Por llegar']
en_espera = [v for v in V if v['estado'] == 'En Espera']
en_pista = [v for v in V if v['estado'] == 'En Pista']
final = [v for v in V if v['estado'] == 'Finalizado']
por_llegar = [v for v in V if v['estado'] == 'Por llegar']
w_prom = sum(mins(v['llegada'], v['fin']) for v in final) / len(final) if final else 0
espera_prom = sum(mins(v['llegada'], v['inicio']) for v in final) / len(final) if final else 0

cals = [v['calificacion'] for v in final if v['calificacion'] is not None]
cal_prom = sum(cals) / len(cals) if cals else None
k = st.columns(8)
cards = [("👷 Inspectores activos", f"{len(en_pista)} / {len(ss.inspectores_activos)}"),
         ("🚦 Por llegar", len(por_llegar)),
         ("⏳ En fila", len(en_espera)),
         ("🔧 En pista", len(en_pista)),
         ("✅ Finalizados", f"{len(final)} / {len(V)}"),
         ("⏱️ Espera prom.", f"{int(espera_prom)} min"),
         ("⏱️ Total sistema prom.", f"{int(w_prom)} min"),
         ("⭐ Satisfacción prom.", f"{cal_prom:.1f} / 5" if cal_prom is not None else "-")]
for col, (t, val) in zip(k, cards):
    col.markdown(f'<div class="kpi-card"><div class="kpi-title">{t}</div><div class="kpi-value">{val}</div></div>', unsafe_allow_html=True)

kk = st.columns([3, 1])
kk[0].caption(f"📅 {ss.reloj:%A %d/%m/%Y} · Horario: {fmt(ss.apertura_dt)} – {fmt(ss.cierre_dt)} "
              f"· Solver MILP: PuLP / CBC · Ingenieros: {', '.join(lista_ing)}")
extra = '<div class="fuera-horario">Cerrado a nuevas llegadas: se atiende lo pendiente</div>' if ss.reloj >= ss.cierre_dt and not jornada_terminada() else ""
kk[1].markdown(f'<div class="reloj-card">🕒 {ss.reloj:%I:%M %p}{extra}</div>', unsafe_allow_html=True)

if jornada_terminada():
    ss.simulando = False
    ultimo = max(v['fin'] for v in V)
    extra_min = max(0, int(mins(ss.cierre_dt, ultimo)))
    st.success(f"✅ Todos los vehículos salieron. Última salida: {fmt(ultimo)}"
               + (f" ({extra_min} min después del cierre)." if extra_min else "."))

# ------------------------------------------------------------------ TABS
tab_mapa, tab_reg, tab_an, tab_sat, tab_log = st.tabs(["📍 Mapa de Pistas", "📥 Registro Manual", "📈 Analytics", "⭐ Satisfacción", "📊 Registro y Exportación"])

with tab_mapa:
    c1, c2, c3, _ = ocupacion()
    m = st.columns(3)
    m[0].metric("Ocupación Pista 1", f"{c1} / {ss.caps[0]}")
    m[1].metric("Ocupación Pista 2", f"{c2} / {ss.caps[1]}")
    m[2].metric("Ocupación Pista 3", f"{c3} / {ss.caps[2]}", help="Pesado = 2 cupos")
    pistas = {1: ("Pista 1 — Motos 🏍️", "#0284C7"), 2: ("Pista 2 — Livianos 🚗", "#EA580C"), 3: ("Pista 3 — Mixta 🚚", "#16A34A")}
    cols = st.columns(3)
    for (np_, (tit, color)), col in zip(pistas.items(), cols):
        with col:
            st.markdown(f'<div style="background:{color};color:white;padding:8px;border-radius:8px;text-align:center;font-weight:bold;">{tit}</div><br>', unsafe_allow_html=True)
            en_p = [v for v in en_pista if v['pista'] == np_]
            for i, nombre in enumerate(ESTACIONES, start=1):
                html = f'<div class="estacion-box"><strong style="color:{color};">{nombre}</strong>'
                aqui = [v for v in en_p if v['estacion_actual'] == i]
                if not aqui:
                    html += '<br><small><i>Libre</i></small>'
                for v in aqui:
                    el = mins(v['inicio'], ss.reloj)
                    previo = sum(v['tiempos_estaciones'][:i - 1])
                    t_est = v['tiempos_estaciones'][i - 1]
                    html += (f'<div class="vehiculo-card"><b>{EMOJI[v["tipo"]]} {v["placa"]}</b> · {v["tipo"]}<br>'
                             f'👷 {v["inspector"]}<br>'
                             f'⏱️ En estación: {min(el - previo, t_est):.0f} / {t_est:.0f} min<br>'
                             f'🕓 Total en pista: {el:.0f} / {sum(v["tiempos_estaciones"]):.0f} min<br>'
                             f'⌛ Esperó en fila: {mins(v["llegada"], v["inicio"]):.0f} min'
                             + (f'<br>⚠️ <b>{v["incidente"]}</b> · +{v["min_extra"]:.0f} min' if v['incidente'] else '')
                             + '</div>')
                st.markdown(html + '</div>', unsafe_allow_html=True)

    st.subheader(f"⏳ Fila de espera ({len(en_espera)})")
    if en_espera:
        st.dataframe(pd.DataFrame([{
            "ID": v['id'],
            "Placa": v['placa'], "Tipo": v['tipo'], "Llegó": fmt(v['llegada']),
            "Estación 1 (min)": v['tiempos_estaciones'][0],
            "Estación 2 (min)": v['tiempos_estaciones'][1],
            "Estación 3 (min)": v['tiempos_estaciones'][2],
            "Lleva esperando (min)": round(mins(v['llegada'], ss.reloj), 1)}
            for v in sorted(en_espera, key=lambda x: (x['llegada'], x['id']))]), use_container_width=True, hide_index=True)
    else:
        st.caption("Sin vehículos en fila.")

with tab_reg:
    st.subheader("Registro manual (llega en el instante actual del reloj)")
    cm = st.columns(3)
    for i, col in enumerate(cm):
        with col, st.container(border=True):
            rec = lista_rec[i % len(lista_rec)]
            st.write(f"**{rec}**")
            p = st.text_input("Placa", key=f"mp{i}", placeholder="ABC-123")
            t = st.selectbox("Tipo", ["Moto", "Liviano", "Pesado"], key=f"mt{i}")
            if st.button("Ingresar", key=f"mb{i}", type="primary", use_container_width=True):
                if not ss.jornada_activa:
                    st.error("Día no laborable.")
                elif ss.reloj >= ss.cierre_dt:
                    st.error("Fuera de horario: no se reciben más vehículos.")
                elif p:
                    crear_vehiculo(p.upper(), t, ss.reloj, 'En Espera', rec)
                    procesar()
                    st.rerun()

with tab_an:
    if ss.historial:
        dfh = pd.DataFrame(ss.historial).set_index("Hora")
        a, b = st.columns(2)
        a.write("**Fila de espera e inspectores ocupados**")
        a.line_chart(dfh[["Inspectores Ocupados", "En Espera"]])
        b.write("**Utilización por pista (%)**")
        b.line_chart(dfh[["Utilización Pista 1 (%)", "Utilización Pista 2 (%)", "Utilización Pista 3 (%)"]])
    else:
        st.info("Inicia la simulación para ver las gráficas.")
    if V:
        st.write("**Llegadas por hora**")
        por_hora = pd.Series([v['llegada'].strftime("%H:00") for v in V]).value_counts().sort_index()
        st.bar_chart(por_hora)
        if final:
            st.write("**Carga por inspector (vehículos atendidos)**")
            st.bar_chart(pd.Series([v['inspector'] for v in final]).value_counts())

with tab_sat:
    st.subheader("⭐ Calificación de los clientes al salir (0 = mala, 5 = buena)")
    if not final:
        st.info("Los clientes califican al terminar su revisión. Aún no ha salido ninguno.")
    else:
        buenas = sum(1 for c in cals if c >= 3)
        a1, a2, a3 = st.columns(3)
        a1.metric("Promedio", f"{cal_prom:.2f} / 5")
        a2.metric("Atención buena (3-5 ★)", f"{buenas / len(cals) * 100:.0f}%")
        a3.metric("Atención mala (0-2 ★)", f"{(len(cals) - buenas) / len(cals) * 100:.0f}%")
        dist_cal = pd.Series(cals).value_counts().reindex(range(6), fill_value=0)
        dist_cal.index = [f"{i} ★" for i in dist_cal.index]
        st.write("**Distribución de calificaciones**")
        st.bar_chart(dist_cal)
        dfc = pd.DataFrame([{"Tipo": v['tipo'], "Inspector": v['inspector'], "Calificación": v['calificacion'],
                             "Espera (min)": mins(v['llegada'], v['inicio']),
                             "En pista (min)": sum(v['tiempos_estaciones']),
                             "Contratiempo": bool(v['incidente'])} for v in final])
        c1_, c2_ = st.columns(2)
        c1_.write("**Calificación promedio por tipo de vehículo**")
        c1_.bar_chart(dfc.groupby("Tipo")["Calificación"].mean())
        c2_.write("**Calificación promedio por inspector**")
        c2_.bar_chart(dfc.groupby("Inspector")["Calificación"].mean())

with tab_log:
    filas = []
    for v in V:
        if v['estado'] == 'Por llegar':
            continue
        t = v['tiempos_estaciones']
        espera = mins(v['llegada'], ss.reloj) if v['estado'] == 'En Espera' else mins(v['llegada'], v['inicio'])
        sistema = mins(v['llegada'], v['fin']) if v['estado'] == 'Finalizado' else mins(v['llegada'], ss.reloj)
        filas.append({
            "ID": v['id'], "Placa": v['placa'], "Tipo": v['tipo'], "Estado": v['estado'],
            "Pista": f"Pista {v['pista']}" if v['pista'] else "-", "Inspector": v['inspector'] or "-", "Recepcionista": v['recepcionista'],
            "Llegada": fmt(v['llegada']), "Inicio": fmt(v['inicio']), "Salida": fmt(v['fin']),
            "Espera en fila (min)": round(espera, 1),
            "Estación 1 (min)": t[0], "Estación 2 (min)": t[1], "Estación 3 (min)": t[2],
            "Tiempo en pista (min)": round(sum(t), 1),
            "Tiempo total en sistema (min)": round(sistema, 1),
            "Contratiempo": v['incidente'] or "-", "Minutos extra": v['min_extra'],
            "Calificación (0-5)": v['calificacion'],
            "Estrellas": estrellas(v['calificacion']) if v['calificacion'] is not None else "-",
        })
    if filas:
        df = pd.DataFrame(filas)
        st.dataframe(df, use_container_width=True, hide_index=True)
        d1, d2 = st.columns(2)
        d1.download_button("📥 Exportar CSV", df.to_csv(index=False).encode('utf-8-sig'),
                           file_name=f"CDA_{ss.reloj:%Y%m%d}.csv", mime="text/csv")
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w:
                df.to_excel(w, index=False, sheet_name='Vehiculos')
            d2.download_button("📥 Exportar Excel (.xlsx)", buf.getvalue(),
                               file_name=f"CDA_{ss.reloj:%Y%m%d}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            d2.caption("Instala openpyxl para exportar a Excel.")

# ------------------------------------------------------------------ BUCLE
if ss.simulando and not jornada_terminada():
    time.sleep(1)
    avanzar(vel)
    st.rerun()
