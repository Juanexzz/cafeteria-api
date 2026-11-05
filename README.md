# Cafetería API (`cafeteria-api`)

API REST desarrollada con **FastAPI** para el reto de observabilidad y monitoreo integral con **Prometheus**, **Grafana** y el stack **ELK (Elasticsearch, Logstash, Kibana)**.

El nombre de la aplicación registrado en logs y configuración es estrictamente `cafeteria-api` (en minúsculas).

---

## Tabla de Puertos del Ecosistema

| Servicio | Puerto Host | Protocolo | Descripción |
|---|---|---|---|
| **Cafetería API** | `8000` | HTTP / TCP | API REST FastAPI (`0.0.0.0:8000`) |
| **Logstash** | `5001` | TCP | Ingesta de logs JSON vía TCP (`localhost:5001`) |
| **Elasticsearch** | `9200` | HTTP | Almacenamiento e indexación de logs (`localhost:9200`) |
| **Kibana** | `5601` | HTTP | Interfaz de visualización de logs ELK (`localhost:5601`) |
| **Prometheus** | `9090` | HTTP | Servidor de recolección de métricas (`localhost:9090`) |
| **Grafana** | `3100` | HTTP | Dashboards y visualización de métricas (`localhost:3100`) |

---

## Requisitos Previos

- **Python 3.10+** (probado con Python 3.14 en Windows / PowerShell).
- Opcional: Stack ELK y Prometheus / Grafana en ejecución (contenedores Docker).

---

## Instalación y Configuración del Entorno

1. **Clonar o situarse en el directorio del proyecto:**
   ```powershell
   cd C:\Users\juanv\PycharmProjects\cafeteria-api
   ```

2. **Crear el entorno virtual:**
   ```powershell
   python -m venv .venv
   ```

3. **Activar el entorno virtual:**
   - En Windows (PowerShell):
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - En Linux / macOS (Bash):
     ```bash
     source .venv/bin/activate
     ```

4. **Instalar dependencias fijadas:**
   ```powershell
   pip install -r requirements.txt
   ```

---

## Ejecución de la API

Para arrancar el servidor en modo desarrollo escuchando en todas las interfaces (`0.0.0.0`) y puerto `8000`:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Para activar recarga automática en desarrollo:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Endpoints de la API

Los datos se mantienen en memoria (sin base de datos):

| Método | Endpoint | Descripción | Código HTTP | Logging |
|---|---|---|---|---|
| `GET` | `/health` | Chequeo de salud (`{"status":"ok"}`) | 200 | Silencioso (sin logs en app ni uvicorn) |
| `GET` | `/api/menu` | Lista de 5 productos con su precio | 200 | `INFO: Consultando menú` |
| `GET` | `/api/pedir/{producto}` | Realiza un pedido del menú | 200 si existe / 404 si no | `INFO: Pedido creado: <prod>` / `ERROR: Producto no existe: <prod>` |
| `GET` | `/api/simular-fallo` | Dispara fallo controlado con stack trace | 500 | `ERROR` con stack trace mediante `logger.exception` |
| `GET` | `/metrics` | Métricas en formato Prometheus | 200 | Exportador Prometheus |

### Menú Disponible
- `cafe`: \$1.50
- `croissant`: \$2.00
- `te`: \$1.20
- `tostada`: \$2.50
- `bocadillo`: \$3.80

---

## Métricas Prometheus (`/metrics`)

La aplicación expone métricas usando `prometheus-fastapi-instrumentator` y métricas personalizadas con `prometheus-client`:

1. **Métricas HTTP estándar (Instrumentator):**
   - `http_requests_total`: Total de peticiones clasificadas por `handler`, `method` y `status` (2xx, 4xx, 5xx).
   - `http_request_duration_seconds`: Histogramas de duración/latencia por endpoint.
   - `http_request_duration_highr_seconds`: Histograma de alta resolución para percentiles (p90, p95, p99).

2. **Métricas de negocio personalizadas:**
   - `cafeteria_pedidos_creados_total` (Counter, etiqueta `producto`): Cuenta los pedidos realizados con éxito por producto.
   - `cafeteria_productos_inexistentes_total` (Counter): Cuenta las peticiones de productos fuera de carta (404).
   - `cafeteria_pedidos_en_cola` (Gauge): Número de pedidos en espera de preparación. Se incrementa al pedir un producto y decrece con un hilo de fondo (`WorkerColaPedidos`) que despacha 1 pedido cada 5 segundos.

---

## Sistema de Logging JSON hacia Logstash

El sistema de logs está desacoplado y no bloquea el ciclo de peticiones:

- **Estructura JSON por línea (`\n`):**
  - `@timestamp`: Fecha y hora en formato ISO 8601 UTC con milisegundos y sufijo `Z` (ej. `2026-11-05T18:35:53.460Z`).
  - `level`: Nivel del registro (`INFO`, `ERROR`, etc.).
  - `message`: Mensaje del evento.
  - `logger_name`: Nombre del logger emisor.
  - `thread_name`: Hilo donde ocurrió el evento.
  - `application`: `"cafeteria-api"` (en minúsculas).
  - `stack_trace`: Traza de error completa (presente cuando se produce una excepción con `logger.exception`).
- **Envío no bloqueante:** Emplea `RawQueueHandler` + `QueueListener` en un hilo dedicado con cola en memoria.
- **Tolerancia a fallos:** El handler `LogstashTCPHandler` conecta por TCP a `localhost:5001` con timeout de 1 segundo y reconexión automática. Si Logstash está apagado o no responde, el log se descarta silenciosamente sin interrumpir el funcionamiento ni ralentizar la API.
- **Salida simultánea en consola:** Muestra trazas legibles en la salida estándar (`sys.stdout`).

---

## Generación de Tráfico de Prueba

Se incluye un script basado únicamente en la librería estándar de Python (`urllib`):

```powershell
python scripts/generar_trafico.py --rondas 30 --pausa 0.1
```

Opciones:
- `--host`: Dirección del host (por defecto: `localhost`).
- `--port`: Puerto de la API (por defecto: `8000`).
- `--rondas` / `-r`: Número de ciclos de peticiones (por defecto: `30`).
- `--pausa` / `-p`: Tiempo de espera en segundos entre peticiones (por defecto: `0.1`).

Al finalizar muestra un resumen detallado con códigos de respuesta y peticiones por endpoint.

---

## Importación del Dashboard en Grafana

El archivo `dashboards/cafeteria-api.json` está preparado con la variable de entrada `DS_PROMETHEUS` para una importación inmediata:

1. Abrir la interfaz de Grafana en el navegador: [http://localhost:3100](http://localhost:3100) (o el puerto configurado).
2. Ir a **Dashboards** > **New** > **Import**.
3. Seleccionar **Upload JSON file** y cargar `dashboards/cafeteria-api.json`.
4. En el desplegable del origen de datos, seleccionar la conexión Prometheus (`DS_PROMETHEUS`).
5. Hacer clic en **Import**.

### Paneles incluidos:
1. **Estado de la API**: Visualización tipo Stat de `up{job="cafeteria-api"}` (UP en verde, DOWN en rojo).
2. **Peticiones por Segundo por Endpoint**: Tasa de tráfico (`req/s`) desglosada por handler.
3. **Peticiones por Código de Estado**: Series temporales para respuestas `2xx`, `4xx` y `5xx`.
4. **Latencia p95 por Endpoint**: Percentil 95 de tiempo de respuesta calculado con histogramas.
5. **Pedidos Creados por Producto**: Tasa de pedidos exitosos por tipo de producto.
6. **Pedidos en Cola y Productos Inexistentes**: Evolución del Gauge de pedidos en cola y total/tasa de productos no encontrados.
