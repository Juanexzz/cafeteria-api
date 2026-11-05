from contextlib import asynccontextmanager
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.logging_config import setup_logging, stop_logging, get_logger
from app.metrics import (
    registrar_pedido_creado,
    registrar_producto_inexistente,
    start_metrics_worker,
    stop_metrics_worker,
)

logger = get_logger("cafeteria-api")

# Menú en memoria con 5 productos y sus precios
MENU: Dict[str, float] = {
    "cafe": 1.50,
    "croissant": 2.00,
    "te": 1.20,
    "tostada": 2.50,
    "bocadillo": 3.80,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialización de logging y worker de métricas en segundo plano
    setup_logging()
    start_metrics_worker()
    logger.info("Aplicación cafeteria-api iniciada correctamente")
    yield
    # Limpieza al apagar el servidor
    logger.info("Deteniendo cafeteria-api...")
    stop_metrics_worker()
    stop_logging()


app = FastAPI(
    title="Cafetería API",
    description="API de cafetería para monitoreo con Prometheus, Grafana y ELK",
    version="1.0.0",
    lifespan=lifespan,
)

# Instrumentación Prometheus
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/api/menu")
def obtener_menu() -> List[Dict[str, object]]:
    """Devuelve la lista de 5 productos disponibles en la cafetería con su precio."""
    logger.info("Consultando menú")
    return [{"producto": item, "precio": precio} for item, precio in MENU.items()]


@app.get("/api/pedir/{producto}")
def pedir_producto(producto: str):
    """Crea un pedido si el producto existe en el menú; de lo contrario responde 404."""
    prod_key = producto.lower().strip()
    if prod_key in MENU:
        registrar_pedido_creado(prod_key)
        logger.info(f"Pedido creado: {producto}")
        return {
            "mensaje": "Pedido recibido con éxito",
            "producto": prod_key,
            "precio": MENU[prod_key],
            "estado": "en_preparacion",
        }

    registrar_producto_inexistente()
    logger.error(f"Producto no existe: {producto}")
    raise HTTPException(status_code=404, detail=f"Producto no existe: {producto}")


@app.get("/api/simular-fallo")
def simular_fallo():
    """Lanza una excepción controlada, la registra con logger.exception y responde 500."""
    try:
        raise RuntimeError("Fallo simulado controlado en Cafetería API")
    except Exception as exc:
        logger.exception("Fallo simulado capturado en /api/simular-fallo")
        return JSONResponse(
            status_code=500,
            content={"error": "Fallo simulado", "detalle": str(exc)},
        )


@app.get("/health")
def health():
    """Endpoint de verificación de salud sin generación de logs."""
    return {"status": "ok"}
