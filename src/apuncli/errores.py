"""Errores de apuncli, jerarquía propia con mensajes humanos."""


class ApuncliError(Exception):
    """Error con un mensaje pensado para mostrarse directamente al usuario."""


class ConfigError(ApuncliError):
    """La configuración (acciones.json) no es válida. Código de salida: 3."""

    def __init__(self, problemas):
        if isinstance(problemas, str):
            problemas = [problemas]
        self.problemas = list(problemas)
        super().__init__("; ".join(self.problemas))


class AccionNoValida(ApuncliError):
    """La acción pedida no existe en la configuración."""


class FalloEjecucion(ApuncliError):
    """La acción falló a mitad de camino. Código de salida: 1."""


class SinRedError(ApuncliError):
    """No hay proveedor de IA disponible (sin red o sin clave)."""
