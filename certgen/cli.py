"""Uso: python -m certgen planilha.xlsx [--enviar]"""
import argparse

from . import config as C, emailer, gerador, planilha


def main():
    ap = argparse.ArgumentParser(prog="certgen", description="Gera e envia certificados a partir de uma planilha.")
    ap.add_argument("planilha", help="arquivo .xlsx ou .csv (colunas: nome e email)")
    ap.add_argument("--config", help="caminho de um config.json alternativo")
    ap.add_argument("--coluna-id", help="coluna de identificação (ex.: RA); sobrescreve o config")
    ap.add_argument("--enviar", action="store_true", help="envia por e-mail (sem isso só gera os PDFs)")
    a = ap.parse_args()

    cfg = C.carregar(a.config)
    df = planilha.ler(a.planilha, cfg["planilha"], cfg["textos"]["normalizar_nomes"])
    if a.coluna_id is not None:
        cfg["identificacao"]["coluna"] = a.coluna_id
    elif not cfg["identificacao"]["coluna"]:
        cfg["identificacao"]["coluna"] = ""  # sem identificação por padrão
    print(f"{len(df)} participantes lidos ({(~df['email_valido']).sum()} com e-mail inválido).")
    pdfs = gerador.gerar_todos(df, cfg, progresso=lambda i, n, nm: print(f"[{i}/{n}] PDF: {nm}"))
    print(f"PDFs em {C.PASTA_SAIDA / 'certificados'}")
    if a.enviar:
        for r in emailer.enviar_todos(df, pdfs, cfg, progresso=lambda i, n, m: print(f"[{i}/{n}] {m}")):
            pass
        print(f"Pronto! Registro em {emailer.LOG}")


if __name__ == "__main__":
    main()
