import threading
import time
from prometheus_client import Counter, Gauge

# Métricas personalizadas para Prometheus
cafeteria_pedidos_creados_total = Counter(
    "cafeteria_pedidos_creados_total",
    "Total de pedidos creados con éxito en la cafetería",
    ["producto"],
)

cafeteria_productos_inexistentes_total = Counter(
    "cafeteria_productos_inexistentes_total",
    "Total de intentos de pedidos de productos no existentes en el menú",
)

cafeteria_pedidos_en_cola = Gauge(
    "cafeteria_pedidos_en_cola",
    "Cantidad de pedidos actualmente en cola esperando preparación",
)

# Control del hilo de atención en segundo plano
_cola_lock = threading.Lock()
_stop_event = threading.Event()
_worker_thread: threading.Thread | None = None


def registrar_pedido_creado(producto: str) -> None:
    """Incrementa el contador de pedidos y el gauge de pedidos en cola."""
    cafeteria_pedidos_creados_total.labels(producto=producto).inc()
    with _cola_lock:
        cafeteria_pedidos_en_cola.inc()


def registrar_producto_inexistente() -> None:
    """Incrementa el contador de productos inexistentes."""
    cafeteria_productos_inexistentes_total.inc()


def _procesar_pedidos_loop() -> None:
    """Bucle del worker: atiende un pedido cada 5 segundos reduciendo el gauge."""
    while not _stop_event.is_set():
        with _cola_lock:
            try:
                # Comprobar valor actual del gauge
                actual = cafeteria_pedidos_en_cola._value.get()
                if actual > 0:
                    cafeteria_pedidos_en_cola.dec()
            except Exception:
                pass
        _stop_event.wait(5.0)


def start_metrics_worker() -> None:
    """Inicia el worker en segundo plano para atender pedidos de la cola."""
    global _worker_thread
    _stop_event.clear()
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(
            target=_procesar_pedidos_loop,
            daemon=True,
            name="WorkerColaPedidos",
        )
        _worker_thread.start()


def stop_metrics_worker() -> None:
    """Detiene el worker en segundo plano."""
    _stop_event.set()
    if _worker_thread is not None and _worker_thread.is_alive():
        _worker_thread.join(timeout=2.0)
