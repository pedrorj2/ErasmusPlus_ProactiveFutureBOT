from telethon import TelegramClient, events
from telethon.tl.custom import Button
from datetime import datetime, timedelta
import os
import re
import csv
from collections import defaultdict
import calendar
import openai
import json
from config import api_id, api_hash, bot_token, lista_profesores, openai_api_key

# from config import api_id, api_hash, bot_token, lista_profesores
# from metrics import ranking_usuarios, media_intentos, lista_usuarios

client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

openai.api_key = openai_api_key

# === FUNCIONES PARA ERASMUS ===
def obtener_paises_erasmus(archivo='proyectos_erasmus.csv'):
    paises = set()
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paises.add(row['pais'])
    return sorted(paises)

def obtener_proyectos_por_pais(pais, archivo='proyectos_erasmus.csv'):
    proyectos = []
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['pais'] == pais:
                    proyectos.append(row)
    return proyectos

def extraer_fechas_inicio_fin(fechas_str):
    # Busca patrones como '1-30 junio 2025', '28 junio - 5 julio 2025', '10-20 julio 2025', '12 julio 2025', etc.
    meses_es = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
    fechas_str = fechas_str.lower().replace('–', '-').replace('—', '-')
    # 1-30 junio 2025
    m = re.match(r'(\d{1,2})-(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})', fechas_str)
    if m:
        dia_ini, dia_fin, mes, anio = m.groups()
        mes_num = meses_es.index(mes) + 1
        return (datetime(int(anio), mes_num, int(dia_ini)), datetime(int(anio), mes_num, int(dia_fin)))
    # 28 junio - 5 julio 2025
    m = re.match(r'(\d{1,2})\s+([a-záéíóúñ]+)\s*-\s*(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})', fechas_str)
    if m:
        dia_ini, mes_ini, dia_fin, mes_fin, anio = m.groups()
        mes_ini_num = meses_es.index(mes_ini) + 1
        mes_fin_num = meses_es.index(mes_fin) + 1
        return (datetime(int(anio), mes_ini_num, int(dia_ini)), datetime(int(anio), mes_fin_num, int(dia_fin)))
    # 12-20 julio 2025
    m = re.match(r'(\d{1,2})-(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})', fechas_str)
    if m:
        dia_ini, dia_fin, mes, anio = m.groups()
        mes_num = meses_es.index(mes) + 1
        return (datetime(int(anio), mes_num, int(dia_ini)), datetime(int(anio), mes_num, int(dia_fin)))
    # 12 julio 2025
    m = re.match(r'(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})', fechas_str)
    if m:
        dia, mes, anio = m.groups()
        mes_num = meses_es.index(mes) + 1
        return (datetime(int(anio), mes_num, int(dia)), datetime(int(anio), mes_num, int(dia)))
    return (None, None)

def meses_entre_fechas(dt_ini, dt_fin):
    meses = []
    meses_es = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    if not dt_ini or not dt_fin:
        return meses
    y, m = dt_ini.year, dt_ini.month
    while (y < dt_fin.year) or (y == dt_fin.year and m <= dt_fin.month):
        meses.append(f"{meses_es[m-1]} {y}")
        if m == 12:
            m = 1
            y += 1
        else:
            m += 1
    return meses

def obtener_meses_erasmus(archivo='proyectos_erasmus.csv'):
    meses = set()
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dt_ini, dt_fin = extraer_fechas_inicio_fin(row['fechas'])
                for mes in meses_entre_fechas(dt_ini, dt_fin):
                    meses.add(mes)
    meses = list(meses)
    meses.sort(key=lambda x: (int(x.split()[-1]), ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"].index(x.split()[0])))
    return meses

def obtener_proyectos_por_mes(mes, archivo='proyectos_erasmus.csv'):
    proyectos = []
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dt_ini, dt_fin = extraer_fechas_inicio_fin(row['fechas'])
                if mes in meses_entre_fechas(dt_ini, dt_fin):
                    proyectos.append((dt_ini, dt_fin, row))
    proyectos.sort(key=lambda x: x[0] if x[0] else datetime(2100,1,1))
    return proyectos
# === FIN FUNCIONES ERASMUS ===

def verificar_registro(user_id):
    if os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == str(user_id):
                    return True
    return False

# Añadir variable de contexto de navegación por usuario
client._contexto_navegacion = getattr(client, '_contexto_navegacion', {})

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = str(event.sender_id)
    client._contexto_navegacion[user_id] = None  # Reset contexto
    if not verificar_registro(user_id):
        await registrar_correo(event)
    else:
        buttons = [
            [Button.inline('🌍 Buscar por país', 'paises')],
            [Button.inline('📅 Buscar por mes', 'meses')],
            [Button.inline('⏳ Deadline próxima', 'deadline_proxima')]
        ]
        await event.respond('¿Cómo quieres buscar proyectos Erasmus?\n\nTambién puedes escribir directamente lo que buscas, por ejemplo: "Busco algo en julio" o "Quiero proyectos en Italia".', buttons=buttons)

async def registrar_correo(event):
    user_id = str(event.sender_id)
    respuesta = await event.respond("Bienvenido! Para empezar, por favor regístrate introduciendo tu correo (@alumnos.upm.es) de la UPM.")
    # Estado de registro temporal
    client._registro_usuarios = getattr(client, '_registro_usuarios', {})
    client._registro_usuarios[user_id] = {'estado': 'esperando_correo', 'mensaje_id': respuesta.id}

# Helper: Load all projects from CSV
def cargar_todos_los_proyectos(archivo='proyectos_erasmus.csv'):
    proyectos = []
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                proyectos.append(row)
    return proyectos

def obtener_lista_paises(archivo='proyectos_erasmus.csv'):
    paises = set()
    if os.path.exists(archivo):
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paises.add(row['pais'].strip().lower())
    return paises

# Helper para filtrar proyectos con deadline próxima
def filtrar_deadline_proxima(proyectos, dias=14):
    hoy = datetime.now().date()
    proximos = []
    for p in proyectos:
        deadline_str = p.get('deadline') or p.get('deadline', '')
        try:
            deadline = datetime.strptime(deadline_str, '%d %B %Y').date()
        except ValueError:
            try:
                deadline = datetime.strptime(deadline_str, '%d %b %Y').date()
            except Exception:
                continue
        if (deadline - hoy).days >= 0 and (deadline - hoy).days <= dias:
            proximos.append(p)
    return proximos

# Helper: Buscar proyectos relevantes usando OpenAI
async def buscar_proyectos_nlp(query, proyectos):
    from openai import AsyncOpenAI
    import json
    client_openai = AsyncOpenAI(api_key=openai_api_key)
    contexto = "".join([
        f"Título: {p['titulo']}, País: {p['pais']}, Ciudad: {p['ciudad']}, Fechas: {p['fechas']}, Descripción: {p['descripcion']}\n"
        for p in proyectos
    ])
    ejemplos = """
Ejemplos de uso:
Usuario: Italia
Respuesta: Devuelve proyectos en Italia.
Usuario: Busco algo en julio
Respuesta: Devuelve proyectos que ocurren en julio.
Usuario: Quiero proyectos en Alemania sobre energía
Respuesta: Devuelve proyectos en Alemania relacionados con energía.
Usuario: Madrid
Respuesta: Devuelve proyectos en Madrid.
"""
    prompt = f"""
Eres un asistente que ayuda a encontrar proyectos Erasmus. El usuario puede preguntar por país, ciudad, mes, temática, etc. Si la consulta es solo un país, busca proyectos en ese país. Si es una ciudad, busca en esa ciudad. Si es un mes, busca en ese mes. Si es una temática, busca por descripción. Devuelve la respuesta en formato JSON con una lista llamada 'proyectos', cada uno con las claves: titulo, pais, ciudad, fechas, descripcion, requisitos, gastos_cubiertos, contacto, enlace. Si no hay nada relevante, la lista debe estar vacía. Base de datos:
{contexto}
{ejemplos}
El usuario pregunta: '{query}'
"""
    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content.strip()
        try:
            data = json.loads(content)
            return data.get('proyectos', [])
        except json.JSONDecodeError:
            # Fallback: intenta buscar por país si la consulta es solo un país
            paises = obtener_lista_paises()
            consulta = query.strip().lower()
            if consulta in paises:
                return 'FALLBACK_PAIS', consulta
            return "Ocurrió un error al procesar la respuesta de la IA. Intenta de nuevo o usa otra consulta."
    except Exception as e:
        return f"Ocurrió un error al buscar proyectos: {e}"

@client.on(events.NewMessage)
async def message_handler(event):
    if event.out:
        return
    user_id = str(event.sender_id)
    client._registro_usuarios = getattr(client, '_registro_usuarios', {})
    if user_id in client._registro_usuarios and client._registro_usuarios[user_id].get('estado') == 'esperando_correo':
        correo = event.text.strip()
        if re.match(r'^[a-zA-Z0-9_.+-]+@alumnos.upm.es$', correo):
            usuarios = []
            if os.path.exists('usuarios.csv'):
                with open('usuarios.csv', 'r', newline='', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    usuarios = list(reader)
            usuarios = [row for row in usuarios if row[0] != user_id]
            usuarios.append([user_id, correo])
            with open('usuarios.csv', 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(usuarios)
            del client._registro_usuarios[user_id]
            await event.respond('Registro completado con éxito.')
            buttons = [
                [Button.inline('🌍 Buscar por país', 'paises')],
                [Button.inline('📅 Buscar por mes', 'meses')],
                [Button.inline('⏳ Deadline próxima', 'deadline_proxima')]
            ]
            await event.respond('¿Cómo quieres buscar proyectos Erasmus?\n\nTambién puedes escribir directamente lo que buscas, por ejemplo: "Busco algo en julio" o "Quiero proyectos en Italia".', buttons=buttons)
        return
    # Si no es comando ni registro, usa NLP
    if event.text.startswith('/'):
        return  # deja que otros handlers gestionen comandos
    # Procesa consulta natural
    consulta = event.text.strip()
    proyectos = cargar_todos_los_proyectos()
    # Fallback directo si la consulta es solo un país conocido
    paises = obtener_lista_paises()
    if consulta.lower() in paises:
        proyectos_pais = obtener_proyectos_por_pais(consulta)
        if not proyectos_pais:
            await event.respond(f'No hay proyectos Erasmus registrados para {consulta.title()}.')
            return
        buttons = [[Button.inline(f"{p['titulo']} ({p['ciudad']})", f'proy_{i}_{consulta}')]
                   for i, p in enumerate(proyectos_pais)]
        buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.respond(f'Proyectos Erasmus en {consulta.title()}:', buttons=buttons)
        return
    # Mensaje de "buscando..."
    buscando_msg = await event.respond('🔎 Buscando proyectos que encajen con tu búsqueda...')
    resultados = await buscar_proyectos_nlp(consulta, proyectos)
    # Fallback si la IA detecta país
    if isinstance(resultados, tuple) and resultados[0] == 'FALLBACK_PAIS':
        pais = resultados[1]
        proyectos_pais = obtener_proyectos_por_pais(pais.title())
        if not proyectos_pais:
            await buscando_msg.edit(f'No hay proyectos Erasmus registrados para {pais.title()}.')
            return
        buttons = [[Button.inline(f"{p['titulo']} ({p['ciudad']})", f'proy_{i}_{pais}')]
                   for i, p in enumerate(proyectos_pais)]
        buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
        await buscando_msg.edit(f'Proyectos Erasmus en {pais.title()}:', buttons=buttons)
        return
    if isinstance(resultados, str):
        await buscando_msg.edit(resultados)
        return
    if not resultados:
        await buscando_msg.edit('No se encontraron proyectos relevantes para tu consulta.')
        return
    # Guardar resultados en contexto de usuario
    client._contexto_navegacion[user_id] = {'tipo': 'nlp', 'resultados': resultados, 'idx': 0, 'msg_id': buscando_msg.id}
    n = len(resultados)
    if n > 1:
        aviso = f"<i>Hemos encontrado {n} resultados para ti según tu búsqueda. Puedes navegar con los botones de abajo.</i>"
    else:
        aviso = f"<i>Hemos encontrado 1 resultado para ti según tu búsqueda.</i>"
    await buscando_msg.edit(aviso, parse_mode='html')
    project_msg = await event.respond('Cargando proyecto...')
    client._contexto_navegacion[user_id]['project_msg_id'] = project_msg.id
    await mostrar_proyecto_nlp(project_msg, user_id, 0)

def formatear_proyecto(p, mostrar_dias_deadline=False):
    texto = f"<b>{p.get('titulo','')}</b>\n\n"
    texto += f"<b>País:</b> {p.get('pais','')}\n"
    texto += f"<b>Ciudad:</b> {p.get('ciudad','')}\n"
    # Fechas
    fechas = p.get('fechas','')
    if fechas:
        partes = fechas.split()
        if '-' in partes[0]:
            # Ejemplo: 1-15 junio 2025
            fechas_split = partes[0].split('-')
            if len(fechas_split) == 2:
                texto += f"<b>Fecha inicio:</b> {fechas_split[0]}/{partes[1]}/{partes[2]}\n"
                texto += f"<b>Fecha final:</b> {fechas_split[1]}/{partes[1]}/{partes[2]}\n"
            else:
                texto += f"<b>Fechas:</b> {fechas}\n"
        elif len(partes) >= 3:
            texto += f"<b>Fecha:</b> {fechas}\n"
        else:
            texto += f"<b>Fechas:</b> {fechas}\n"
    else:
        texto += f"<b>Fechas:</b> -\n"
    texto += f"<b>Descripción:</b> {p.get('descripcion','')}\n"
    if p.get('requisitos'):
        texto += f"<b>Requisitos:</b> {p['requisitos']}\n"
    if p.get('gastos_cubiertos'):
        texto += f"<b>Gastos cubiertos:</b> {p['gastos_cubiertos']}\n"
    if p.get('contacto'):
        texto += f"<b>Contacto:</b> {p['contacto']}\n"
    if p.get('enlace'):
        texto += f"<b>Enlace:</b> {p['enlace']}\n"
    if p.get('deadline'):
        texto += f"<b>🗓️ Deadline para aplicar:</b> {p['deadline']}"
        if mostrar_dias_deadline:
            try:
                deadline = datetime.strptime(p['deadline'], '%d %B %Y').date()
            except ValueError:
                try:
                    deadline = datetime.strptime(p['deadline'], '%d %b %Y').date()
                except Exception:
                    deadline = None
            if deadline:
                dias = (deadline - datetime.now().date()).days
                if dias >= 0:
                    texto += f"  <b>({dias} días para cierre)</b>"
        texto += "\n"
    return texto

# Nueva función para mostrar un proyecto NLP con botones de navegación (edita el mensaje del proyecto)
async def mostrar_proyecto_nlp(event_or_msg, user_id, idx):
    ctx = client._contexto_navegacion.get(user_id, {})
    resultados = ctx.get('resultados', [])
    n = len(resultados)
    if not resultados or idx < 0 or idx >= n:
        await event_or_msg.edit('No se pudo mostrar el proyecto seleccionado.')
        return
    p = resultados[idx]
    texto = formatear_proyecto(p, mostrar_dias_deadline=True)
    # Botones de navegación
    nav_buttons = []
    # Anterior (vacío si idx==0)
    if idx == 0:
        nav_buttons.append(Button.inline(' ', 'nlp_dummy'))
    else:
        nav_buttons.append(Button.inline('⬅️ Anterior', f'nlp_prev_{idx-1}'))
    # x/n SIEMPRE visible
    nav_buttons.append(Button.inline(f'{idx+1}/{n}', 'nlp_dummy'))
    # Siguiente (vacío si idx==n-1)
    if idx == n-1:
        nav_buttons.append(Button.inline(' ', 'nlp_dummy'))
    else:
        nav_buttons.append(Button.inline('Siguiente ➡️', f'nlp_next_{idx+1}'))
    buttons = [nav_buttons]
    buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
    await event_or_msg.edit(texto, buttons=buttons, parse_mode='html')

# Handler para navegación NLP (edita el mensaje del proyecto)
@client.on(events.CallbackQuery(pattern=b'nlp_(prev|next)_\d+'))
async def nlp_nav_handler(event):
    user_id = str(event.sender_id)
    data = event.data.decode()
    m = re.match(r'nlp_(prev|next)_(\d+)', data)
    if not m:
        await event.answer('Navegación inválida')
        return
    idx = int(m.group(2))
    client._contexto_navegacion = getattr(client, '_contexto_navegacion', {})
    if user_id not in client._contexto_navegacion or client._contexto_navegacion[user_id].get('tipo') != 'nlp':
        await event.answer('No hay resultados para navegar.')
        return
    client._contexto_navegacion[user_id]['idx'] = idx
    project_msg_id = client._contexto_navegacion[user_id].get('project_msg_id')
    # Recupera el mensaje del proyecto para editarlo
    msg = await event.get_message()
    await mostrar_proyecto_nlp(msg, user_id, idx)

@client.on(events.CallbackQuery)
async def callback_query_handler(event):
    data = event.data.decode()
    user_id = str(event.sender_id)
    client._contexto_navegacion = getattr(client, '_contexto_navegacion', {})
    if event.sender_id in lista_profesores:
        if event.data == b'confirmar_reset':
            if os.path.exists('usuarios.csv'):
                os.remove('usuarios.csv')
            await event.edit('Datos de usuarios borrados con éxito.')
        elif event.data == b'cancelar_reset':
            await event.edit('Acción cancelada. Los datos no fueron borrados.')
    if data.startswith('pais_'):
        pais = data.split('pais_')[1]
        proyectos = obtener_proyectos_por_pais(pais)
        client._contexto_navegacion[user_id] = {'tipo': 'pais', 'valor': pais}
        if not proyectos:
            await event.edit(f'No hay proyectos Erasmus registrados para {pais}.')
            return
        buttons = [[Button.inline(f"{p['titulo']} ({p['ciudad']})", f'proy_{i}_{pais}')] for i, p in enumerate(proyectos)]
        buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit(f'Proyectos Erasmus en {pais}:', buttons=buttons)
    elif data.startswith('mes_'):
        mes = data.split('mes_')[1]
        proyectos = obtener_proyectos_por_mes(mes)
        client._contexto_navegacion[user_id] = {'tipo': 'mes', 'valor': mes}
        if not proyectos:
            await event.edit(f'No hay proyectos Erasmus registrados para {mes}.')
            return
        buttons = [[Button.inline(f"{p[2]['titulo']} ({p[2]['ciudad']}, {p[2]['pais']})", f'proy_mes_{i}_{mes}')] for i, p in enumerate(proyectos)]
        buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit(f'Proyectos Erasmus en {mes}:', buttons=buttons)
    elif data.startswith('proy_mes_'):
        _, _, idx, mes = data.split('_', 3)
        proyectos = obtener_proyectos_por_mes(mes)
        try:
            idx = int(idx)
            print(f"[DEBUG] proy_mes_: idx={idx}, total proyectos={len(proyectos)}")
            if not proyectos:
                await event.edit('No hay proyectos para este mes.')
                return
            if idx < 0 or idx >= len(proyectos):
                await event.edit(f'Índice fuera de rango. Proyectos: {len(proyectos)}, idx: {idx}')
                return
            dt_ini, dt_fin, row = proyectos[idx]
            texto = f"<b>{row['titulo']}</b>\n\n"
            texto += f"<b>País:</b> {row['pais']}\n"
            texto += f"<b>Ciudad:</b> {row['ciudad']}\n"
            texto += f"<b>Fecha inicio:</b> {dt_ini.strftime('%d/%m/%Y') if dt_ini else '-'}\n"
            texto += f"<b>Fecha final:</b> {dt_fin.strftime('%d/%m/%Y') if dt_fin else '-'}\n"
            texto += f"<b>Descripción:</b> {row['descripcion']}\n"
            if row['requisitos']:
                texto += f"<b>Requisitos:</b> {row['requisitos']}\n"
            if row['gastos_cubiertos']:
                texto += f"<b>Gastos cubiertos:</b> {row['gastos_cubiertos']}\n"
            if row['contacto']:
                texto += f"<b>Contacto:</b> {row['contacto']}\n"
            if row['enlace']:
                texto += f"<b>Enlace:</b> {row['enlace']}\n"
            buttons = [
                [Button.inline('🔙 Volver atrás', 'volver_atras')],
                [Button.inline('🏠 Volver al inicio', 'start')]
            ]
            await event.edit(texto, buttons=buttons, parse_mode='html')
        except Exception as e:
            print(f"[ERROR] proy_mes_: {e}")
            await event.edit('No se pudo mostrar el proyecto seleccionado.')
    elif data.startswith('proy_'):
        _, idx, pais = data.split('_', 2)
        proyectos = obtener_proyectos_por_pais(pais)
        try:
            idx = int(idx)
            p = proyectos[idx]
            dt_ini, dt_fin = extraer_fechas_inicio_fin(p['fechas'])
            client._contexto_navegacion[user_id] = {'tipo': 'pais', 'valor': pais}
            texto = f"<b>{p['titulo']}</b>\n\n"
            texto += f"<b>Ciudad:</b> {p['ciudad']}\n"
            texto += f"<b>Fecha inicio:</b> {dt_ini.strftime('%d/%m/%Y') if dt_ini else '-'}\n"
            texto += f"<b>Fecha final:</b> {dt_fin.strftime('%d/%m/%Y') if dt_fin else '-'}\n"
            texto += f"<b>Descripción:</b> {p['descripcion']}\n"
            if p['requisitos']:
                texto += f"<b>Requisitos:</b> {p['requisitos']}\n"
            if p['gastos_cubiertos']:
                texto += f"<b>Gastos cubiertos:</b> {p['gastos_cubiertos']}\n"
            if p['contacto']:
                texto += f"<b>Contacto:</b> {p['contacto']}\n"
            if p['enlace']:
                texto += f"<b>Enlace:</b> {p['enlace']}\n"
            buttons = [
                [Button.inline('🔙 Volver atrás', 'volver_atras')],
                [Button.inline('🏠 Volver al inicio', 'start')]
            ]
            await event.edit(texto, buttons=buttons, parse_mode='html')
        except Exception:
            await event.edit('No se pudo mostrar el proyecto seleccionado.')
    elif data == 'volver_atras':
        ctx = client._contexto_navegacion.get(user_id)
        if ctx and ctx['tipo'] == 'pais':
            pais = ctx['valor']
            proyectos = obtener_proyectos_por_pais(pais)
            buttons = [[Button.inline(f"{p['titulo']} ({p['ciudad']})", f'proy_{i}_{pais}')] for i, p in enumerate(proyectos)]
            buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.edit(f'Proyectos Erasmus en {pais}:', buttons=buttons)
        elif ctx and ctx['tipo'] == 'mes':
            mes = ctx['valor']
            proyectos = obtener_proyectos_por_mes(mes)
            buttons = [[Button.inline(f"{p[2]['titulo']} ({p[2]['ciudad']}, {p[2]['pais']})", f'proy_mes_{i}_{mes}')] for i, p in enumerate(proyectos)]
            buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.edit(f'Proyectos Erasmus en {mes}:', buttons=buttons)
        else:
            buttons = [
                [Button.inline('🌍 Buscar por país', 'paises')],
                [Button.inline('📅 Buscar por mes', 'meses')],
                [Button.inline('⏳ Deadline próxima', 'deadline_proxima')]
            ]
            await event.edit('¿Cómo quieres buscar proyectos Erasmus?', buttons=buttons)
    elif data == 'start':
        client._contexto_navegacion[user_id] = None
        buttons = [
            [Button.inline('🌍 Buscar por país', 'paises')],
            [Button.inline('📅 Buscar por mes', 'meses')],
            [Button.inline('⏳ Deadline próxima', 'deadline_proxima')]
        ]
        await event.edit('¿Cómo quieres buscar proyectos Erasmus?', buttons=buttons)
    elif data == 'paises':
        paises = obtener_paises_erasmus()
        buttons = [[Button.inline(pais, f'pais_{pais}')] for pais in paises]
        buttons.append([Button.inline('⬅️ Volver atrás', 'start')])
        await event.edit('Elige un país para ver proyectos Erasmus:', buttons=buttons)
    elif data == 'meses':
        meses = obtener_meses_erasmus()
        buttons = [[Button.inline(mes, f'mes_{mes}')] for mes in meses]
        buttons.append([Button.inline('⬅️ Volver atrás', 'start')])
        await event.edit('Elige un mes para ver proyectos Erasmus:', buttons=buttons)
    elif data == 'deadline_proxima':
        proyectos = filtrar_deadline_proxima(cargar_todos_los_proyectos())
        if not proyectos:
            await event.edit('No hay proyectos con deadline próxima.')
            return
        # Ordenar por deadline más cercana
        def dias_para_deadline(p):
            deadline_str = p.get('deadline') or p.get('deadline', '')
            try:
                deadline = datetime.strptime(deadline_str, '%d %B %Y').date()
            except ValueError:
                try:
                    deadline = datetime.strptime(deadline_str, '%d %b %Y').date()
                except Exception:
                    return 9999
            return (deadline - datetime.now().date()).days
        proyectos.sort(key=dias_para_deadline)
        buttons = []
        for i, p in enumerate(proyectos):
            dias = dias_para_deadline(p)
            texto_btn = f"{p['titulo']} ({p['ciudad']}, {p['pais']}) - {dias} días para cierre"
            buttons.append([Button.inline(texto_btn, f"proy_deadline_{i}")])
        buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit('Proyectos con deadline próxima:', buttons=buttons)

# Comandos de administración (puedes mantenerlos o quitarlos si no los necesitas)
@client.on(events.NewMessage(pattern='/id'))
async def send_id(event):
    user_id = str(event.sender_id)
    await event.respond(f"Tu ID de usuario es: {user_id}")

@client.on(events.NewMessage(pattern='/reset'))
async def reset(event):
    if event.sender_id in lista_profesores:
        buttons = [[Button.inline('Sí', 'confirmar_reset'), Button.inline('No', 'cancelar_reset')]]
        await event.respond('¿Estás seguro de que quieres borrar todos los datos de usuarios? No se podrán recuperar', buttons=buttons)
    else:
        await event.respond('No tienes permiso para ejecutar este comando. Sólo está disponible para profesores.')

@client.on(events.NewMessage(pattern='/paises'))
async def menu_paises(event):
    paises = obtener_paises_erasmus()
    buttons = [[Button.inline(pais, f'pais_{pais}')] for pais in paises]
    buttons.append([Button.inline('⏳ Solo deadlines próximas', 'paises_deadline')])
    await event.respond('Elige un país para ver proyectos Erasmus:', buttons=buttons)

@client.on(events.NewMessage(pattern='/meses'))
async def menu_meses(event):
    meses = obtener_meses_erasmus()
    buttons = [[Button.inline(mes, f'mes_{mes}')] for mes in meses]
    buttons.append([Button.inline('⏳ Solo deadlines próximas', 'meses_deadline')])
    await event.respond('Elige un mes para ver proyectos Erasmus:', buttons=buttons)

# Handler para deadlines próximas por país
@client.on(events.CallbackQuery(pattern=b'paises_deadline'))
async def paises_deadline_handler(event):
    proyectos = cargar_todos_los_proyectos()
    proximos = filtrar_deadline_proxima(proyectos)
    if not proximos:
        await event.edit('No hay proyectos con deadline próxima.')
        return
    buttons = [[Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f"proy_deadline_{i}")] for i, p in enumerate(proximos)]
    buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
    await event.edit('Proyectos con deadline próxima:', buttons=buttons)

# Handler para deadlines próximas por mes
@client.on(events.CallbackQuery(pattern=b'meses_deadline'))
async def meses_deadline_handler(event):
    proyectos = cargar_todos_los_proyectos()
    proximos = filtrar_deadline_proxima(proyectos)
    if not proximos:
        await event.edit('No hay proyectos con deadline próxima.')
        return
    buttons = [[Button.inline(f"{p['titulo']} ({p['ciudad']}, {p['pais']})", f"proy_deadline_{i}")] for i, p in enumerate(proximos)]
    buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
    await event.edit('Proyectos con deadline próxima:', buttons=buttons)

# Handler para mostrar proyecto de deadline próxima
@client.on(events.CallbackQuery(pattern=b'proy_deadline_\d+'))
async def proy_deadline_handler(event):
    idx = int(event.data.decode().split('_')[-1])
    proyectos = filtrar_deadline_proxima(cargar_todos_los_proyectos())
    if idx < 0 or idx >= len(proyectos):
        await event.edit('No se pudo mostrar el proyecto seleccionado.')
        return
    p = proyectos[idx]
    texto = formatear_proyecto(p, mostrar_dias_deadline=True)
    buttons = [[Button.inline('🏠 Volver al inicio', 'start')]]
    await event.edit(texto, buttons=buttons, parse_mode='html')

client.start()
client.run_until_disconnected()
