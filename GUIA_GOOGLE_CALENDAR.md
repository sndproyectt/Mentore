# 🗓️ Guía: Conectar Google Calendar API con Mentore

## ¿Qué necesitas?
Una cuenta de Google y acceso a Google Cloud Console (gratis).

---

## PASO 1 — Crear proyecto en Google Cloud

1. Ve a → https://console.cloud.google.com/
2. Haz clic en el selector de proyectos (arriba a la izquierda)
3. Clic en **"Nuevo proyecto"**
4. Nombre: `Mentore` (o el que prefieras)
5. Clic en **"Crear"**

---

## PASO 2 — Activar la API de Google Calendar

1. En el menú lateral ve a **"APIs y servicios" → "Biblioteca"**
2. Busca: `Google Calendar API`
3. Haz clic en ella y luego en **"Habilitar"**

---

## PASO 3 — Configurar pantalla de consentimiento OAuth

1. Ve a **"APIs y servicios" → "Pantalla de consentimiento de OAuth"**
2. Selecciona **"Externo"** → Clic en **"Crear"**
3. Rellena:
   - **Nombre de la app:** Mentore
   - **Correo de asistencia:** tu correo de Google
   - **Correo del desarrollador:** tu correo de Google
4. Clic en **"Guardar y continuar"**
5. En **Permisos (Scopes)**: clic en **"Agregar o quitar permisos"**
   - Busca y selecciona: `https://www.googleapis.com/auth/calendar`
   - Clic en **"Actualizar"** → **"Guardar y continuar"**
6. En **Usuarios de prueba**: agrega tu correo de Google
7. Clic en **"Guardar y continuar"** → **"Volver al panel"**

---

## PASO 4 — Crear credenciales OAuth 2.0

1. Ve a **"APIs y servicios" → "Credenciales"**
2. Clic en **"+ Crear credenciales" → "ID de cliente de OAuth"**
3. Tipo de aplicación: **"Aplicación web"**
4. Nombre: `Mentore Web`
5. En **"URIs de redireccionamiento autorizados"**, agrega:
   ```
   http://localhost:8000/dashboard/calendar/oauth/callback/
   ```
   *(Si usas otro puerto, ajústalo)*
6. Clic en **"Crear"**
7. Se mostrará tu **Client ID** y **Client Secret** → ¡Cópialos!

---

## PASO 5 — Pegar credenciales en Mentore

Abre el archivo `mentore/settings.py` y busca al final:

```python
GOOGLE_CLIENT_ID = ''       # ← Pega aquí tu Client ID
GOOGLE_CLIENT_SECRET = ''   # ← Pega aquí tu Client Secret
```

Reemplaza con tus valores, por ejemplo:

```python
GOOGLE_CLIENT_ID = '123456789-abcdef.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'GOCSPX-xxxxxxxxxxxxxxx'
```

---

## PASO 6 — Aplicar migración de base de datos

Ejecuta en la terminal, dentro de la carpeta del proyecto:

```bash
python manage.py migrate
```

---

## PASO 7 — Probar la conexión

1. Inicia el servidor: `python manage.py runserver`
2. Ve a → http://localhost:8000/dashboard/calendar/
3. Haz clic en **"Conectar Google Calendar"**
4. Autoriza el acceso con tu cuenta de Google
5. ¡Listo! Tus eventos aparecerán en el calendario de Mentore

---

## ⚠️ Notas importantes

- Mientras la app esté en modo "prueba" en Google Cloud, solo los correos que agregues como **usuarios de prueba** podrán conectarse.
- Si vas a usar esto con muchos usuarios, deberás publicar la app (proceso de verificación de Google).
- Las credenciales (`GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`) son privadas — **nunca las subas a GitHub**.

---

## 🔁 Flujo de funcionamiento

```
Profe hace clic "Conectar Google Calendar"
        ↓
Mentore redirige a Google (OAuth2)
        ↓
Google pide autorización al profe
        ↓
Google redirige de vuelta a Mentore con un "code"
        ↓
Mentore intercambia el code por access_token + refresh_token
        ↓
Mentore guarda los tokens en la BD (tabla GoogleCalendarToken)
        ↓
Mentore llama a Google Calendar API para leer/crear/eliminar eventos
        ↓
Los eventos aparecen en el calendario de Mentore ✅
```
