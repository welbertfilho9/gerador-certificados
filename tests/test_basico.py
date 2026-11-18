import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from certgen import config as C, emailer, gerador, planilha

EXEMPLO = Path(__file__).resolve().parent.parent / "exemplos" / "planilha_exemplo.csv"


def _cfg():
    cfg = C.carregar(Path("__nao_existe__"))
    return cfg


def test_leitura_e_normalizacao():
    df = planilha.ler(EXEMPLO)
    assert list(df["nome"])[1] == "João Pedro Álvares de Albuquerque Montenegro Neto"
    assert df["email_valido"].all()


def test_colunas_estilo_google_forms(tmp_path):
    f = tmp_path / "f.csv"
    f.write_text("Carimbo de data/hora,Endereço de e-mail,Nome,RA (discentes),Email institucional\n"
                 "x,a@b.com,ana lima,123,a@inst.edu\n", encoding="utf-8")
    df = planilha.ler(f)
    assert df.loc[0, "email"] == "a@b.com"
    df = planilha.ler(f, {"coluna_email": "institucional"})
    assert df.loc[0, "email"] == "a@inst.edu"
    assert planilha.adivinhar_identificacao(df.columns) == "RA (discentes)"


def test_identificacao_opcional(tmp_path):
    cfg = _cfg(); cfg["identificacao"]["coluna"] = "RA"
    v = gerador.valores_do_certificado({"nome": "Ana", "RA": ""}, cfg)
    assert v["identificacao"] == ""
    v = gerador.valores_do_certificado({"nome": "Ana", "RA": "99"}, cfg)
    assert "RA 99" in v["identificacao"]


def test_gera_pdf(tmp_path):
    df = planilha.ler(EXEMPLO)
    pdfs = gerador.gerar_todos(df, _cfg(), pasta=tmp_path)
    assert len(pdfs) == 3 and all(p.read_bytes().startswith(b"%PDF") for p in pdfs)


def test_envio_monta_mensagem(tmp_path, monkeypatch):
    monkeypatch.setenv("EMAIL_REMETENTE", "eu@exemplo.com")
    monkeypatch.setenv("EMAIL_SENHA", "senha")
    monkeypatch.setattr(emailer, "LOG", tmp_path / "log.csv")
    cfg = _cfg()
    df = planilha.ler(EXEMPLO)
    pdfs = gerador.gerar_todos(df, cfg, pasta=tmp_path)
    smtp = MagicMock()
    with patch("smtplib.SMTP_SSL", return_value=smtp), patch("time.sleep"):
        res = emailer.enviar_todos(df, pdfs, cfg)
    assert [r["status"] for r in res] == ["ok"] * 3
    assert smtp.send_message.call_count == 3
    msg = smtp.send_message.call_args_list[0].args[0]
    assert msg["To"] == "maria@exemplo.com" and "Nome do Evento" in msg["Subject"]
    with patch("smtplib.SMTP_SSL", return_value=smtp), patch("time.sleep"):
        res2 = emailer.enviar_todos(df, pdfs, cfg)  # segunda rodada: ninguém reenviado
    assert [r["status"] for r in res2] == ["ja_enviado"] * 3
