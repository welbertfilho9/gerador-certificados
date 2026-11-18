"""Utilitários de imagem: assinatura com fundo transparente e placeholders de exemplo."""
from pathlib import Path

from PIL import Image


def assinatura_transparente(origem, destino):
    """Converte uma assinatura escaneada/fotografada (fundo claro) em PNG transparente, tinta escura."""
    import numpy as np

    im = Image.open(origem).convert("RGBA")
    a = np.array(im).astype(float)
    luminosidade = a[..., :3].mean(axis=2)
    alpha = np.clip((255 - luminosidade) * 1.4, 0, 255)
    a[..., 3] = np.minimum(a[..., 3], alpha)
    a[..., :3] = 20
    out = Image.fromarray(a.astype("uint8"))
    bbox = out.getchannel("A").getbbox()
    if bbox:
        out = out.crop(bbox)
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    out.save(destino)
    return destino


def salvar_logo(origem, destino, lado_max=800):
    im = Image.open(origem).convert("RGBA")
    im.thumbnail((lado_max, lado_max))
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    return destino
