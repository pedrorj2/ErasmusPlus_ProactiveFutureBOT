from telethon import TelegramClient, events
from telethon.tl.custom import Button
from datetime import datetime, timedelta
import csv
import os
import unicodedata
import openai
import numpy as np
import re

# ===========================
# CONFIGURACIÓN (config.py)
# ===========================
# En config.py define:
#   api_id = <TU_API_ID_DE_TELEGRAM>
#   api_hash = "<TU_API_HASH_DE_TELEGRAM>"
#   bot_token = "<TU_BOT_TOKEN_DE_TELEGRAM>"
#   openai_api_key = "<TU_API_KEY_DE_OPENAI>"

from config import api_id, api_hash, bot_token, openai_api_key

# ===========================
# INICIALIZAR CLIENTES
# ===========================
client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)
openai.api_key = openai_api_key

# ===========================
# NORMALIZACIÓN DE TEXTO
# ===========================
def normalizar(texto: str) -> str:
    """
    Convierte texto a minúsculas y quita tildes/acentos.
    Ejemplo: "Róterdam" -> "rotterdam"
    """
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

# ===========================
# CARGAR PROYECTOS DESDE CSV (fechas en ISO)
# ===========================
def cargar_todos_los_proyectos(archivo='erasmus_projects.csv'):
    """
    Lee un CSV con columnas:
      pais,ciudad,titulo,descripcion,fecha_inicio,fecha_fin,
      requisitos,gastos_cubiertos,contacto,enlace,deadline
    (fechas en formato ISO YYYY-MM-DD).
    Devuelve lista de diccionarios con:
      - texto (str)
      - fecha_inicio, fecha_fin, deadline como datetime.date o None
    """
    proyectos = []
    if not os.path.exists(archivo):
        return proyectos

    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for fila in reader:
            try:
                fecha_ini = datetime.strptime(fila['fecha_inicio'], '%Y-%m-%d').date()
            except Exception:
                fecha_ini = None
            try:
                fecha_fin = datetime.strptime(fila['fecha_fin'], '%Y-%m-%d').date()
            except Exception:
                fecha_fin = None
            try:
                deadline = datetime.strptime(fila['deadline'], '%Y-%m-%d').date()
            except Exception:
                deadline = None

            proyectos.append({
                'pais': fila['pais'].strip(),
                'ciudad': fila['ciudad'].strip(),
                'titulo': fila['titulo'].strip(),
                'descripcion': fila['descripcion'].strip(),
                'fecha_inicio': fecha_ini,
                'fecha_fin': fecha_fin,
                'requisitos': fila.get('requisitos', '').strip(),
                'gastos_cubiertos': fila.get('gastos_cubiertos', '').strip(),
                'contacto': fila.get('contacto', '').strip(),
                'enlace': fila.get('enlace', '').strip(),
                'deadline': deadline
            })
    return proyectos

# ===========================
# FORMATEAR PROYECTO PARA MENSAJE
# ===========================
def formatear_proyecto(p, mostrar_dias_deadline=False):
    """
    Devuelve un texto HTML con emojis y negritas
    para mostrar la información del proyecto 'p'.
    """
    texto = f"📌 <b>{p['titulo']}</b>\n\n"
    texto += f"🌍 <b>País:</b> {p['pais']}    📌 <b>Ciudad:</b> {p['ciudad']}\n"

    if p['fecha_inicio']:
        inicio = p['fecha_inicio'].strftime("%d/%m/%Y")
    else:
        inicio = "-"
    if p['fecha_fin']:
        fin = p['fecha_fin'].strftime("%d/%m/%Y")
    else:
        fin = "-"
    texto += f"📅 <b>Inicio:</b> {inicio}    ⏳ <b>Fin:</b> {fin}\n\n"

    if p['descripcion']:
        texto += f"📝 <b>Descripción:</b>\n{p['descripcion']}\n\n"
    if p['requisitos']:
        texto += f"✅ <b>Requisitos:</b>\n{p['requisitos']}\n\n"
    if p['gastos_cubiertos']:
        texto += f"💶 <b>Gastos cubiertos:</b>\n{p['gastos_cubiertos']}\n\n"
    if p['contacto']:
        texto += f"📧 <b>Contacto:</b> {p['contacto']}\n"
    if p['enlace']:
        texto += f"🔗 <b>Enlace:</b> {p['enlace']}\n"

    if p['deadline']:
        texto += f"\n⏰ <b>Deadline:</b> {p['deadline'].strftime('%d/%m/%Y')}"
        if mostrar_dias_deadline:
            dias_rest = (p['deadline'] - datetime.now().date()).days
            if dias_rest >= 0:
                texto += f"  (<b>{dias_rest} días restantes</b>)"
        texto += "\n"

    return texto

# ===========================
# FILTRADOS MANUALES
# ===========================
MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]
MESES_NORMAL = [normalizar(m) for m in MESES_ES]

def obtener_lista_paises(proyectos):
    """Retorna lista ordenada de países únicos en los proyectos."""
    return sorted({p['pais'] for p in proyectos})

def obtener_lista_ciudades(proyectos):
    """Retorna lista ordenada de ciudades únicas en los proyectos."""
    return sorted({p['ciudad'] for p in proyectos})

def filtrar_por_pais(proyectos, pais):
    """
    Filtra proyectos donde p['pais'] == pais.
    Ordena por fecha_inicio ascendente.
    """
    r = [p for p in proyectos if p['pais'] == pais]
    r.sort(key=lambda x: x['fecha_inicio'] or datetime.max.date())
    return r

def filtrar_por_ciudad(proyectos, ciudad):
    """
    Filtra proyectos donde p['ciudad'] == ciudad.
    Ordena por fecha_inicio ascendente.
    """
    r = [p for p in proyectos if p['ciudad'] == ciudad]
    r.sort(key=lambda x: x['fecha_inicio'] or datetime.max.date())
    return r

def filtrar_por_mes(proyectos, mes_norm):
    """
    Filtra proyectos cuyo mes de 'fecha_inicio' coincide con mes_norm (sin tildes).
    Ordena por fecha_inicio.
    """
    try:
        idx_mes = MESES_NORMAL.index(mes_norm) + 1
    except ValueError:
        return []
    r = []
    for p in proyectos:
        if p['fecha_inicio'] and p['fecha_inicio'].month == idx_mes:
            r.append(p)
    r.sort(key=lambda x: x['fecha_inicio'])
    return r

def filtrar_por_rango(proyectos, inicio, fin):
    """
    Filtra proyectos cuya 'fecha_inicio' está entre inicio y fin inclusive.
    Ordena por fecha_inicio.
    """
    r = []
    for p in proyectos:
        if p['fecha_inicio'] and inicio <= p['fecha_inicio'] <= fin:
            r.append(p)
    r.sort(key=lambda x: x['fecha_inicio'])
    return r

def filtrar_deadline_proxima(proyectos, dias=14):
    """
    Retorna proyectos cuya 'deadline' esté entre hoy y hoy+dias.
    Ordena por deadline ascendente.
    """
    hoy = datetime.now().date()
    r = []
    for p in proyectos:
        if p['deadline']:
            diff = (p['deadline'] - hoy).days
            if 0 <= diff <= dias:
                r.append(p)
    r.sort(key=lambda x: x['deadline'])
    return r

# ===========================
# BÚSQUEDA SEMÁNTICA CON EMBEDDINGS
# ===========================
def calcular_embeds_proyectos(proyectos):
    """
    Calcula y devuelve una lista de embeddings para cada proyecto,
    usando 'Título + Descripción' como texto fuente.
    """
    textos = []
    for p in proyectos:
        txt = f"{p['titulo']}. {p['descripcion']}"
        textos.append(txt)

    resp = openai.embeddings.create(model="text-embedding-3-small", input=textos)
    embeddings = [np.array(d.embedding) for d in resp.data]
    return embeddings

def buscar_proyectos_semantico(query, proyectos, embeddings_proyectos, top_k=5):
    """
    Dada una consulta en lenguaje natural, calcula su embedding y
    obtiene las distancias coseno con los embeddings de proyectos.
    Devuelve los índices de los 'top_k' proyectos más similares.
    """
    resp = openai.embeddings.create(model="text-embedding-3-small", input=[query])
    embed_query = np.array(resp.data[0].embedding)

    sims = []
    for idx, emb_p in enumerate(embeddings_proyectos):
        cos = np.dot(embed_query, emb_p) / (np.linalg.norm(embed_query) * np.linalg.norm(emb_p))
        sims.append((cos, idx))

    sims.sort(reverse=True, key=lambda x: x[0])
    resultados = [idx for cos, idx in sims if cos >= 0.7]
    if not resultados:
        resultados = [idx for _, idx in sims[:top_k]]
    else:
        resultados = resultados[:top_k]
    return resultados

# ===========================
# CONTEXTO DE NAVEGACIÓN POR USUARIO
# ===========================
# Guardamos para cada user_id un dict con {'modo': <modo>, 'lista': <lista_filtrada>}.
# Además, almacenamos los embeddings de proyectos en memoria.
client._contexto = getattr(client, '_contexto', {})
client._embeddings = None  # Aquí cargaremos embeddings al arrancar

# ===========================
# INICIALIZAR EMBEDDINGS (al arrancar el bot)
# ===========================
@client.on(events.NewMessage(pattern='/start'))
async def initialize_and_start(event):
    """
    Cuando alguien envía /start, nos aseguramos de cargar los embeddings
    si aún no se han calculado, para usarlos luego en búsquedas semánticas.
    """
    user_id = str(event.sender_id)
    if client._embeddings is None:
        proyectos = cargar_todos_los_proyectos()
        client._embeddings = calcular_embeds_proyectos(proyectos)

    client._contexto[user_id] = None
    botones = [
        [Button.inline('🌍 Buscar por país', 'menu_paises')],
        [Button.inline('📅 Buscar por mes', 'menu_meses')],
        [Button.inline('📆 Buscar entre fechas', 'menu_rango')],
        [Button.inline('⏳ Deadline próxima', 'menu_deadline')]
    ]
    await event.respond(
        '¡Hola! Este bot te ayuda a encontrar proyectos Erasmus.\n\n'
        'Puedes usar los botones de abajo.\n'
        'O bien, escribe tu consulta en lenguaje natural, por ejemplo:\n'
        '"Busco un proyecto en Alemania a finales de julio que se centre en tecnología o innovación digital"\n',
        buttons=botones
    )

# ===========================
# HANDLER DE MENSAJES DE TEXTO (NLP + FILTROS EN ORDEN)
# ===========================
@client.on(events.NewMessage)
async def texto_libre(event):
    if event.out:
        return
    texto_original = event.text.strip()
    if texto_original.startswith('/'):
        return

    user_id = str(event.sender_id)
    proyectos = cargar_todos_los_proyectos()
    norm = normalizar(texto_original)

    # Preparamos mapas de países y ciudades normalizadas → reales
    lista_paises = obtener_lista_paises(proyectos)
    mapa_paises_norm = {normalizar(p): p for p in lista_paises}
    lista_ciudades = obtener_lista_ciudades(proyectos)
    mapa_ciudades_norm = {normalizar(c): c for c in lista_ciudades}

    # 1) Detectar país o ciudad
    pais_detectado = None
    for p_norm, p_real in mapa_paises_norm.items():
        if p_norm in norm.split():
            pais_detectado = p_real
            break

    ciudad_detectada = None
    for c_norm, c_real in mapa_ciudades_norm.items():
        if c_norm in norm.split():
            ciudad_detectada = c_real
            break

    # 2) Detectar mes en español
    mes_detectado = None
    for m_norm, m_real in zip(MESES_NORMAL, MESES_ES):
        if m_norm in norm:
            mes_detectado = m_real
            break

    # 3) Detectar rango de fechas YYYY-MM-DD (si hay al menos 2 coincidencias)
    fechas = re.findall(r'(\d{4}-\d{2}-\d{2})', texto_original)
    rango_inicio = rango_fin = None
    if len(fechas) >= 2:
        try:
            rango_inicio = datetime.strptime(fechas[0], '%Y-%m-%d').date()
            rango_fin = datetime.strptime(fechas[1], '%Y-%m-%d').date()
        except Exception:
            rango_inicio = rango_fin = None

    # 4) Extraer palabras clave restantes (todo lo que no sea país/ciudad/mes/fechas)
    texto_sin_pm = norm
    if pais_detectado:
        texto_sin_pm = texto_sin_pm.replace(normalizar(pais_detectado), "")
    if ciudad_detectada:
        texto_sin_pm = texto_sin_pm.replace(normalizar(ciudad_detectada), "")
    if mes_detectado:
        texto_sin_pm = texto_sin_pm.replace(normalizar(mes_detectado), "")
    for f in fechas:
        texto_sin_pm = texto_sin_pm.replace(f, "")
    palabras = [w for w in re.findall(r'\w+', texto_sin_pm) if len(w) >= 3]

    # ======================================================
    # ORDEN DE FILTRADO:
    # 1) Fechas + País/Ciudad
    # 2) Fechas solamente
    # 3) País/Ciudad + Mes
    # 4) País/Ciudad solo o Mes solo
    # 5) Embeddings (semántico) dentro del subconjunto manual si hay palabras clave,
    #    o en toda la base si no hay filtrado manual.
    # ======================================================

    # ---------------------------------
    # 1) Fechas + País/Ciudad
    # ---------------------------------
    if rango_inicio and rango_fin and (pais_detectado or ciudad_detectada):
        if pais_detectado:
            base = filtrar_por_pais(proyectos, pais_detectado)
        else:
            base = filtrar_por_ciudad(proyectos, ciudad_detectada)

        # Filtrar por rango sobre la base
        filtrados = [p for p in base if p['fecha_inicio'] and rango_inicio <= p['fecha_inicio'] <= rango_fin]
        filtrados.sort(key=lambda x: x['fecha_inicio'] or datetime.max.date())

        # Si existen palabras clave, aplicar búsqueda semántica sobre este subconjunto
        if palabras and filtrados:
            textos_sub = [f"{p['titulo']}. {p['descripcion']}" for p in filtrados]
            resp = openai.embeddings.create(model="text-embedding-3-small", input=textos_sub)
            embeds_sub = [np.array(d.embedding) for d in resp.data]

            resp_q = openai.embeddings.create(model="text-embedding-3-small", input=[" ".join(palabras)])
            embed_q = np.array(resp_q.data[0].embedding)

            sims = []
            for idx, emb_p in enumerate(embeds_sub):
                cos = np.dot(embed_q, emb_p) / (np.linalg.norm(embed_q) * np.linalg.norm(emb_p))
                sims.append((cos, idx))
            sims.sort(reverse=True, key=lambda x: x[0])
            indices_sem = [idx for cos, idx in sims if cos >= 0.7]
            if not indices_sem:
                indices_sem = [idx for _, idx in sims[:5]]

            resultados = [filtrados[i] for i in indices_sem]
            client._contexto[user_id] = {'modo': 'rango_sem', 'lista': resultados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_rango_sem_{i}')]
                for i, p in enumerate(resultados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(
                f"Resultados semánticos en {pais_detectado or ciudad_detectada} entre {fechas[0]} y {fechas[1]}:",
                buttons=botones
            )
            return

        # Si no hay palabras clave, devolvemos la lista completa
        if filtrados:
            client._contexto[user_id] = {'modo': 'rango', 'lista': filtrados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_rango_{i}')]
                for i, p in enumerate(filtrados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(
                f"Proyectos en {pais_detectado or ciudad_detectada} entre {fechas[0]} y {fechas[1]}:",
                buttons=botones
            )
            return
        # Si no hay filtrados, continuamos al siguiente paso

    # ---------------------------------
    # 2) Fechas solamente
    # ---------------------------------
    if rango_inicio and rango_fin:
        filtrados = filtrar_por_rango(proyectos, rango_inicio, rango_fin)

        # Si existen palabras clave, aplicar semántico sobre este subconjunto
        if palabras and filtrados:
            textos_sub = [f"{p['titulo']}. {p['descripcion']}" for p in filtrados]
            resp = openai.embeddings.create(model="text-embedding-3-small", input=textos_sub)
            embeds_sub = [np.array(d.embedding) for d in resp.data]

            resp_q = openai.embeddings.create(model="text-embedding-3-small", input=[" ".join(palabras)])
            embed_q = np.array(resp_q.data[0].embedding)

            sims = []
            for idx, emb_p in enumerate(embeds_sub):
                cos = np.dot(embed_q, emb_p) / (np.linalg.norm(embed_q) * np.linalg.norm(emb_p))
                sims.append((cos, idx))
            sims.sort(reverse=True, key=lambda x: x[0])
            indices_sem = [idx for cos, idx in sims if cos >= 0.7]
            if not indices_sem:
                indices_sem = [idx for _, idx in sims[:5]]

            resultados = [filtrados[i] for i in indices_sem]
            client._contexto[user_id] = {'modo': 'rango_sem', 'lista': resultados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_rango_sem_{i}')]
                for i, p in enumerate(resultados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(
                f"Resultados semánticos entre {fechas[0]} y {fechas[1]}:",
                buttons=botones
            )
            return

        if filtrados:
            client._contexto[user_id] = {'modo': 'rango', 'lista': filtrados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_rango_{i}')]
                for i, p in enumerate(filtrados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(f"Proyectos entre {fechas[0]} y {fechas[1]}:", buttons=botones)
            return
        # Si no hay en ese rango, seguimos

    # ---------------------------------
    # 3) País/Ciudad + Mes
    # ---------------------------------
    if (pais_detectado or ciudad_detectada) and mes_detectado:
        if pais_detectado:
            base = filtrar_por_pais(proyectos, pais_detectado)
            target = pais_detectado
        else:
            base = filtrar_por_ciudad(proyectos, ciudad_detectada)
            target = ciudad_detectada

        idx_mes = MESES_ES.index(mes_detectado) + 1
        filtrados = [p for p in base if p['fecha_inicio'] and p['fecha_inicio'].month == idx_mes]
        filtrados.sort(key=lambda x: x['fecha_inicio'] or datetime.max.date())

        # Si hay palabras clave, búsqueda semántica sobre filtrados
        if palabras and filtrados:
            textos_sub = [f"{p['titulo']}. {p['descripcion']}" for p in filtrados]
            resp = openai.embeddings.create(model="text-embedding-3-small", input=textos_sub)
            embeds_sub = [np.array(d.embedding) for d in resp.data]

            resp_q = openai.embeddings.create(model="text-embedding-3-small", input=[" ".join(palabras)])
            embed_q = np.array(resp_q.data[0].embedding)

            sims = []
            for idx, emb_p in enumerate(embeds_sub):
                cos = np.dot(embed_q, emb_p) / (np.linalg.norm(embed_q) * np.linalg.norm(emb_p))
                sims.append((cos, idx))
            sims.sort(reverse=True, key=lambda x: x[0])
            indices_sem = [idx for cos, idx in sims if cos >= 0.7]
            if not indices_sem:
                indices_sem = [idx for _, idx in sims[:5]]

            resultados = [filtrados[i] for i in indices_sem]
            client._contexto[user_id] = {'modo': 'pais_mes_sem', 'lista': resultados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_pais_mes_sem_{i}')]
                for i, p in enumerate(resultados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(
                f"Resultados semánticos en {target} durante {mes_detectado}:",
                buttons=botones
            )
            return

        if filtrados:
            client._contexto[user_id] = {'modo': 'pais_mes', 'lista': filtrados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_pais_mes_{i}')]
                for i, p in enumerate(filtrados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(f"Proyectos en {target} durante {mes_detectado}:", buttons=botones)
            return
        # Si no hay coincidencias, seguimos

    # ---------------------------------
    # 4) País/Ciudad solo o Mes solo
    # ---------------------------------
    # 4a) País o Ciudad solo
    if pais_detectado or ciudad_detectada:
        if pais_detectado:
            filtrados = filtrar_por_pais(proyectos, pais_detectado)
            modo = 'pais'
            target = pais_detectado
        else:
            filtrados = filtrar_por_ciudad(proyectos, ciudad_detectada)
            modo = 'ciudad'
            target = ciudad_detectada

        # Si hay palabras clave, semántico sobre este subconjunto
        if palabras and filtrados:
            textos_sub = [f"{p['titulo']}. {p['descripcion']}" for p in filtrados]
            resp = openai.embeddings.create(model="text-embedding-3-small", input=textos_sub)
            embeds_sub = [np.array(d.embedding) for d in resp.data]

            resp_q = openai.embeddings.create(model="text-embedding-3-small", input=[" ".join(palabras)])
            embed_q = np.array(resp_q.data[0].embedding)

            sims = []
            for idx, emb_p in enumerate(embeds_sub):
                cos = np.dot(embed_q, emb_p) / (np.linalg.norm(embed_q) * np.linalg.norm(emb_p))
                sims.append((cos, idx))
            sims.sort(reverse=True, key=lambda x: x[0])
            indices_sem = [idx for cos, idx in sims if cos >= 0.7]
            if not indices_sem:
                indices_sem = [idx for _, idx in sims[:5]]

            resultados = [filtrados[i] for i in indices_sem]
            client._contexto[user_id] = {'modo': f'{modo}_sem', 'lista': resultados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_{modo}_sem_{i}')]
                for i, p in enumerate(resultados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(f"Resultados semánticos en {target}:", buttons=botones)
            return

        # Si no hay palabras clave, devolvemos la lista manual
        if filtrados:
            client._contexto[user_id] = {'modo': modo, 'lista': filtrados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_{modo}_{i}')]
                for i, p in enumerate(filtrados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(f"Proyectos en {target}:", buttons=botones)
            return
        # Si no hay proyectos en ese país/ciudad, seguimos

    # 4b) Mes solo
    if mes_detectado:
        idx_mes = MESES_ES.index(mes_detectado) + 1
        filtrados = [p for p in proyectos if p['fecha_inicio'] and p['fecha_inicio'].month == idx_mes]
        filtrados.sort(key=lambda x: x['fecha_inicio'] or datetime.max.date())

        if palabras and filtrados:
            textos_sub = [f"{p['titulo']}. {p['descripcion']}" for p in filtrados]
            resp = openai.embeddings.create(model="text-embedding-3-small", input=textos_sub)
            embeds_sub = [np.array(d.embedding) for d in resp.data]

            resp_q = openai.embeddings.create(model="text-embedding-3-small", input=[" ".join(palabras)])
            embed_q = np.array(resp_q.data[0].embedding)

            sims = []
            for idx, emb_p in enumerate(embeds_sub):
                cos = np.dot(embed_q, emb_p) / (np.linalg.norm(embed_q) * np.linalg.norm(emb_p))
                sims.append((cos, idx))
            sims.sort(reverse=True, key=lambda x: x[0])
            indices_sem = [idx for cos, idx in sims if cos >= 0.7]
            if not indices_sem:
                indices_sem = [idx for _, idx in sims[:5]]

            resultados = [filtrados[i] for i in indices_sem]
            client._contexto[user_id] = {'modo': 'mes_sem', 'lista': resultados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_mes_sem_{i}')]
                for i, p in enumerate(resultados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(f"Resultados semánticos en {mes_detectado}:", buttons=botones)
            return

        if filtrados:
            client._contexto[user_id] = {'modo': 'mes', 'lista': filtrados}
            botones = [
                [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_mes_{i}')]
                for i, p in enumerate(filtrados)
            ]
            botones.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.respond(f"Proyectos en {mes_detectado}:", buttons=botones)
            return
        # Si no hay proyectos en ese mes, seguimos

    # ---------------------------------
    # 5) FALLBACK: Búsqueda semántica en TODO el dataset
    # ---------------------------------
    msg_buscando = await event.respond("🔎 Buscando proyectos semánticamente con embeddings en toda la base...")
    embeddings = client._embeddings or []
    if not embeddings:
        embeddings = calcular_embeds_proyectos(proyectos)
        client._embeddings = embeddings

    resp_q = openai.embeddings.create(model="text-embedding-3-small", input=[texto_original])
    embed_q = np.array(resp_q.data[0].embedding)

    sims = []
    for idx, emb_p in enumerate(embeddings):
        cos = np.dot(embed_q, emb_p) / (np.linalg.norm(embed_q) * np.linalg.norm(emb_p))
        sims.append((cos, idx))
    sims.sort(reverse=True, key=lambda x: x[0])
    indices_sem = [idx for cos, idx in sims if cos >= 0.7]
    if not indices_sem:
        indices_sem = [idx for _, idx in sims[:5]]

    resultados = [proyectos[i] for i in indices_sem]
    if not resultados:
        await msg_buscando.edit(
            "No se encontraron proyectos relevantes para tu consulta.\n\n"
            "Prueba a usar un país, ciudad, mes, rango de fechas (YYYY-MM-DD) o palabras clave."
        )
        return

    client._contexto[user_id] = {'modo': 'nlp', 'lista': resultados}
    botones = [
        [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_nlp_{i}')]
        for i, p in enumerate(resultados)
    ]
    botones.append([Button.inline('🏠 Volver al inicio', 'start')])
    await msg_buscando.edit(f"Hemos encontrado {len(resultados)} proyecto(s) semánticamente similares en toda la base:", buttons=botones)

# ===========================
# CALLBACKS PARA BOTONES
# ===========================
@client.on(events.CallbackQuery)
async def callback_query_handler(event):
    data = event.data.decode()
    user_id = str(event.sender_id)
    proyectos = cargar_todos_los_proyectos()
    ctx = client._contexto.get(user_id)

    # --- Volver al menú principal ---
    if data == 'start':
        client._contexto[user_id] = None
        botones = [
            [Button.inline('🌍 Buscar por país', 'menu_paises')],
            [Button.inline('📅 Buscar por mes', 'menu_meses')],
            [Button.inline('📆 Buscar entre fechas', 'menu_rango')],
            [Button.inline('⏳ Deadline próxima', 'menu_deadline')]
        ]
        await event.edit('¿Cómo quieres buscar proyectos Erasmus?', buttons=botones)
        return

    # --- Menú “Buscar por país” ---
    if data == 'menu_paises':
        lista_paises = obtener_lista_paises(proyectos)
        botones = [[Button.inline(p, f'pais_{p}')] for p in lista_paises]
        botones.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit('Elige un país para ver proyectos:', buttons=botones)
        return

    # --- Selección de un país ---
    if data.startswith('pais_'):
        pais = data.split('pais_', 1)[1]
        proyectos_pais = filtrar_por_pais(proyectos, pais)
        client._contexto[user_id] = {'modo': 'pais', 'lista': proyectos_pais}
        if not proyectos_pais:
            await event.edit(f'No hay proyectos Erasmus registrados para {pais}.')
            return
        botones = [
            [Button.inline(f"{p['titulo']} ({p['ciudad']})", f'proy_pais_{i}')]
            for i, p in enumerate(proyectos_pais)
        ]
        botones.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit(f'Proyectos en {pais}:', buttons=botones)
        return

    # --- Menú “Buscar por mes” ---
    if data == 'menu_meses':
        meses_set = set()
        for p in proyectos:
            if p['fecha_inicio']:
                meses_set.add(p['fecha_inicio'].strftime("%B %Y"))
        lista_meses = sorted(
            meses_set,
            key=lambda x: (
                int(x.split()[1]),
                datetime.strptime(x.split()[0], "%B").month
            )
        )
        botones = [[Button.inline(m, f'mes_{m}')] for m in lista_meses]
        botones.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit('Elige un mes (p.ej. "July 2025") para ver proyectos:', buttons=botones)
        return

    # --- Selección de un mes ---
    if data.startswith('mes_'):
        mes = data.split('mes_', 1)[1]
        # Convertir “July 2025” a mes normalizado “julio” y año “2025”
        partes = mes.split()
        nombre_ingles = partes[0]
        anio = int(partes[1])
        # Mapeo inglés→español básico
        map_mes_ing_es = {
            "January": "enero", "February": "febrero", "March": "marzo",
            "April": "abril", "May": "mayo", "June": "junio",
            "July": "julio", "August": "agosto", "September": "septiembre",
            "October": "octubre", "November": "noviembre", "December": "diciembre"
        }
        mes_es = map_mes_ing_es.get(nombre_ingles, None)
        if not mes_es:
            await event.edit(f'Mes inválido: {mes}.')
            return

        # Filtrar proyectos cuyo fecha_inicio está en ese mes y año
        filtrados = []
        for p in proyectos:
            if p['fecha_inicio'] and p['fecha_inicio'].month == MESES_ES.index(mes_es) + 1 and p['fecha_inicio'].year == anio:
                filtrados.append(p)
        filtrados.sort(key=lambda x: x['fecha_inicio'] or datetime.max.date())

        client._contexto[user_id] = {'modo': 'mes', 'lista': filtrados}
        if not filtrados:
            await event.edit(f'No hay proyectos Erasmus en {mes_es.capitalize()} {anio}.')
            return
        botones = [
            [Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f'proy_mes_{i}')]
            for i, p in enumerate(filtrados)
        ]
        botones.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit(f'Proyectos en {mes_es.capitalize()} {anio}:', buttons=botones)
        return

    # --- Menú “Buscar entre fechas” ---
    if data == 'menu_rango':
        await event.edit(
            'Escribe dos fechas en formato YYYY-MM-DD en un mismo mensaje.\n'
            'Ejemplo: "entre 2025-06-01 y 2025-06-15"\n\n'
            'Si no incluyes dos fechas válidas, no se mostrarán resultados.'
        )
        return

    # --- Menú “Deadline próxima” ---
    if data == 'menu_deadline':
        proximos = filtrar_deadline_proxima(proyectos, dias=14)
        client._contexto[user_id] = {'modo': 'deadline', 'lista': proximos}
        if not proximos:
            await event.edit('No hay proyectos con deadline en los próximos 14 días.')
            return
        botones = []
        hoy = datetime.now().date()
        for i, p in enumerate(proximos):
            dias = (p['deadline'] - hoy).days
            botones.append([
                Button.inline(
                    f"{p['titulo']} ({p['ciudad']}, {p['pais']}) — {dias} días",
                    f'proy_deadline_{i}'
                )
            ])
        botones.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit('Proyectos con deadline próxima:', buttons=botones)
        return

    # —————————————————————————————————————————————————————
    # A partir de aquí, chequeamos primero los callbacks más específicos
    # —————————————————————————————————————————————————————

    # --- Detalle de proyecto semántico por rango (modo 'rango_sem') ---
    if data.startswith('proy_rango_sem_'):
        if not ctx or ctx.get('modo') != 'rango_sem':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_rango')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto por rango (modo 'rango'): fechas ± país/ciudad o sólo fechas ---
    if data.startswith('proy_rango_'):
        if not ctx or ctx.get('modo') not in ('rango',):
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_rango')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto País+Mes semántico (modo 'pais_mes_sem') ---
    if data.startswith('proy_pais_mes_sem_'):
        if not ctx or ctx.get('modo') != 'pais_mes_sem':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'start')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto País+Mes (modo 'pais_mes') ---
    if data.startswith('proy_pais_mes_'):
        if not ctx or ctx.get('modo') != 'pais_mes':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'start')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto País semántico (modo 'pais_sem') ---
    if data.startswith('proy_pais_sem_'):
        if not ctx or ctx.get('modo') != 'pais_sem':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_paises')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto País (modo 'pais') ---
    if data.startswith('proy_pais_') and not data.startswith('proy_pais_mes_') and not data.startswith('proy_pais_sem_'):
        if not ctx or ctx.get('modo') != 'pais':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_paises')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto Ciudad semántico (modo 'ciudad_sem') ---
    if data.startswith('proy_ciudad_sem_'):
        if not ctx or ctx.get('modo') != 'ciudad_sem':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_ciudades')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto Ciudad (modo 'ciudad') ---
    if data.startswith('proy_ciudad_') and not data.startswith('proy_ciudad_sem_'):
        if not ctx or ctx.get('modo') != 'ciudad':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_ciudades')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto Mes semántico (modo 'mes_sem') ---
    if data.startswith('proy_mes_sem_'):
        if not ctx or ctx.get('modo') != 'mes_sem':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_meses')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto Mes (modo 'mes') ---
    if data.startswith('proy_mes_') and not data.startswith('proy_mes_sem_'):
        if not ctx or ctx.get('modo') != 'mes':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [
            [Button.inline('🔙 Volver atrás', 'menu_meses')],
            [Button.inline('🏠 Volver al inicio', 'start')]
        ]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto por deadline próxima ---
    if data.startswith('proy_deadline_'):
        if not ctx or ctx.get('modo') != 'deadline':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [[Button.inline('🏠 Volver al inicio', 'start')]]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

    # --- Detalle de proyecto por búsqueda semántica (modo 'nlp') ---
    if data.startswith('proy_nlp_'):
        if not ctx or ctx.get('modo') != 'nlp':
            await event.answer('Contexto inválido.')
            return
        idx = int(data.split('_')[-1])
        lista = ctx['lista']
        if idx < 0 or idx >= len(lista):
            await event.edit('Proyecto no válido.')
            return
        proyecto = lista[idx]
        texto = formatear_proyecto(proyecto, mostrar_dias_deadline=True)
        botones = [[Button.inline('🏠 Volver al inicio', 'start')]]
        await event.edit(texto, buttons=botones, parse_mode='html')
        return

# ===========================
# ARRANCAR EL BOT
# ===========================
client.start()
client.run_until_disconnected()
