import json
import logging
from logging.handlers import QueueHandler, QueueListener
import queue
import socket
import sys
from datetime import datetime, timezone
from typing import Optional

APPLICATION_NAME = "cafeteria-api"


class HealthFilter(logging.Filter):
    """Filtro para ignorar las peticiones hacia /health tanto en aplicación como en uvicorn."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/health" not in msg


class RawQueueHandler(QueueHandler):
    """
    QueueHandler que no agranda ni aplana las excepciones en record.msg,
    permitiendo que los formatters de destino procesen exc_info y exc_text de forma independiente.
    """
    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        return record


class LogstashJSONFormatter(logging.Formatter):
    """Formateador JSON con los campos requeridos para Logstash."""
    def format(self, record: logging.LogRecord) -> str:
        # ISO 8601 UTC con milisegundos y sufijo Z (ej: 2026-11-05T18:32:54.123Z)
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        log_data = {
            "@timestamp": timestamp,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
            "thread_name": record.threadName,
            "application": APPLICATION_NAME,
        }

        if record.exc_info:
            log_data["stack_trace"] = self.formatException(record.exc_info)
        elif getattr(record, "exc_text", None):
            log_data["stack_trace"] = record.exc_text

        return json.dumps(log_data, ensure_ascii=False)


class LogstashTCPHandler(logging.Handler):
    """Handler TCP personalizado con timeout de 1s y reconexión automática."""
    def __init__(self, host: str = "127.0.0.1", port: int = 5001, timeout: float = 1.0):
        super().__init__()
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def _connect(self) -> bool:
        if self.sock is not None:
            return True
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            self.sock = sock
            return True
        except Exception:
            self._close_socket()
            return False

    def _close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            if not msg.endswith("\n"):
                msg += "\n"
            data = msg.encode("utf-8")
            if not self._connect():
                return
            assert self.sock is not None
            self.sock.sendall(data)
        except Exception:
            self._close_socket()

    def close(self):
        self._close_socket()
        super().close()


_queue_listener: Optional[QueueListener] = None
_log_queue: queue.Queue = queue.Queue(maxsize=10000)


def setup_logging(host: str = "127.0.0.1", port: int = 5001):
    global _queue_listener

    if _queue_listener is not None:
        return

    # Handler TCP Logstash
    tcp_handler = LogstashTCPHandler(host=host, port=port, timeout=1.0)
    tcp_handler.setFormatter(LogstashJSONFormatter())
    tcp_handler.addFilter(HealthFilter())

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] [%(threadName)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(HealthFilter())

    # Listener en segundo plano (tcp_handler primero para capturar exc_info)
    _queue_listener = QueueListener(
        _log_queue,
        tcp_handler,
        console_handler,
        respect_handler_level=True,
    )
    _queue_listener.start()

    # QueueHandler hacia la cola
    queue_handler = RawQueueHandler(_log_queue)
    queue_handler.addFilter(HealthFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(queue_handler)

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        l = logging.getLogger(logger_name)
        l.handlers.clear()
        l.addHandler(queue_handler)
        l.propagate = False


def stop_logging():
    global _queue_listener
    if _queue_listener is not None:
        _queue_listener.stop()
        _queue_listener = None


def get_logger(name: str = "cafeteria-api") -> logging.Logger:
    return logging.getLogger(name)
