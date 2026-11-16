"""Detecta qué librerías de terceros usa el programa y si están instaladas.

Uso (con el entorno virtual activo):
    python scripts/verificar_dependencias.py             # solo muestra el informe
    python scripts/verificar_dependencias.py --escribir  # además genera requirements.txt

Sirve para armar requirements.txt a partir de lo que el código REALMENTE importa,
y para detectar rápido qué falta instalar en otra computadora.
"""

import ast
import os
import sys
from importlib import metadata
from pathlib import Path

# Raíz del proyecto: la carpeta que contiene app.py (sirve desde la raíz o desde scripts/)
BASE = Path(__file__).resolve().parent
if not (BASE / "app.py").exists():
    BASE = BASE.parent

# Solo se analiza el código que necesita el programa para funcionar
A_ANALIZAR = ["app.py", "routes", "services", "utils", "database"]


def archivos_python():
    for nombre in A_ANALIZAR:
        ruta = BASE / nombre
        if ruta.is_file():
            yield ruta
        elif ruta.is_dir():
            for raiz, carpetas, archivos in os.walk(ruta):
                carpetas[:] = [c for c in carpetas if c != "__pycache__"]
                for a in archivos:
                    if a.endswith(".py"):
                        yield Path(raiz) / a


def modulos_importados(ruta):
    """Devuelve los nombres de módulo de más alto nivel que importa un archivo."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                yield alias.name.split(".")[0]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            yield nodo.module.split(".")[0]


def main():
    escribir = "--escribir" in sys.argv

    # Nombres propios del proyecto (carpetas y archivos .py): no son librerías externas
    propios = {p.stem for p in BASE.glob("*.py")}
    for nombre in A_ANALIZAR:
        propios.add(Path(nombre).stem)
        carpeta = BASE / nombre
        if carpeta.is_dir():
            propios.update(p.stem for p in carpeta.rglob("*.py"))

    usados = {}  # módulo -> archivos que lo importan
    for archivo in archivos_python():
        for mod in modulos_importados(archivo):
            if mod in sys.stdlib_module_names or mod in propios or mod == "__future__":
                continue
            usados.setdefault(mod, set()).add(archivo.relative_to(BASE).as_posix())

    # Qué paquete de pip provee cada módulo (ej. 'dotenv' -> 'python-dotenv')
    paquetes = metadata.packages_distributions()
    requeridos, faltantes = [], []
    print("Librerías de terceros que usa el programa:\n")
    for mod in sorted(usados):
        donde = ", ".join(sorted(usados[mod]))
        if mod in paquetes:
            dist = paquetes[mod][0]
            version = metadata.version(dist)
            requeridos.append(f"{dist}=={version}")
            print(f"  OK        {mod:<12} -> {dist}=={version}   (usado en: {donde})")
        else:
            faltantes.append(mod)
            print(f"  FALTA     {mod:<12} -> no está instalado       (usado en: {donde})")

    if faltantes:
        print("\n[ATENCIÓN] Hay librerías sin instalar. Ejecutá:  pip install -r requirements.txt")
        print("Si ese archivo no las incluye, instalalas a mano y volvé a correr este script con --escribir.")

    if escribir:
        if faltantes:
            sys.exit("\nNo se escribió requirements.txt: primero instalá lo que falta.")
        destino = BASE / "requirements.txt"
        destino.write_text("\n".join(sorted(requeridos, key=str.lower)) + "\n", encoding="utf-8")
        print(f"\n[OK] requirements.txt actualizado en {destino}")
        print("     (Flask instala solo Werkzeug, Jinja2 y demás dependencias internas).")


if __name__ == "__main__":
    main()
