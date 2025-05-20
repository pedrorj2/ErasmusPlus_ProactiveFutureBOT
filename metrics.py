import csv

def ranking_usuarios(archivo='respuestas.csv'):
    mejores_puntuaciones = {}
    
    with open(archivo, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 4:
                username, tema_pregunta, numero_pregunta, puntuacion, *_ = row
                clave = (username, tema_pregunta, numero_pregunta)
                puntuacion = int(puntuacion.replace('%', ''))
                
                if clave not in mejores_puntuaciones or puntuacion > mejores_puntuaciones[clave]:
                    mejores_puntuaciones[clave] = puntuacion

    ranking = {}
    for (username, tema_pregunta, numero_pregunta), puntuacion in mejores_puntuaciones.items():
        if username not in ranking:
            ranking[username] = 0
        ranking[username] += puntuacion
    
    ranking_ordenado = sorted(ranking.items(), key=lambda x: x[1], reverse=True)
    return ranking_ordenado

def media_intentos(archivo='respuestas.csv'):
    with open(archivo, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        intentos = {}
        for row in reader:
            if len(row) >= 4:
                username, tema_pregunta, numero_pregunta, puntuacion, _ = row
                if username not in intentos:
                    intentos[username] = 0
                intentos[username] += 1
        intentos_medios = sum(intentos.values()) / len(intentos)
        return intentos_medios

def lista_usuarios(archivo='respuestas.csv'):
    usuarios = set()
    with open(archivo, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 4:
                username, *_ = row
                usuarios.add(username)
    return list(usuarios)
