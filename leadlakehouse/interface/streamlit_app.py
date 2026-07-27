"""UI do lead-lakehouse (Streamlit).

Roda a prospecção chamando o CLI via subprocess (evita conflito de event-loop async/
Playwright dentro do Streamlit — mesmo padrão robusto da versão antiga) e lê os leads
direto do Postgres.
"""

from __future__ import annotations

# UI: strings de CSS/HTML inevitavelmente longas.
# ruff: noqa: E501
import json
import subprocess
import sys
import tempfile
from datetime import datetime

import streamlit as st

# Imports absolutos: o Streamlit roda este arquivo como script (sem pacote pai),
# então imports relativos (from ..) quebrariam.
from leadlakehouse.domain.models import Fonte
from leadlakehouse.infra.db import queries

st.set_page_config(page_title="lead-lakehouse", page_icon="⚡", layout="wide")

st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: #080c14; }
    [data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #1e2530; }
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; color: #fff !important; }
    [data-testid="stMetricValue"] { color:#fff !important; font-family:'Syne',sans-serif !important; }
    .stButton > button { background:#3b82f6 !important; color:#fff !important; border:none !important;
        border-radius:8px !important; font-family:'Syne',sans-serif !important; font-weight:600 !important; }
    .section { font-family:'Syne',sans-serif; font-size:0.7rem; font-weight:700; letter-spacing:0.12em;
        text-transform:uppercase; color:#3b82f6; margin:8px 0; }
</style>
""",
    unsafe_allow_html=True,
)


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "leadlakehouse.interface.cli", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


with st.sidebar:
    st.markdown(
        "<div style='font-family:Syne;font-size:1.3rem;font-weight:800;color:#fff'>"
        "lead<span style='color:#3b82f6'>lakehouse</span></div>"
        "<div style='font-size:0.7rem;color:#3a4556;letter-spacing:0.1em;text-transform:uppercase'>"
        "motor de prospecção</div>",
        unsafe_allow_html=True,
    )
    st.divider()
    pagina = st.radio("nav", ["Prospectar", "Leads", "Enviar ao zapagente"],
                      label_visibility="collapsed")
    st.divider()
    try:
        c = queries.contagens()
        st.metric("Negócios", c["negocios"])
        st.metric("Leads", c["leads"])
        st.metric("Enviados", c["enviados"])
    except Exception as e:  # noqa: BLE001
        st.caption(f"Banco indisponível: {e}")


# ────────────────────────── PROSPECTAR ──────────────────────────
if pagina == "Prospectar":
    st.title("⚡ Prospectar")
    st.caption("Defina o ICP (critérios) e rode a coleta multi-fonte.")

    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome do ICP", "Alvos sem site")
        nichos_txt = st.text_input("Nichos (separados por vírgula)", "restaurante, lanchonete")
        municipio = st.text_input("Município", "João Pessoa")
        uf = st.text_input("UF", "PB", max_chars=2)
    with col2:
        fontes = st.multiselect(
            "Fontes", [f.value for f in Fonte if f in (Fonte.OPENSTREETMAP, Fonte.GOOGLE_MAPS)],
            default=[Fonte.OPENSTREETMAP.value],
        )
        limite = st.slider("Limite de resultados", 10, 200, 30, 10)
        st.markdown("<div class='section'>Filtros de oportunidade</div>", unsafe_allow_html=True)
        tem_site_opt = st.selectbox("Presença de site", ["Tanto faz", "Só quem NÃO tem site",
                                                          "Só quem TEM site"])
        enriquecer = st.checkbox("Enriquecer (visita-site, CNPJ)", value=False)

    if st.button("Rodar prospecção", type="primary", use_container_width=True):
        filtros: dict = {}
        if tem_site_opt == "Só quem NÃO tem site":
            filtros["tem_site"] = False
        elif tem_site_opt == "Só quem TEM site":
            filtros["tem_site"] = True

        icp = {
            "nome": nome,
            "nicho": [n.strip() for n in nichos_txt.split(",") if n.strip()],
            "regiao": {"municipio": municipio, "uf": uf},
            "fontes": fontes,
            "filtros": filtros,
            "limite": limite,
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(icp, tf, ensure_ascii=False)
            caminho = tf.name

        args = ["prospectar", "--icp", caminho, "--top", "20"]
        args += ["--enriquecer"] if enriquecer else ["--no-enriquecer"]
        with st.spinner("Coletando, deduplicando e pontuando..."):
            r = _cli(*args)
        st.markdown("<div class='section'>Log</div>", unsafe_allow_html=True)
        st.code((r.stdout or "") + ("\n" + r.stderr if r.returncode != 0 else ""), language="bash")
        if r.returncode == 0:
            st.success("Prospecção concluída! Veja em Leads.")
        else:
            st.error("Falha na prospecção (veja o log).")


# ────────────────────────── LEADS ──────────────────────────
elif pagina == "Leads":
    st.title("≡ Leads")
    try:
        df = queries.leads_df()
    except Exception as e:  # noqa: BLE001
        st.error(f"Banco indisponível: {e}")
        df = None

    if df is None or df.empty:
        st.info("Nenhum lead ainda. Vá em Prospectar.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            niv = st.selectbox("Nível", ["Todos"] + sorted(df["nivel"].dropna().unique().tolist()))
        with c2:
            cid = st.selectbox("Cidade", ["Todas"] + sorted(df["municipio"].dropna().unique().tolist()))
        with c3:
            só_sem_site = st.checkbox("Só sem site", value=False)

        f = df.copy()
        if niv != "Todos":
            f = f[f["nivel"] == niv]
        if cid != "Todas":
            f = f[f["municipio"] == cid]
        if só_sem_site:
            f = f[~f["tem_site"]]

        st.caption(f"{len(f)} leads")
        st.dataframe(
            f[["nome", "nivel", "score", "telefone_e164", "tem_site", "municipio", "categoria",
               "status"]],
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            "Exportar CSV", f.to_csv(index=False).encode("utf-8"),
            f"leads_{datetime.now():%Y%m%d_%H%M%S}.csv", "text/csv",
        )


# ────────────────────────── ENVIAR AO ZAPAGENTE ──────────────────────────
elif pagina == "Enviar ao zapagente":
    st.title("✉ Enviar ao zapagente")
    st.caption("Manda os leads como contatos + tags para o zapagente conversar e fechar.")
    try:
        df = queries.leads_df()
    except Exception as e:  # noqa: BLE001
        st.error(f"Banco indisponível: {e}")
        df = None

    if df is None or df.empty:
        st.info("Nenhum lead para enviar.")
    else:
        pendentes = df[df["status"] != "enviado_zapagente"]
        com_tel = pendentes[pendentes["telefone_e164"].notna()]
        st.metric("Leads com telefone, ainda não enviados", len(com_tel))
        st.dataframe(
            com_tel[["nome", "nivel", "telefone_e164", "municipio"]].head(50),
            use_container_width=True, hide_index=True,
        )
        st.info(
            "O conector (`llh enviar-zapagente`) usa a API do zapagente "
            "(contatos + tags + campanha). Configure `LLH_ZAPAGENTE_BASE_URL` e "
            "`LLH_ZAPAGENTE_TOKEN` no `.env` para habilitar o envio."
        )
        disabled = not com_tel.empty and False
        if st.button("Enviar ao zapagente", type="primary", disabled=len(com_tel) == 0 or disabled):
            with st.spinner("Enviando..."):
                r = _cli("enviar-zapagente", "--icp-nome", "")
            st.code((r.stdout or "") + ("\n" + r.stderr if r.returncode != 0 else ""))
