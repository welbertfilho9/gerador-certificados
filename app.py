"""Interface web. Rode com:  python -m streamlit run app.py"""
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from certgen import config as C, emailer, gerador, imagens, planilha

st.set_page_config(page_title="Gerador de Certificados", page_icon="🎓", layout="wide")
st.title("🎓 Gerador de Certificados")

if "cfg" not in st.session_state:
    st.session_state.cfg = C.carregar()
    st.session_state.processados = set()
cfg = st.session_state.cfg
ev, tx, ident, vis, em = cfg["evento"], cfg["textos"], cfg["identificacao"], cfg["visual"], cfg["email"]

previa = st.sidebar.container()  # preenchida no fim do script, com as configurações já atualizadas
st.sidebar.divider()
if st.sidebar.button("💾 Salvar configurações", use_container_width=True):
    C.salvar(cfg)
    st.sidebar.success("Salvo em config.json")
if st.sidebar.button("↩️ Restaurar padrão", use_container_width=True):
    st.session_state.cfg = C.carregar(Path("__nao_existe__"))
    st.rerun()

aba1, aba2, aba3 = st.tabs(["1. Evento e textos", "2. Visual", "3. Planilha e envio"])

# ------------------------------------------------------------------ aba 1
with aba1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Evento")
        ev["nome"] = st.text_input("Nome do evento", ev["nome"])
        ev["organizacao"] = st.text_input("Organização (aparece sob o título)", ev["organizacao"])
        ev["data"] = st.text_input("Data", ev["data"])
        ev["horario"] = st.text_input("Horário", ev["horario"])
        ev["local"] = st.text_input("Local", ev["local"])
        ev["carga_horaria"] = st.text_input("Carga horária", ev["carga_horaria"])
    with c2:
        st.subheader("Textos do certificado")
        tx["titulo"] = st.text_input("Título", tx["titulo"])
        tx["abertura"] = st.text_input("Frase antes do nome", tx["abertura"])
        tx["corpo"] = st.text_area("Texto principal", tx["corpo"], height=140)
        st.caption("Variáveis: `{nome}` `{evento}` `{data}` `{horario}` `{local}` `{carga_horaria}` "
                   "`{organizacao}` `{identificacao}` (RA/matrícula, só aparece se preenchido)")
        tx["tamanho_corpo"] = st.slider("Tamanho da fonte do texto", 10, 24, int(tx["tamanho_corpo"]))
        tx["rodape"] = st.text_input("Texto extra no rodapé (opcional)", tx["rodape"])
        tx["mostrar_codigo"] = st.checkbox("Mostrar código de verificação no rodapé", tx["mostrar_codigo"])
        tx["normalizar_nomes"] = st.checkbox("Padronizar maiúsculas/minúsculas dos nomes", tx["normalizar_nomes"])
    st.subheader("E-mail enviado com o certificado")
    em["assunto"] = st.text_input("Assunto", em["assunto"])
    em["corpo"] = st.text_area("Mensagem", em["corpo"], height=170)
    st.caption("Variáveis: `{primeiro_nome}` `{nome}` `{evento}` `{data}` `{carga_horaria}` `{assinante}` `{organizacao}`")
    c3, c4, c5 = st.columns(3)
    em["nome_remetente"] = c3.text_input("Nome do remetente", em["nome_remetente"])
    em["servidor"] = c4.text_input("Servidor SMTP", em["servidor"])
    em["porta"] = int(c5.number_input("Porta (465 = SSL, 587 = STARTTLS)", value=int(em["porta"]), step=1))

# ------------------------------------------------------------------ aba 2
with aba2:
    st.subheader("Cores")
    k1, k2, k3 = st.columns(3)
    vis["cor_primaria"] = k1.color_picker("Cor principal (faixas e nome)", vis["cor_primaria"])
    vis["cor_destaque"] = k2.color_picker("Cor de destaque (detalhes)", vis["cor_destaque"])
    vis["cor_texto"] = k3.color_picker("Cor do texto", vis["cor_texto"])

    st.subheader("Logos")
    vis["tamanho_logo"] = st.slider("Tamanho dos logos", 50, 100, int(vis["tamanho_logo"]))
    novos = st.file_uploader("Adicionar logos (PNG, de preferência com fundo transparente)",
                             type=["png"], accept_multiple_files=True, key="up_logos")
    for f in novos or []:
        chave = ("logo", f.name, f.size)
        if chave not in st.session_state.processados:
            dest = C.PASTA_UPLOADS / f"logo_{Path(f.name).stem}.png"
            imagens.salvar_logo(f, dest)
            vis["logos"].append({"arquivo": str(dest.relative_to(C.ROOT)), "lado": "esquerda"})
            st.session_state.processados.add(chave)
    for i, logo in enumerate(list(vis["logos"])):
        col_a, col_b, col_c = st.columns([1, 3, 1])
        p = C.resolver(logo["arquivo"])
        if p:
            col_a.image(str(p), width=60)
        lado = col_b.radio(Path(logo["arquivo"]).name, ["esquerda", "direita"], horizontal=True,
                           index=0 if logo.get("lado") != "direita" else 1, key=f"lado_{i}")
        logo["lado"] = lado
        if col_c.button("Remover", key=f"rm_{i}"):
            vis["logos"].pop(i)
            st.rerun()
    st.caption("A ordem de cada lado segue a ordem da lista (a partir da borda do certificado).")

    st.subheader("Assinaturas")
    n = st.number_input("Quantidade de assinaturas", 1, 3, max(1, len(cfg["assinaturas"])))
    while len(cfg["assinaturas"]) < n:
        cfg["assinaturas"].append({"nome": "", "cargo": "", "imagem": ""})
    del cfg["assinaturas"][n:]
    for i, a in enumerate(cfg["assinaturas"]):
        s1, s2, s3 = st.columns([2, 2, 2])
        a["nome"] = s1.text_input(f"Nome do assinante {i + 1}", a["nome"], key=f"an_{i}")
        a["cargo"] = s2.text_input("Cargo / função", a.get("cargo", ""), key=f"ac_{i}")
        up = s3.file_uploader("Imagem da assinatura (fundo claro serve)", type=["png", "jpg", "jpeg"], key=f"ai_{i}")
        if up is not None and ("ass", i, up.name, up.size) not in st.session_state.processados:
            dest = C.PASTA_UPLOADS / f"assinatura_{i + 1}.png"
            imagens.assinatura_transparente(up, dest)
            a["imagem"] = str(dest.relative_to(C.ROOT))
            st.session_state.processados.add(("ass", i, up.name, up.size))

# ------------------------------------------------------------------ aba 3
with aba3:
    arq = st.file_uploader("Planilha (.xlsx ou .csv) com colunas de nome e e-mail", type=["xlsx", "csv"])
    df = None
    if arq:
        try:
            df = planilha.ler(arq, cfg["planilha"], tx["normalizar_nomes"])
        except Exception as e:
            st.error(str(e))
    if df is not None:
        extras = [c for c in df.columns if c not in ("nome", "email", "email_valido")]
        st.write(f"**{len(df)} participantes** encontrados.")
        if (~df["email_valido"]).any():
            st.warning(f"{(~df['email_valido']).sum()} com e-mail inválido (não receberão).")
        st.dataframe(df, use_container_width=True)

        st.markdown("**Campo de identificação (opcional)** — por exemplo RA, matrícula ou RG.")
        opcoes = ["(nenhum)"] + extras
        atual = ident["coluna"] if ident["coluna"] in extras else planilha.adivinhar_identificacao(extras)
        escolha = st.selectbox("Coluna que identifica o participante", opcoes,
                               index=opcoes.index(atual) if atual in opcoes else 0)
        ident["coluna"] = "" if escolha == "(nenhum)" else escolha
        ident["rotulo"] = st.text_input("Rótulo exibido no certificado (ex.: RA, matrícula, RG)", ident["rotulo"])
        st.caption("Linhas com esse campo vazio saem sem a identificação; as demais mostram "
                   "“portador(a) do RA 123…”. Para não usar, deixe “(nenhum)”.")

        st.divider()
        ok_cred = emailer.credenciais_ok()
        st.info("✅ Credenciais de e-mail encontradas (.env)." if ok_cred else
                "⚠️ Credenciais de e-mail não configuradas — veja o README (arquivo .env). "
                "Você ainda pode gerar os PDFs.")
        b1, b2, b3 = st.columns(3)
        if b1.button("1) Gerar PDFs"):
            barra = st.progress(0)
            pdfs = gerador.gerar_todos(df, cfg, progresso=lambda i, n, nm: barra.progress(i / n, text=nm))
            st.success(f"{len(pdfs)} certificados em: {C.PASTA_SAIDA / 'certificados'}")
        if b2.button("2) Enviar teste para mim", disabled=not ok_cred):
            try:
                tmp = Path(tempfile.mkdtemp()) / "teste.pdf"
                gerador.gerar_pdf(df.to_dict("records")[0], cfg, tmp)
                st.success(f"Teste enviado para {emailer.enviar_teste(cfg, df.to_dict('records')[0], tmp)}")
            except Exception as e:
                st.error(f"Falha no envio: {e}")
        confirma = b3.checkbox("Confirmo o envio real para todos", disabled=not ok_cred)
        if b3.button("3) Gerar e ENVIAR", disabled=not (ok_cred and confirma)):
            barra = st.progress(0)
            try:
                pdfs = gerador.gerar_todos(df, cfg)
                res = emailer.enviar_todos(df, pdfs, cfg, progresso=lambda i, n, m: barra.progress(i / n, text=m))
                st.success("Envio concluído.")
                st.dataframe(pd.DataFrame(res), use_container_width=True)
            except Exception as e:
                st.error(f"Falha no envio: {e}")
    else:
        st.caption("Envie a planilha para continuar. Exemplo: `exemplos/planilha_exemplo.csv`.")

# ------------------------------------------------------------------ prévia (sidebar)
with previa:
    st.subheader("Prévia")
    amostra = {"nome": "Maria da Silva Exemplo", "email": "maria@exemplo.com", "email_valido": True}
    if ident["coluna"]:
        amostra[ident["coluna"]] = "11202012345"
    tmp = Path(tempfile.mkdtemp()) / "previa.pdf"
    gerador.gerar_pdf(amostra, cfg, tmp)
    png = gerador.pdf_para_png(tmp)
    if png:
        st.image(png, use_container_width=True)
    st.download_button("Baixar prévia (PDF)", tmp.read_bytes(), "previa.pdf", use_container_width=True)
