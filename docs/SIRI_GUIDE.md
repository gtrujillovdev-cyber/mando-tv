# Guía Paso a Paso: Integración de Atajos de Voz con Apple Siri

Esta guía detalla cómo configurar **Atajos de Apple (Apple Shortcuts)** en iPhone, iPad, Mac o Apple Watch para controlar tus televisores por voz con respuesta hablada natural en español, **de forma individual para cada televisión (LG 65" o Xiaomi MiTV) o de forma unificada (ambas teles a la vez)**.

---

## 1. Hub Visual de Atajos en el Mando

El servidor incorpora una página visual dedicada en:
`http://<IP_SERVIDOR>:8899/siri`

En ella puedes:
- 🔘 **Filtrar por dispositivo:** Botones para ver atajos de **LG**, **Xiaomi** o **Ambas**.
- 📋 **Copiar la URL exacta:** Con un solo clic en el botón "Copiar".
- 🔊 **Probar la voz en directo:** Escuchar la respuesta exacta que te dará Siri mediante el botón **"Probar"** (Web Speech API).

---

## 2. Cómo Crear un Atajo en iPhone (Solo 2 Acciones)

```text
┌──────────────────────────────────────────────────────────────────┐
│  Acción 1: Obtener contenido de URL                              │
│  URL: http://192.168.1.205:8899/api/siri?action=encender&target=lg
│  Método: GET                                                     │
└──────────────────────────────────────────────────────────────────┘
                                  │ (Pasa el texto de respuesta)
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│  Acción 2: Leer texto con la voz                                 │
│  Texto: [Contenido de URL]                                      │
│  Idioma: Español                                                 │
└──────────────────────────────────────────────────────────────────┘
```

1. Abre **Atajos (Shortcuts)** en tu iPhone.
2. Pulsa en **`+`** (arriba a la derecha).
3. Añade la acción **"Obtener contenido de la URL"** y pega el enlace del comando que deseas.
4. Añade la acción **"Leer texto con la voz"**.
5. Nombra el atajo con la frase exacta que le dirás a Siri (ej. *"Enciende la tele LG"*).

---

## 3. Catálogo de Comandos de Voz por Dispositivo

### 🔵 Para LG 65" (webOS)

| Frase que le dices a Siri | URL del Webhook | Respuesta Hablada de Siri |
| :--- | :--- | :--- |
| **"Oye Siri, enciende la tele LG"** | `/api/siri?action=encender&target=lg` | *"Televisión LG encendida."* |
| **"Oye Siri, apaga la tele LG"** | `/api/siri?action=apagar&target=lg` | *"Televisión LG apagada."* |
| **"Oye Siri, modo noche en la LG"** | `/api/siri?action=noche&target=lg` | *"Modo Noche activado en la televisión LG. Retroiluminación al 6% y temporizador de 90 minutos."* |
| **"Oye Siri, modo día en la LG"** | `/api/siri?action=dia&target=lg` | *"Modo Día activado en la televisión LG con retroiluminación al 100%."* |
| **"Oye Siri, modo cine en la LG"** | `/api/siri?action=cine&target=lg` | *"Modo Cine activado en la televisión LG."* |
| **"Oye Siri, pon Netflix en la LG"** | `/api/siri?action=reproducir&platform=netflix&target=lg` | *"Abriendo Netflix en la televisión LG."* |

---

### 🟠 Para Xiaomi MiTV (Android TV)

| Frase que le dices a Siri | URL del Webhook | Respuesta Hablada de Siri |
| :--- | :--- | :--- |
| **"Oye Siri, enciende la Xiaomi"** | `/api/siri?action=encender&target=xiaomi` | *"Televisión Xiaomi encendida."* |
| **"Oye Siri, apaga la Xiaomi"** | `/api/siri?action=apagar&target=xiaomi` | *"Televisión Xiaomi apagada y en modo de bajo consumo."* |
| **"Oye Siri, modo noche en la Xiaomi"** | `/api/siri?action=noche&target=xiaomi` | *"Modo Noche activado en la Xiaomi. Retroiluminación tenue y temporizador de 90 minutos."* |
| **"Oye Siri, modo día en la Xiaomi"** | `/api/siri?action=dia&target=xiaomi` | *"Modo Día activado en la Xiaomi con retroiluminación al 100%."* |
| **"Oye Siri, pon SmartTube"** | `/api/siri?action=reproducir&platform=smarttube&target=xiaomi` | *"Abriendo SmartTube en la Xiaomi."* |
| **"Oye Siri, pon Spotify en la Xiaomi"** | `/api/siri?action=reproducir&platform=spotify&target=xiaomi` | *"Abriendo Spotify en la Xiaomi."* |

---

### 🟣 Comandos Maestros (Ambas Pantallas / Salón)

| Frase que le dices a Siri | URL del Webhook | Respuesta Hablada de Siri |
| :--- | :--- | :--- |
| **"Oye Siri, enciende las teles"** | `/api/siri?action=encender&target=ambas` | *"Ambas televisiones encendidas."* |
| **"Oye Siri, apaga las teles"** | `/api/siri?action=apagar&target=ambas` | *"Ambas televisiones apagadas."* |
| **"Oye Siri, modo noche en el salón"** | `/api/siri?action=noche&target=ambas` | *"Modo Noche activado en ambas televisiones con retroiluminación al 6% y temporizador de 90 minutos."* |
| **"Oye Siri, estado de las teles"** | `/api/siri?action=status` | *"Estado actual: La televisión LG está encendida y la televisión Xiaomi está en espera."* |
