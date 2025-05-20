from telethon import TelegramClient, events
from telethon.tl.custom import Button
from datetime import datetime

# from config import api_id, api_hash, bot_token, lista_profesores
from metrics import ranking_usuarios, media_intentos, lista_usuarios

import os
import re
import csv

# Configuración de tu API de Telegram, la importo del archivo config.py
# No es público por seguridad, sólo contiene estos tres datos de a continuación:
api_id = '28092530'
api_hash = 'dcedc3ea5fbfb53690f7d80873e0d5d6'
bot_token = '7952301503:AAGnCDg0L8aWbtdemmjsFof_9vnMstNSJak'
lista_profesores = []


client = TelegramClient('bot_session', api_id, api_hash).start(bot_token=bot_token)

preguntas_folder = r'Preguntas'

selecciones_pregunta = {}

respuestas_de_usuarios = {}

def verificar_registro(user_id):
    if os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == str(user_id):
                    return True
    return False


def obtener_preguntas_desde_archivo(archivo):
    ruta_completa = os.path.join(preguntas_folder, archivo)
    with open(ruta_completa, 'r', encoding='utf-8') as file:
        contenido = file.read()

    preguntas = re.findall(r'::(.*?)\{(.*?)\}', contenido, re.DOTALL)
    preguntas_procesadas = []

    for titulo, opciones in preguntas:
        titulo_limpio = titulo.replace(':: ', '').strip()
        opciones = re.sub(r'~%-\d+%', '~', opciones)
        opciones = re.sub(r'~%\d+%', '=', opciones)
        opciones = re.findall(r'([=~])(.*?)\s*(?=\n|\Z)', opciones)
    
        opciones_procesadas = [(opcion.strip()[0].upper() + opcion.strip()[1:].lower(), tipo == '=') for tipo, opcion in opciones]
        preguntas_procesadas.append((titulo_limpio, opciones_procesadas))

    return preguntas_procesadas


def listar_archivos_preguntas(prefijo):
    archivos = [f for f in os.listdir(preguntas_folder) if f.startswith(prefijo) and f.endswith('.txt')]
    archivos.sort()
    return archivos

def guardar_csv(user_id, datos, archivo='respuestas.csv'):
    with open(archivo, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for dato in datos:
            writer.writerow([user_id, *dato, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

def cargar_csv(archivo='respuestas.csv'):
    try:
        with open(archivo, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 4:
                    user_id, tema_pregunta, numero_pregunta, puntuacion, _ = row
                    clave_respuesta = (tema_pregunta, numero_pregunta)
                    if user_id not in respuestas_de_usuarios:
                        respuestas_de_usuarios[user_id] = {}
                    if clave_respuesta not in respuestas_de_usuarios[user_id]:
                        respuestas_de_usuarios[user_id][clave_respuesta] = []
                    respuestas_de_usuarios[user_id][clave_respuesta].append(puntuacion)
    except FileNotFoundError:
        print("Archivo de resultados no encontrado, iniciando sin datos previos.")


cargar_csv()


@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = str(event.sender_id)
    if not verificar_registro(user_id):
        await registrar_correo(event)
    else:
        archivos = listar_archivos_preguntas('tema_')
        buttons = [[Button.inline(f'{archivo.replace(".txt", "").replace("_", " ").title()}', f'archivo_{archivo}')] for archivo in archivos]
        await event.respond('Elige un tema:', buttons=buttons)

async def registrar_correo(event):
    user_id = str(event.sender_id)
    respuesta = await event.respond("Bienvenido! Para empezar, por favor regístrate introduciendo tu correo (@alumnos.upm.es) de la UPM.")
    respuestas_de_usuarios[user_id] = {'estado': 'esperando_correo', 'mensaje_id': respuesta.id}

@client.on(events.NewMessage)
async def message_handler(event):
    # Ignorar los mensajes que el bot envía a sí mismo
    if event.out:
        return

    user_id = str(event.sender_id)
    
    # Verificar si el usuario está en el estado de 'esperando_correo' antes de procesar el mensaje
    if user_id in respuestas_de_usuarios and respuestas_de_usuarios[user_id].get('estado') == 'esperando_correo':
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

            del respuestas_de_usuarios[user_id]
            await event.respond('Registro completado con éxito.')
            
            # Mostrar la selección de temas inmediatamente después del registro
            archivos = listar_archivos_preguntas('tema_')
            buttons = [[Button.inline(f'{archivo.replace(".txt", "").replace("_", " ").title()}', f'archivo_{archivo}')] for archivo in archivos]
            await event.respond('Elige un tema:', buttons=buttons)




@client.on(events.NewMessage(pattern='/mis_respuestas'))
async def ver_datos(event):
    user_id = str(event.sender_id)
    if user_id in respuestas_de_usuarios:

        claves_ordenadas = sorted(respuestas_de_usuarios[user_id].keys(), key=lambda x: (x[0], x[1]))

        respuesta_texto = "Datos almacenados:\n"
        for clave in claves_ordenadas:
            puntuaciones = respuestas_de_usuarios[user_id][clave]

            puntuaciones_formateadas = [f"{float(p.replace('%', '')):.0f}%" for p in puntuaciones]
            respuesta_texto += f"Tema {clave[0]}, Pregunta {clave[1]}: {', '.join(puntuaciones_formateadas)}\n"
        
        await event.respond(respuesta_texto)
    else:
        await event.respond("No hay datos almacenados para tu usuario.")

@client.on(events.NewMessage(pattern='/ranking'))
async def ranking(event):
    user_id = str(event.sender_id)
    correo_usuario = None

    # Buscar el correo del usuario solicitante en usuarios.csv
    if os.path.exists('usuarios.csv'):
        with open('usuarios.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[0] == user_id:
                    correo_usuario = row[1]
                    break

    try:
        ranking = ranking_usuarios()
        ranking_texto = "Top 20 Ranking de usuarios:\n"

        # Mostrar el ranking, identificando al usuario solicitante con su correo sin el dominio @alumnos.upm.es
        for i, (usuario, puntuacion) in enumerate(ranking[:20], start=1):
            if usuario == user_id and correo_usuario:
                correo_sin_dominio = correo_usuario.replace('@alumnos.upm.es', '')

                # Mensaje especial si el usuario está en primer lugar
                if i == 1:
                    ranking_texto = "¡Qué más da el ranking, vas primero!\n\nEsto es un easter egg que dejó en que hizo este bot, saludos! ;)\n\n" + ranking_texto

                ranking_texto += f"{i}: {correo_sin_dominio} - {puntuacion} puntos\n"  # Mostrar el correo del usuario solicitante sin el dominio
            else:
                ranking_texto += f"{i}: {puntuacion} puntos\n"  # Mostrar puntos para otros usuarios sin identificarlos

        # Si el usuario solicitante no está en el Top 20, mostrar su posición completa en el ranking
        if user_id not in [usuario for usuario, _ in ranking[:20]]:
            for i, (usuario, puntuacion) in enumerate(ranking, start=1):
                if usuario == user_id:
                    # Obtener usuario de correo si el puesto > 20
                    correo_sin_dominio = correo_usuario.replace('@alumnos.upm.es', '')
                    ranking_texto += f"\nTu posición en el ranking es {i}:\n {correo_sin_dominio} - {puntuacion} puntos\n"
                    break

        await event.respond(ranking_texto)
    except FileNotFoundError:
        await event.respond("No hay datos de ranking disponibles.")


@client.on(events.NewMessage(pattern='/rankingprofesor'))
async def ranking(event):
    if event.sender_id in lista_profesores:
        try:
            ranking = ranking_usuarios()
            ranking_texto = "Ranking de usuarios:\n"
            for i, (usuario, puntuacion) in enumerate(ranking, start=1):
                ranking_texto += f"{i}. {usuario}: {puntuacion} puntos\n"
            await event.respond(ranking_texto)
        except FileNotFoundError:
            await event.respond("No hay datos de ranking disponibles.")
    else:
        await event.respond('No tienes permiso para ejecutar este comando. Ahora sólo está disponible para profesores.')



@client.on(events.NewMessage(pattern='/media'))
async def media(event):
    if event.sender_id in lista_profesores:
        try:
            ranking = ranking_usuarios()
            puntuaciones = [puntuacion for _, puntuacion in ranking]
            puntuacion_maxima = 100 * sum(len(obtener_preguntas_desde_archivo(archivo)) for archivo in listar_archivos_preguntas('tema_'))
            puntuacion_media = sum(puntuaciones) / len(puntuaciones)
            await event.respond(f"Media de puntuaciones: {puntuacion_media:.0f} puntos\nPuntuación máxima posible: {puntuacion_maxima:.0f} puntos")
        except FileNotFoundError:
            await event.respond("No hay datos de puntuaciones disponibles.")
    else:
        await event.respond('No tienes permiso para ejecutar este comando. Ahora sólo está disponible para profesores.')

@client.on(events.NewMessage(pattern='/lista'))
async def lista(event):
    if event.sender_id in lista_profesores:
        try:
            usuarios = lista_usuarios()
            if usuarios:
                lista_usuarios_texto = f"Hay {len(usuarios)} usuarios con datos almacenados:\n" + '\n'.join(usuarios)
                await event.respond(lista_usuarios_texto)
            else:
                await event.respond("No hay datos almacenados para ningún usuario.")
        except FileNotFoundError:
            await event.respond("No hay datos de usuarios disponibles.")
    else:
        await event.respond('No tienes permiso para ejecutar este comando. Ahora sólo está disponible para profesores.')

@client.on(events.NewMessage(pattern='/id'))
async def send_id(event):
    user_id = str(event.sender_id)
    await event.respond(f"Tu ID de usuario es: {user_id}")


@client.on(events.NewMessage(pattern='/reset'))
async def reset(event):
    if event.sender_id in lista_profesores:
        buttons = [[Button.inline('Sí', 'confirmar_reset'), Button.inline('No', 'cancelar_reset')]]
        await event.respond('¿Estás seguro de que quieres borrar todas las respuestas? No se podrán recuperar', buttons=buttons)
    else:
        await event.respond('No tienes permiso para ejecutar este comando. Sólo está disponible para profesores.')  


@client.on(events.CallbackQuery)
async def callback_query_handler(event):
    data = event.data.decode()

    if event.sender_id in lista_profesores:
        if event.data == b'confirmar_reset':
            if os.path.exists('respuestas.csv'):
                os.remove('respuestas.csv')
            respuestas_de_usuarios.clear()
            await event.edit('Datos borrados con éxito.')
        elif event.data == b'cancelar_reset':
            await event.edit('Acción cancelada. Los datos no fueron borrados.')

    if data.startswith('archivo_'):
        archivo_seleccionado = data.split('archivo_')[1]
        preguntas = obtener_preguntas_desde_archivo(archivo_seleccionado)
        selecciones_pregunta[archivo_seleccionado] = [[False] * len(opciones) for _, opciones in preguntas]

        user_id = str(event.sender_id)
        buttons = []
        for i, _ in enumerate(preguntas, start=1):
            estado = obtener_estado_pregunta(user_id, archivo_seleccionado, i)
            boton_texto = f'Pregunta {i} {estado}'
            buttons.append([Button.inline(boton_texto, f'preg_{i}_{archivo_seleccionado}')])
        buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
        await event.edit('Elige una pregunta:', buttons=buttons)

    if data.startswith('preg_'):
        _, numero_pregunta, archivo_seleccionado = data.split('_', 2)
        preguntas = obtener_preguntas_desde_archivo(archivo_seleccionado)
        pregunta, opciones = preguntas[int(numero_pregunta) - 1]

        total_correctas = sum(1 for _, correcta in opciones if correcta)
        instruccion_pregunta = "la única opción correcta:" if total_correctas == 1 else f"las {total_correctas} respuestas correctas:"

        texto_pregunta = f"{pregunta}\n\nSeleccione {instruccion_pregunta}"
        texto_opciones = "\n".join([f"{chr(65 + i)}. {opcion[0]}" for i, opcion in enumerate(opciones)])
        seleccion_actual = selecciones_pregunta[archivo_seleccionado][int(numero_pregunta) - 1]
        buttons = generar_botones_pregunta(seleccion_actual, numero_pregunta, archivo_seleccionado)
        buttons.append([Button.inline('📤 Enviar respuesta', f'enviar_{numero_pregunta}_{archivo_seleccionado}')])
        buttons.append([Button.inline('🔙 Volver al tema', f'archivo_{archivo_seleccionado}')])

        await event.edit(f'{texto_pregunta}\n\n{texto_opciones}', buttons=buttons)

    elif data.startswith('select_'):
        _, numero_pregunta, opcion_seleccionada, archivo_seleccionado = data.split('_', 3)
        preguntas = obtener_preguntas_desde_archivo(archivo_seleccionado)
        pregunta, opciones = preguntas[int(numero_pregunta) - 1]

        selecciones = selecciones_pregunta[archivo_seleccionado][int(numero_pregunta) - 1]
        selecciones[int(opcion_seleccionada)] = not selecciones[int(opcion_seleccionada)]

        total_correctas = sum(1 for _, correcta in opciones if correcta)
        instruccion_pregunta = "la única opción correcta:" if total_correctas == 1 else f"las {total_correctas} respuestas correctas:"

        texto_pregunta = f"{pregunta}\n\nSeleccione {instruccion_pregunta}"
        texto_opciones = "\n".join([f"{chr(65 + i)}. {opcion[0]}" for i, opcion in enumerate(opciones)])
        buttons = generar_botones_pregunta(selecciones, numero_pregunta, archivo_seleccionado)
        buttons.append([Button.inline('📤 Enviar respuesta', f'enviar_{numero_pregunta}_{archivo_seleccionado}')])
        buttons.append([Button.inline('🔙 Volver al tema', f'archivo_{archivo_seleccionado}')])

        await event.edit(f'{texto_pregunta}\n\n{texto_opciones}', buttons=buttons)

    if data.startswith('enviar_'):
        _, numero_pregunta, archivo_seleccionado = data.split('_', 2)
        preguntas = obtener_preguntas_desde_archivo(archivo_seleccionado)
        pregunta, opciones = preguntas[int(numero_pregunta) - 1]
        selecciones = selecciones_pregunta[archivo_seleccionado][int(numero_pregunta) - 1]

        if not any(selecciones):
            await event.answer("Por favor, selecciona al menos una opción antes de enviar las respuestas.", alert=True)
            return

        seleccion_incorrecta = any(seleccion and not correcta for seleccion, (_, correcta) in zip(selecciones, opciones))
        total_correctas = sum(1 for _, correcta in opciones if correcta)

        if seleccion_incorrecta:
            puntuacion = 0
        else:
            correctas_seleccionadas = sum(seleccion for seleccion, (_, correcta) in zip(selecciones, opciones) if correcta)
            puntuacion = (correctas_seleccionadas / total_correctas) * 100 if total_correctas > 0 else 0

        resultado = "Respuestas:\n"
        for i, (opcion, correcta) in enumerate(opciones):
            if selecciones[i]:
                resultado += f"{chr(65 + i)} - {'Correcta' if correcta else 'Incorrecta'}\n"

        if puntuacion == 0 and total_correctas > 1:
            resultado += f"\nPuntuación: {puntuacion:.0f}%\n\nUna sola respuesta incorrecta anula el resto de respuestas."
        else:
            resultado += f"\nPuntuación: {puntuacion:.0f}%"

        tema_pregunta = ''.join(re.findall(r'\d+', archivo_seleccionado))
        user_id = str(event.sender_id)
        puntuacion_texto = f"{puntuacion:.0f}%"
        clave_respuesta = (tema_pregunta, numero_pregunta, puntuacion_texto)
        guardar_csv(user_id, [clave_respuesta])

        if user_id not in respuestas_de_usuarios:
            respuestas_de_usuarios[user_id] = {}
        clave_respuesta = (tema_pregunta, numero_pregunta)
        
        if clave_respuesta not in respuestas_de_usuarios[user_id]:
            respuestas_de_usuarios[user_id][clave_respuesta] = []
        
        respuestas_de_usuarios[user_id][clave_respuesta].append(f"{puntuacion:.0f}%")

        selecciones_pregunta[archivo_seleccionado][int(numero_pregunta) - 1] = [False] * len(opciones)

        await event.answer(resultado, alert=True)

        if puntuacion == 100:
            buttons = []
            for i, _ in enumerate(preguntas, start=1):
                estado = obtener_estado_pregunta(user_id, archivo_seleccionado, i)
                boton_texto = f'Pregunta {i} {estado}'
                buttons.append([Button.inline(boton_texto, f'preg_{i}_{archivo_seleccionado}')])
            buttons.append([Button.inline('🏠 Volver al inicio', 'start')])
            await event.edit('Elige una pregunta:', buttons=buttons)
        else:
            instruccion_pregunta = "la única opción correcta:" if total_correctas == 1 else f"las {total_correctas} respuestas correctas:"
            texto_pregunta = f"{pregunta}\n\nSeleccione {instruccion_pregunta}"
            texto_opciones = "\n".join([f"{chr(65 + i)}. {opcion[0]}" for i, opcion in enumerate(opciones)])
            buttons = generar_botones_pregunta([False] * len(opciones), numero_pregunta, archivo_seleccionado)
            buttons.append([Button.inline('📤 Enviar respuesta', f'enviar_{numero_pregunta}_{archivo_seleccionado}')])
            buttons.append([Button.inline('🔙 Volver al tema', f'archivo_{archivo_seleccionado}')])
            await event.edit(f'{texto_pregunta}\n\n{texto_opciones}', buttons=buttons)

    elif data == 'start':
        archivos = listar_archivos_preguntas('tema_')
        buttons = [[Button.inline(f'{archivo.replace(".txt", "").replace("_", " ").title()}', f'archivo_{archivo}')] for archivo in archivos]
        await event.edit('Elige un tema:', buttons=buttons)

def obtener_estado_pregunta(user_id, archivo, numero_pregunta):
    tema_pregunta = ''.join(re.findall(r'\d+', archivo))
    clave_respuesta = (tema_pregunta, str(numero_pregunta))
    if user_id in respuestas_de_usuarios and clave_respuesta in respuestas_de_usuarios[user_id]:
        puntuaciones = respuestas_de_usuarios[user_id][clave_respuesta]
        if any(p == "100%" for p in puntuaciones):
            return " ✅"
        return " ❌"
    return ""

def generar_botones_pregunta(selecciones, num_pregunta, archivo):
    letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    buttons = []
    fila = []
    for i, seleccionada in enumerate(selecciones):
        texto_opcion = f'✅ {letras[i]}' if seleccionada else letras[i]
        fila.append(Button.inline(texto_opcion, f'select_{num_pregunta}_{i}_{archivo}'))
        if len(fila) == 4:
            buttons.append(fila)
            fila = []
    if fila:
        buttons.append(fila)
    return buttons

client.start()
client.run_until_disconnected()
client.disconnect()
