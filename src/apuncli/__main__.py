"""Punto de entrada de apuncli."""

import sys

from .argumentos import ejecutar
from .errores import ApuncliError


def main() -> int:
    try:
        return ejecutar()
    except ApuncliError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
