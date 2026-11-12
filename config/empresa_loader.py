"""Carga la configuración privada o utiliza valores de ejemplo seguros."""

from copy import deepcopy

from config.empresa_ejemplo import EMPRESA as EMPRESA_EJEMPLO


def obtener_datos_empresa():
    """Devuelve datos privados locales si existen; si no, usa la plantilla vacía."""
    try:
        from config.empresa import EMPRESA
    except ModuleNotFoundError as error:
        # No ocultar errores de importación internos de empresa.py.
        if error.name != "config.empresa":
            raise
        return deepcopy(EMPRESA_EJEMPLO)

    return deepcopy(EMPRESA)
