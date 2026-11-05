#!/usr/bin/env python3
"""
Script generador de tráfico para cafeteria-api.
Utiliza únicamente la librería estándar de Python (urllib).
"""

import argparse
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict


def realizar_peticion(url: str) -> int:
    """Envía una petición GET a la URL y devuelve el código de estado HTTP."""
    req = urllib.request.Request(url, headers={"User-Agent": "GeneradorTrafico/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        print(f"[ERROR] Conexión fallida hacia {url}: {e}", file=sys.stderr)
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generador de tráfico HTTP para cafeteria-api."
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host del servicio (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Puerto del servicio (default: 8000)",
    )
    parser.add_argument(
        "--rondas",
        "-r",
        type=int,
        default=30,
        help="Número de rondas de peticiones a ejecutar (default: 30)",
    )
    parser.add_argument(
        "--pausa",
        "-p",
        type=float,
        default=0.1,
        help="Pausa en segundos entre peticiones individuales (default: 0.1)",
    )

    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    endpoints = [
        "/api/menu",
        "/api/pedir/cafe",
        "/api/pedir/croissant",
        "/api/pedir/pizza",  # Producto inexistente (404 esperado)
        "/api/simular-fallo",  # Fallo controlado (500 esperado)
    ]

    conteo_estados = defaultdict(int)
    conteo_endpoints = defaultdict(lambda: defaultdict(int))
    total_peticiones = 0

    print("==================================================")
    print(f" Iniciando generación de tráfico hacia {base_url}")
    print(f" Rondas: {args.rondas} | Peticiones por ronda: {len(endpoints)}")
    print(f" Total estimado: {args.rondas * len(endpoints)} peticiones")
    print("==================================================")

    inicio = time.time()

    for ronda in range(1, args.rondas + 1):
        for path in endpoints:
            url = f"{base_url}{path}"
            status = realizar_peticion(url)
            total_peticiones += 1
            conteo_estados[status] += 1
            conteo_endpoints[path][status] += 1
            if args.pausa > 0:
                time.sleep(args.pausa)

        if ronda % 5 == 0 or ronda == args.rondas:
            print(f" -> Ronda {ronda}/{args.rondas} completada...")

    duracion = time.time() - inicio

    print("\n==================================================")
    print(" RESUMEN DE GENERACIÓN DE TRÁFICO")
    print("==================================================")
    print(f"Tiempo total: {duracion:.2f} segundos")
    print(f"Total de peticiones realizadas: {total_peticiones}")
    print(f"Rendimiento medio: {total_peticiones / duracion:.2f} req/s\n")

    print("Desglose por código de estado:")
    for status, count in sorted(conteo_estados.items()):
        porcentaje = (count / total_peticiones) * 100
        print(f"  HTTP {status}: {count} peticiones ({porcentaje:.1f}%)")

    print("\nDesglose por endpoint:")
    for path, estados in sorted(conteo_endpoints.items()):
        detalles = ", ".join(f"HTTP {st}: {cnt}" for st, cnt in sorted(estados.items()))
        print(f"  {path:20} -> {detalles}")
    print("==================================================")


if __name__ == "__main__":
    main()
