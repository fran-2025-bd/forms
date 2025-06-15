from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import unicodedata
import os

app = Flask(__name__)
app.secret_key = 'clave_super_segura'

# Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

cred_dict = json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_dict, scope)
client = gspread.authorize(creds)
spreadsheet = client.open("prueba")
sheet = spreadsheet.worksheet("bd1")

# Credenciales hardcodeadas
USERS = {
    "admin": {"password": "1234", "role": "admin"},
    "concejal": {"password": "5678", "role": "lectura"}
}

# ================= FUNCIONES =================

def normalizar(texto):
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in texto if not unicodedata.combining(c))

# ================= LOGIN =================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = USERS.get(username)
        if user and user["password"] == password:
            session['logged_in'] = True
            session['user'] = username
            session['role'] = user["role"]
            if user["role"] == "admin":
                return redirect(url_for('index'))
            else:
                return redirect(url_for('solo_lectura'))
        else:
            error = "Usuario o contraseña incorrectos"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= ADMIN =================

@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in') or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        sheet.append_row([nombre, email])
        flash("Datos guardados con éxito", "success")

    return render_template('menu_admin.html')

# ================= SOLO LECTURA =================

@app.route('/solo_lectura')
def solo_lectura():
    if not session.get('logged_in') or session.get('role') != 'lectura':
        return redirect(url_for('login'))

    registros = sheet.get_all_records()
    return render_template('solo_lectura.html', registros=registros)

# ================= API de artículos =================

@app.route('/api/articulos')
def api_articulos():
    query = request.args.get('q', '').strip().lower()
    query_normalizado = normalizar(query)

    with open('data/articulos.json', 'r', encoding='utf-8') as f:
        articulos = json.load(f)

    resultados = [
        a for a in articulos
        if query_normalizado in normalizar(a['titulo']) or query_normalizado in normalizar(a['contenido'])
    ] if query else []

    return jsonify(resultados)

# ================= Vista Reglamento =================

@app.route('/reglamento', methods=['GET', 'POST'])
def reglamento():
    with open("data/articulos.json", "r", encoding="utf-8") as f:
        articulos = json.load(f)

    # Soporte para búsqueda
    busqueda = request.form.get("busqueda", "").strip()
    normal_busqueda = normalizar(busqueda)
    resultados = []

    if normal_busqueda:
        for articulo in articulos:
            if normal_busqueda in normalizar(articulo.get("titulo", "")) or \
               normal_busqueda in normalizar(articulo.get("contenido", "")):
                resultados.append(articulo)

    # Soporte para selector individual de artículos
    titulos_articulos = [a['titulo'] for a in articulos]
    articulo_actual = None
    seleccion = request.form.get('articulo_seleccionado')
    if seleccion:
        articulo_actual = next((a for a in articulos if a['titulo'] == seleccion), None)

    return render_template('reglamento.html',
                           resultados=resultados,
                           busqueda=busqueda,
                           titulos=titulos_articulos,
                           articulo=articulo_actual)

# ================= MAIN =================

if __name__ == '__main__':
    app.run(debug=True)
