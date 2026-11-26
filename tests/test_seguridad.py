"""Pruebas de T-30: claves fuera de Git (RNF-01, RNF-02; spec, sección 10).

- ``.env`` está en ``.gitignore``.
- ``.env.example`` no tiene valores en las variables ``*_API_KEY``.
- Extra (decisión de Yeimy): ``git ls-files`` no incluye ``.env`` ni
  ``.streamlit/secrets.toml`` (criterio de aceptación de la sección 11).

Ninguna prueba lee ni imprime el contenido de ``.env``.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GITIGNORE = RAIZ / ".gitignore"
ENV_EXAMPLE = RAIZ / ".env.example"
ARCHIVOS_SECRETOS = (".env", ".streamlit/secrets.toml")


def reglas_gitignore() -> list[str]:
    lineas = GITIGNORE.read_text(encoding="utf-8").splitlines()
    return [linea.strip() for linea in lineas if linea.strip() and not linea.strip().startswith("#")]


def variables_del_ejemplo() -> dict[str, str]:
    variables = {}
    for linea in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            nombre, valor = linea.split("=", 1)
            variables[nombre.strip()] = valor.strip()
    return variables


# ---------- las dos pruebas de la sección 10 ----------

def test_env_esta_en_gitignore():
    reglas = reglas_gitignore()
    assert ".env" in reglas or "/.env" in reglas


def test_env_example_no_tiene_valores_en_las_claves():
    claves = {n: v for n, v in variables_del_ejemplo().items() if n.endswith("_API_KEY")}
    assert set(claves) == {"GEMINI_API_KEY", "ELEVENLABS_API_KEY"}
    vacias_o_no = {n: ("vacía" if not v else "TIENE UN VALOR") for n, v in claves.items()}
    assert all(not v for v in claves.values()), vacias_o_no  # nunca se muestra el valor


def test_gitignore_no_ignora_el_ejemplo():
    """.env.example sí debe subirse: documenta qué variables hay que llenar."""
    assert ".env*" not in reglas_gitignore() and ".env.*" not in reglas_gitignore()


# ---------- extra: git ls-files (decisión de Yeimy) ----------

def archivos_en_git() -> list[str]:
    if shutil.which("git") is None:
        pytest.skip("git no está instalado")
    resultado = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True)
    if resultado.returncode != 0:
        pytest.skip("la carpeta no es un repositorio de Git")
    return resultado.stdout.splitlines()


@pytest.mark.parametrize("secreto", ARCHIVOS_SECRETOS)
def test_git_no_tiene_archivos_secretos(secreto):
    assert secreto not in archivos_en_git()


def test_git_si_tiene_el_ejemplo():
    assert ".env.example" in archivos_en_git()


def test_ningun_archivo_subido_se_llama_env():
    """Ni en subcarpetas (por ejemplo, una copia de .env dentro de docs/)."""
    sospechosos = [a for a in archivos_en_git() if re.search(r"(^|/)\.env$", a)]
    assert sospechosos == []
