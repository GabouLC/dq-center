"""Levanta la API en local: python -m dqc.api [--puerto 8000]."""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument("--recargar", action="store_true", help="reiniciar al cambiar el código")
    args = parser.parse_args()
    uvicorn.run("dqc.api.main:app", host="127.0.0.1", port=args.puerto, reload=args.recargar)


if __name__ == "__main__":
    main()
