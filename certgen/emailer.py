"""Envio de e-mails via SMTP (Gmail, Outlook, etc.) com registro de envios."""
import csv
import os
import smtplib
import ssl
import time
from contextlib import contextmanager
from datetime import datetime
from email.message import EmailMessage

from . import config as C
from .gerador import renderizar, valores_do_certificado

LOG = C.PASTA_SAIDA / "log_envios.csv"


def credenciais():
    C.carregar_env()
    return os.getenv("EMAIL_REMETENTE", "").strip(), os.getenv("EMAIL_SENHA", "").strip()


def credenciais_ok():
    r, s = credenciais()
    return bool(r and s)


@contextmanager
def _conectar(cfg, remetente, senha):
    e = cfg["email"]
    ctx = ssl.create_default_context()
    if int(e["porta"]) == 465:
        srv = smtplib.SMTP_SSL(e["servidor"], 465, context=ctx, timeout=30)
    else:
        srv = smtplib.SMTP(e["servidor"], int(e["porta"]), timeout=30)
        srv.starttls(context=ctx)
    try:
        srv.login(remetente, senha)
        yield srv
    finally:
        try:
            srv.quit()
        except Exception:
            pass


def montar_mensagem(cfg, linha, pdf, remetente, destino=None):
    v = valores_do_certificado(linha, cfg)
    m = EmailMessage()
    m["From"] = f"{cfg['email']['nome_remetente']} <{remetente}>"
    m["To"] = destino or linha["email"]
    m["Subject"] = renderizar(cfg["email"]["assunto"], v)
    m.set_content(renderizar(cfg["email"]["corpo"], v))
    m.add_attachment(open(pdf, "rb").read(), maintype="application", subtype="pdf", filename=pdf.name)
    return m


def _log(email, nome, status, detalhe=""):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    novo = not LOG.exists()
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data", "email", "nome", "status", "detalhe"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), email, nome, status, detalhe])


def _ja_enviados():
    if not LOG.exists():
        return set()
    with open(LOG, encoding="utf-8") as f:
        return {r["email"].lower() for r in csv.DictReader(f) if r["status"] == "ok"}


def enviar_teste(cfg, linha, pdf):
    """Manda um certificado de teste para o PRÓPRIO remetente."""
    rem, senha = credenciais()
    if not (rem and senha):
        raise RuntimeError("Credenciais não configuradas. Veja o README (arquivo .env).")
    with _conectar(cfg, rem, senha) as s:
        s.send_message(montar_mensagem(cfg, linha, pdf, rem, destino=rem))
    return rem


def enviar_todos(df, pdfs, cfg, progresso=None):
    rem, senha = credenciais()
    if not (rem and senha):
        raise RuntimeError("Credenciais não configuradas. Veja o README (arquivo .env).")
    ja, resultados = _ja_enviados(), []
    with _conectar(cfg, rem, senha) as s:
        for i, (linha, pdf) in enumerate(zip(df.to_dict("records"), pdfs)):
            email, nome = linha["email"], linha["nome"]
            if not linha["email_valido"]:
                status = "email_invalido"; _log(email, nome, status)
            elif email.lower() in ja:
                status = "ja_enviado"
            else:
                try:
                    s.send_message(montar_mensagem(cfg, linha, pdf, rem))
                    status = "ok"; _log(email, nome, status)
                    time.sleep(float(cfg["email"].get("pausa_segundos", 2)))
                except Exception as e:  # registra e segue para o próximo
                    status = "erro"; _log(email, nome, status, str(e))
            resultados.append({"nome": nome, "email": email, "status": status})
            if progresso:
                progresso(i + 1, len(df), f"{nome} → {status}")
    return resultados
