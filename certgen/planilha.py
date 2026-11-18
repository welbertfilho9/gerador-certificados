"""Leitura da planilha (.xlsx ou .csv) com detecção flexível de colunas."""
import io
import re
import unicodedata
from pathlib import Path

import pandas as pd

ALIASES = {
    "nome": {"nome", "nome completo", "aluno", "participante", "name"},
    "email": {"email", "e-mail", "e mail", "endereco de email", "endereco de e-mail", "mail"},
}
REGRAS = {
    "nome": lambda n: re.match(r"^(nome|aluno|participante)\b", n),
    "email": lambda n: "mail" in n and "institucional" not in n,
}
PARTICULAS = {"da", "de", "do", "das", "dos", "e"}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def capitalizar_nome(nome):
    return " ".join(
        w.lower() if i and w.lower() in PARTICULAS else w.capitalize()
        for i, w in enumerate(str(nome).split())
    )


def _ler_bruto(origem):
    nome = getattr(origem, "name", str(origem)).lower()
    dados = origem.read() if hasattr(origem, "read") else Path(origem).read_bytes()
    if nome.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(io.BytesIO(dados), dtype=str)
    if nome.endswith(".csv"):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                texto = dados.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        return pd.read_csv(io.StringIO(texto), dtype=str, sep=None, engine="python")
    raise ValueError("Formato não suportado. Use .xlsx ou .csv.")


def mapear_colunas(colunas, cfg_planilha=None):
    """Descobre quais colunas são 'nome' e 'email'. Retorna {destino: coluna_original}."""
    cfg_planilha = cfg_planilha or {}
    mapa = {}
    usadas = lambda: set(mapa.values())
    # 1) escolha manual (parte do nome da coluna)
    for destino in ("nome", "email"):
        forcada = _norm(cfg_planilha.get(f"coluna_{destino}", ""))
        if forcada:
            for c in colunas:
                if forcada in _norm(c) and c not in usadas():
                    mapa[destino] = c
                    break
    # 2) nome exato conhecido
    for destino in ("nome", "email"):
        if destino not in mapa:
            for c in colunas:
                if c not in usadas() and _norm(c) in ALIASES[destino]:
                    mapa[destino] = c
                    break
    # 3) aproximado
    for destino, regra in REGRAS.items():
        if destino not in mapa:
            for c in colunas:
                if c not in usadas() and regra(_norm(c)):
                    mapa[destino] = c
                    break
    # 4) último recurso: qualquer coluna com "mail" (ex.: só existe o institucional)
    if "email" not in mapa:
        for c in colunas:
            if c not in usadas() and "mail" in _norm(c):
                mapa["email"] = c
                break
    return mapa


def adivinhar_identificacao(colunas):
    """Sugere uma coluna de identificação (RA, matrícula, RG...), ou '' se não achar."""
    for c in colunas:
        if re.match(r"^(ra|rg|matricula|registro|documento|id)\b", _norm(c)):
            return c
    return ""


def ler(origem, cfg_planilha=None, normalizar_nomes=True):
    """Retorna DataFrame com 'nome', 'email', 'email_valido' + as demais colunas originais."""
    df = _ler_bruto(origem).fillna("")
    mapa = mapear_colunas(list(df.columns), cfg_planilha)
    faltando = {"nome", "email"} - set(mapa)
    if faltando:
        raise ValueError(
            f"Não encontrei a(s) coluna(s): {', '.join(sorted(faltando))}. "
            f"Colunas da planilha: {list(df.columns)}. "
            "Renomeie para 'Nome' e 'Email' ou ajuste 'planilha' no config.json."
        )
    for destino, col in mapa.items():  # evita colisão com colunas já chamadas 'nome'/'email'
        if destino in df.columns and col != destino:
            df = df.rename(columns={destino: destino + "_orig"})
            mapa = {k: (destino + "_orig" if v == destino else v) for k, v in mapa.items()}
    df = df.rename(columns={v: k for k, v in mapa.items()})
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    if normalizar_nomes:
        df["nome"] = df["nome"].apply(capitalizar_nome)
    df = df[(df["nome"] != "") | (df["email"] != "")]
    df = df.assign(_k=df["email"].str.lower() + "|" + df["nome"].str.lower())
    df = df.drop_duplicates("_k").drop(columns="_k").reset_index(drop=True)
    df["email_valido"] = df["email"].str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    return df
