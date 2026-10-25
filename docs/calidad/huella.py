#!/usr/bin/env python3
"""Huella reproducible del arbol revisado.

Receta (fijada el 12-oct-2026, sustituye al md5 de las revisiones 1-3, cuya receta
no quedo anotada y no he podido reproducir con 14 variantes):

    sha256 sobre, para cada fichero de core/, app/ y tests/ ordenado por ruta
    relativa POSIX, la ruta + '\\0' + el contenido en bytes + '\\0'.
    Se excluyen __pycache__/ y *.pyc.

Uso:  python3 huella.py <raiz-del-proyecto>
"""
import hashlib
import pathlib
import sys

DIRS = ("core", "app", "tests")


def huella(raiz: pathlib.Path) -> tuple[str, int]:
    ficheros = []
    for d in DIRS:
        for p in (raiz / d).rglob("*"):
            if p.is_dir() or "__pycache__" in p.parts or p.suffix == ".pyc":
                continue
            ficheros.append(p)
    ficheros.sort(key=lambda p: p.relative_to(raiz).as_posix())
    h = hashlib.sha256()
    for p in ficheros:
        h.update(p.relative_to(raiz).as_posix().encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest(), len(ficheros)


if __name__ == "__main__":
    raiz = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    v, n = huella(raiz)
    print(f"{v}  ({n} ficheros)  {raiz}")
