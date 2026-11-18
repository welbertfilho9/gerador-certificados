"""Configurações: valores padrão (genéricos) + sobrescritas locais em config.json."""
import json
import os
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_LOCAL = ROOT / "config.json"
PASTA_SAIDA = ROOT / "saida"
PASTA_UPLOADS = ROOT / "assets" / "meus"

PADRAO = {
    "evento": {
        "nome": "Nome do Evento",
        "organizacao": "Nome da Organização",
        "data": "DD/MM/AAAA",
        "horario": "das 14h às 16h",
        "local": "Local do evento",
        "carga_horaria": "2 horas",
    },
    "textos": {
        "titulo": "CERTIFICADO",
        "abertura": "Certificamos que",
        "corpo": (
            "{identificacao}participou do evento “{evento}”, realizado em {data}, "
            "{horario}, em {local}, com carga horária total de {carga_horaria}."
        ),
        "tamanho_corpo": 17,
        "rodape": "",
        "mostrar_codigo": True,
        "normalizar_nomes": True,
    },
    "identificacao": {
        "coluna": "",
        "rotulo": "RA",
        "formato": "portador(a) do {rotulo} {valor}, ",
    },
    "visual": {
        "cor_primaria": "#1B3F8B",
        "cor_destaque": "#FFC800",
        "cor_texto": "#0B2A5E",
        "tamanho_logo": 80,
        "logos": [
            {"arquivo": "assets/exemplo/logo_exemplo_1.png", "lado": "esquerda"},
            {"arquivo": "assets/exemplo/logo_exemplo_2.png", "lado": "direita"},
        ],
    },
    "assinaturas": [
        {"nome": "Nome do Assinante", "cargo": "Cargo / Função",
         "imagem": "assets/exemplo/assinatura_exemplo.png"},
    ],
    "planilha": {"coluna_nome": "", "coluna_email": ""},
    "email": {
        "servidor": "smtp.gmail.com",
        "porta": 465,
        "nome_remetente": "Organização do Evento",
        "pausa_segundos": 2,
        "assunto": "Seu certificado – {evento}",
        "corpo": (
            "Olá, {primeiro_nome}!\n\n"
            "Obrigado por participar de {evento}, em {data}.\n\n"
            "Em anexo está o seu certificado de {carga_horaria}.\n\n"
            "Atenciosamente,\n{assinante}\n{organizacao}\n"
        ),
    },
}


def _mesclar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def carregar(caminho=None):
    """Padrões + config.json (se existir)."""
    cfg = deepcopy(PADRAO)
    caminho = Path(caminho) if caminho else CONFIG_LOCAL
    if caminho.exists():
        _mesclar(cfg, json.loads(caminho.read_text(encoding="utf-8")))
    return cfg


def salvar(cfg, caminho=None):
    caminho = Path(caminho) if caminho else CONFIG_LOCAL
    caminho.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def resolver(caminho):
    """Caminho relativo à raiz do projeto -> Path existente, ou None."""
    if not caminho:
        return None
    p = Path(caminho)
    if not p.is_absolute():
        p = ROOT / p
    return p if p.exists() else None


def carregar_env():
    """Lê o arquivo .env (se existir) sem depender de bibliotecas externas."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
