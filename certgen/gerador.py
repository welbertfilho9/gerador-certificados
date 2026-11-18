"""Geração do certificado em PDF (A4 paisagem) com reportlab."""
import hashlib
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from . import config as C


def renderizar(template, valores):
    """Troca {chave} pelos valores. Chaves desconhecidas permanecem como estão."""
    return re.sub(r"\{(\w+)\}", lambda m: str(valores.get(m.group(1), m.group(0))), template)


def valores_do_certificado(linha, cfg):
    ev, ident = cfg["evento"], cfg["identificacao"]
    col = ident.get("coluna", "")
    valor = str(linha.get(col, "")).strip() if col else ""
    identificacao = (
        renderizar(ident["formato"], {"rotulo": ident["rotulo"], "valor": valor}) if valor else ""
    )
    assinantes = [a for a in cfg["assinaturas"] if a.get("nome")]
    nome = linha["nome"]
    return {
        **ev,
        "evento": ev["nome"],
        "nome": nome,
        "primeiro_nome": nome.split()[0] if nome else "",
        "identificacao": identificacao,
        "assinante": assinantes[0]["nome"] if assinantes else "",
        "data_emissao": datetime.now().strftime("%d/%m/%Y"),
    }


def codigo_verificacao(nome, identificacao, cfg):
    base = f"{nome}|{identificacao}|{cfg['evento']['nome']}|{cfg['evento']['data']}"
    return hashlib.sha256(base.encode()).hexdigest()[:12].upper()


def _img(c, arquivo, x, y, w, h, anchor="c"):
    p = C.resolver(arquivo)
    if not p:
        return False
    try:
        c.drawImage(str(p), x, y, w, h, preserveAspectRatio=True, mask="auto", anchor=anchor)
        return True
    except Exception:
        return False


def gerar_pdf(linha, cfg, caminho_pdf):
    v, t, vis = valores_do_certificado(linha, cfg), cfg["textos"], cfg["visual"]
    primaria, destaque, texto_cor = (HexColor(vis[k]) for k in ("cor_primaria", "cor_destaque", "cor_texto"))
    W, H = landscape(A4)
    nome = linha["nome"]

    c = canvas.Canvas(str(caminho_pdf), pagesize=(W, H))
    c.setTitle(f"Certificado – {nome}")

    # fundo, faixas e moldura
    c.setFillColor(white); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(primaria); c.rect(0, H - 14, W, 14, fill=1, stroke=0)
    c.setFillColor(destaque); c.rect(0, H - 19, W, 5, fill=1, stroke=0)
    c.setFillColor(primaria); c.rect(0, 0, W, 28, fill=1, stroke=0)
    c.setFillColor(destaque); c.rect(0, 28, W, 4, fill=1, stroke=0)
    c.setStrokeColor(primaria); c.setLineWidth(1.2)
    c.rect(22, 44, W - 44, H - 174, fill=0, stroke=1)

    # logos (PNG transparente direto sobre o fundo branco)
    S = float(vis.get("tamanho_logo", 80))
    esq = [l for l in vis["logos"] if l.get("lado") != "direita"]
    dire = [l for l in vis["logos"] if l.get("lado") == "direita"]
    x = 34
    for l in esq:
        _img(c, l["arquivo"], x, H - 25 - S, S, S); x += S + 8
    x = W - 34 - S
    for l in dire:
        _img(c, l["arquivo"], x, H - 25 - S, S, S); x -= S + 8

    # título
    c.setFillColor(texto_cor); c.setFont("Helvetica-Bold", 42)
    c.drawCentredString(W / 2, H - 72, t["titulo"])
    c.setFillColor(primaria); c.setFont("Helvetica", 12)
    c.drawCentredString(W / 2, H - 94, cfg["evento"]["organizacao"].upper())

    # abertura + nome
    c.setFillColor(texto_cor); c.setFont("Helvetica", 19)
    c.drawCentredString(W / 2, H - 178, t["abertura"])
    tam = 36
    while c.stringWidth(nome, "Helvetica-Bold", tam) > W - 130 and tam > 16:
        tam -= 1
    c.setFont("Helvetica-Bold", tam); c.setFillColor(primaria)
    c.drawCentredString(W / 2, H - 226, nome)
    c.setStrokeColor(destaque); c.setLineWidth(2.5)
    c.line(W / 2 - 230, H - 238, W / 2 + 230, H - 238)

    # corpo (reduz a fonte automaticamente se o texto for longo)
    corpo = renderizar(t["corpo"], v)
    c.setFillColor(texto_cor)
    fonte = float(t.get("tamanho_corpo", 17))
    topo, limite = H - 280, 160
    while True:
        esp = fonte * 1.65
        linhas = simpleSplit(corpo, "Helvetica", fonte, W - 140)
        if topo - len(linhas) * esp >= limite or fonte <= 9:
            break
        fonte -= 0.5
    c.setFont("Helvetica", fonte)
    y = topo
    for l in linhas:
        c.drawCentredString(W / 2, y, l); y -= esp

    # assinaturas (1 a 3)
    assin = [a for a in cfg["assinaturas"] if a.get("nome")][:3]
    n = len(assin)
    larg = 300 if n == 1 else 230
    ay = 100
    for i, a in enumerate(assin):
        ax = W * (i + 1) / (n + 1)
        _img(c, a.get("imagem"), ax - larg / 2, ay + 1, larg, 46, anchor="s")
        c.setStrokeColor(texto_cor); c.setLineWidth(0.8)
        c.line(ax - larg / 2, ay + 2, ax + larg / 2, ay + 2)
        c.setFillColor(texto_cor); c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(ax, ay - 15, a["nome"])
        if a.get("cargo"):
            c.setFont("Helvetica", 11.5); c.drawCentredString(ax, ay - 30, a["cargo"])

    # rodapé
    c.setFillColor(white); c.setFont("Helvetica", 8)
    if t.get("mostrar_codigo", True):
        c.drawString(30, 10, f"Código de verificação: {codigo_verificacao(nome, v['identificacao'], cfg)}")
    if t.get("rodape"):
        c.drawCentredString(W / 2, 10, renderizar(t["rodape"], v))
    c.drawRightString(W - 30, 10, f"Emitido em {v['data_emissao']}")
    c.showPage(); c.save()
    return caminho_pdf


def _slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()


def gerar_todos(df, cfg, pasta=None, progresso=None):
    pasta = Path(pasta or C.PASTA_SAIDA / "certificados")
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for i, linha in enumerate(df.to_dict("records")):
        col = cfg["identificacao"].get("coluna", "")
        sufixo = _slug(linha.get(col, "")) if col else ""
        p = pasta / f"certificado_{i + 1:03d}_{_slug(linha['nome'])}{'_' + sufixo if sufixo else ''}.pdf"
        gerar_pdf(linha, cfg, p)
        caminhos.append(p)
        if progresso:
            progresso(i + 1, len(df), linha["nome"])
    return caminhos


def pdf_para_png(caminho_pdf, zoom=1.4):
    """Prévia em PNG (bytes). Requer pymupdf; retorna None se não estiver instalado."""
    try:
        import fitz
    except ImportError:
        return None
    with fitz.open(str(caminho_pdf)) as doc:
        return doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
