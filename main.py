import streamlit as st
import subprocess
import sys
import os
import time
import duckdb
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db.database import init_db, get_connection, reset_db, DB_PATH

st.set_page_config(
    page_title="LeadLakehouse",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: #080c14; }
    [data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #1e2530; }
    [data-testid="stSidebar"] * { color: #8892a4 !important; }
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; color: #fff !important; }
    [data-testid="stMetric"] { background: #0d1117; border: 1px solid #1e2530; border-radius: 12px; padding: 20px 24px; }
    [data-testid="stMetricLabel"] { color: #5a6478 !important; font-size: 0.78rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #fff !important; font-family: 'Syne', sans-serif !important; font-size: 2rem !important; }
    .stTextInput input { background: #0d1117 !important; border: 1px solid #1e2530 !important; border-radius: 8px !important; color: #e2e8f0 !important; }
    .stButton > button { background: #3b82f6 !important; color: #fff !important; border: none !important; border-radius: 8px !important; font-family: 'Syne', sans-serif !important; font-weight: 600 !important; }
    .stButton > button:hover { background: #2563eb !important; }
    .stButton > button:disabled { background: #1e2530 !important; color: #3a4556 !important; }
    [data-testid="stDataFrame"] { border: 1px solid #1e2530; border-radius: 10px; overflow: hidden; }
    hr { border-color: #1e2530 !important; }
    .stAlert { border-radius: 10px !important; }
    .stProgress > div > div { background: #3b82f6 !important; }
    .stCaption { color: #5a6478 !important; }
    .section-title { font-family: 'Syne', sans-serif; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #3b82f6; margin-bottom: 12px; }
    .stat-big { font-family: 'Syne', sans-serif; font-size: 3.5rem; font-weight: 800; color: #fff; line-height: 1; }
    .stat-label { font-size: 0.8rem; color: #5a6478; margin-top: 6px; letter-spacing: 0.06em; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

init_db()

if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Coletar"


def load_leads() -> pd.DataFrame:
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        df  = con.execute("SELECT * FROM leads ORDER BY id DESC").df()
        con.close()
        return df
    except Exception:
        return pd.DataFrame()


# ── Sidebar
with st.sidebar:
    st.markdown("""
    <div style='padding:8px 0 20px'>
        <div style='font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:#fff;'>
            Lead<span style='color:#3b82f6'>Lakehouse</span>
        </div>
        <div style='font-size:0.72rem;color:#3a4556;letter-spacing:0.1em;text-transform:uppercase;margin-top:2px;'>
            Pipeline de Leads
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    pagina = st.radio(
        "nav",
        ["Coletar", "Dashboard", "Leads", "Configuracoes"],
        format_func=lambda x: {
            "Coletar":       "⚡  Coletar Leads",
            "Dashboard":     "◈  Dashboard",
            "Leads":         "≡  Leads",
            "Configuracoes": "⚙  Configuracoes",
        }[x],
        label_visibility="collapsed",
        key="nav_radio",
        index=["Coletar", "Dashboard", "Leads", "Configuracoes"].index(
            st.session_state.pagina_atual
        ),
    )
    st.session_state.pagina_atual = pagina
    st.divider()

    df_sb    = load_leads()
    total_sb = len(df_sb)
    alvos_sb = int((df_sb["score_digital"] == 0).sum()) if not df_sb.empty else 0
    st.markdown(f"""
    <div style='font-size:0.7rem;color:#3a4556;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;'>Base atual</div>
    <div style='display:flex;gap:16px;'>
        <div>
            <div style='font-family:Syne,sans-serif;font-size:1.4rem;font-weight:700;color:#fff;'>{total_sb}</div>
            <div style='font-size:0.68rem;color:#3a4556;'>leads</div>
        </div>
        <div>
            <div style='font-family:Syne,sans-serif;font-size:1.4rem;font-weight:700;color:#f87171;'>{alvos_sb}</div>
            <div style='font-size:0.68rem;color:#3a4556;'>alvos</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── COLETAR
if pagina == "Coletar":
    st.markdown("<h1 style='margin-bottom:4px'>⚡ Coletar Leads</h1>", unsafe_allow_html=True)
    st.caption("Configure a busca e aguarde a coleta terminar.")
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        nicho  = st.text_input("Nicho / Tipo de negocio", placeholder="Ex: petshops, mecanicas, saloes...")
    with col2:
        cidade = st.text_input("Cidade / Regiao", placeholder="Ex: Bayeux PB, Joao Pessoa PB...")

    max_leads = st.slider("Quantidade maxima de leads", 5, 50, 20, 5)

    if nicho and cidade:
        query = f"{nicho} em {cidade}"
        st.markdown(f"<div style='color:#3b82f6;font-size:0.85rem;margin:8px 0;'>🔎 {query}</div>",
            unsafe_allow_html=True)

    st.divider()

    iniciar = st.button(
        "Iniciar Coleta",
        disabled=not (nicho and cidade),
        use_container_width=True,
        type="primary",
    )

    if iniciar:
        query = f"{nicho} em {cidade}"
        project_dir   = os.path.dirname(os.path.abspath(__file__))
        scraper_path  = os.path.join(project_dir, "scraper", "google_maps_scraper.py")
        pipeline_path = os.path.join(project_dir, "pipelines", "bronze_pipeline.py")

        with st.spinner("Abrindo Chrome e coletando leads... Aguarde."):
            r1 = subprocess.run(
                [sys.executable, scraper_path, "--query", query, "--max", str(max_leads)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=project_dir,
            )

        log_scraper = r1.stdout + ("\n" + r1.stderr if r1.returncode != 0 else "")

        if r1.returncode != 0:
            st.error("Erro no scraper. Veja o log abaixo.")
            st.code(log_scraper, language="bash")
        else:
            with st.spinner("Salvando no banco..."):
                r2 = subprocess.run(
                    [sys.executable, pipeline_path],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    cwd=project_dir,
                )
            log_pipeline = r2.stdout

            st.success("Coleta finalizada!")
            st.markdown("<div class='section-title'>Log da coleta</div>", unsafe_allow_html=True)
            st.code(log_scraper + "\n" + log_pipeline, language="bash")

            st.session_state.pagina_atual = "Dashboard"
            time.sleep(1)
            st.rerun()


# ── DASHBOARD
elif pagina == "Dashboard":
    st.markdown("<h1 style='margin-bottom:4px'>◈ Dashboard</h1>", unsafe_allow_html=True)
    st.caption("Visao geral dos leads coletados.")
    st.divider()

    df = load_leads()

    if df.empty:
        st.info("Nenhum lead ainda. Va para Coletar Leads para comecar.")
    else:
        total     = len(df)
        sem_site  = int((df["score_digital"] == 0).sum())
        so_social = int((df["score_digital"] == 1).sum())
        tem_site  = int((df["tem_site"] == True).sum())
        pct_sem   = int(sem_site * 100 / total) if total else 0

        st.markdown(f"""
        <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px;'>
            <div style='background:#0d1117;border:1px solid #1e2530;border-radius:14px;padding:24px;'>
                <div class='stat-label'>Total de leads</div>
                <div class='stat-big'>{total}</div>
            </div>
            <div style='background:#0d1117;border:1px solid #7f1d1d;border-radius:14px;padding:24px;'>
                <div class='stat-label' style='color:#f87171;'>Alvos principais</div>
                <div class='stat-big' style='color:#f87171;'>{sem_site}</div>
                <div style='font-size:0.75rem;color:#5a6478;margin-top:4px;'>{pct_sem}% do total</div>
            </div>
            <div style='background:#0d1117;border:1px solid #78350f;border-radius:14px;padding:24px;'>
                <div class='stat-label' style='color:#fbbf24;'>So redes sociais</div>
                <div class='stat-big' style='color:#fbbf24;'>{so_social}</div>
            </div>
            <div style='background:#0d1117;border:1px solid #064e3b;border-radius:14px;padding:24px;'>
                <div class='stat-label' style='color:#34d399;'>Tem site</div>
                <div class='stat-big' style='color:#34d399;'>{tem_site}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='section-title'>Presenca Digital</div>", unsafe_allow_html=True)
            presenca = pd.DataFrame({
                "Categoria": ["Sem presenca", "So redes sociais", "Tem site"],
                "Leads":     [sem_site, so_social, tem_site],
            })
            st.bar_chart(presenca.set_index("Categoria"), color="#3b82f6", height=220)

        with col2:
            st.markdown("<div class='section-title'>Leads por Nicho</div>", unsafe_allow_html=True)
            if "nicho" in df.columns and not df["nicho"].isna().all():
                nc = df["nicho"].value_counts().reset_index()
                nc.columns = ["Nicho", "Leads"]
                st.bar_chart(nc.set_index("Nicho"), color="#3b82f6", height=220)

        st.divider()
        st.markdown("<div class='section-title'>Top Alvos — sem presenca digital</div>", unsafe_allow_html=True)
        alvos = df[df["score_digital"] == 0][["nome","categoria","telefone","avaliacao","cidade","nicho"]].head(10)
        st.dataframe(alvos, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("<div class='section-title'>Coletados recentemente</div>", unsafe_allow_html=True)
        recentes = df[["nome","categoria","telefone","oportunidade","cidade","nicho"]].head(8)
        st.dataframe(recentes, use_container_width=True, hide_index=True)


# ── LEADS
elif pagina == "Leads":
    st.markdown("<h1 style='margin-bottom:4px'>≡ Leads</h1>", unsafe_allow_html=True)
    st.caption("Todos os leads com filtros.")
    st.divider()

    df = load_leads()

    if df.empty:
        st.info("Nenhum lead ainda.")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            cidade_f = st.selectbox("Cidade", ["Todas"] + sorted(df["cidade"].dropna().unique().tolist()))
        with col2:
            nicho_f  = st.selectbox("Nicho",  ["Todos"]  + sorted(df["nicho"].dropna().unique().tolist()))
        with col3:
            op_f     = st.selectbox("Oportunidade", ["Todas","Alta - sem presenca digital",
                        "Media - so redes sociais","Baixa - tem site","Nenhuma - presenca completa"])

        filtered = df.copy()
        if cidade_f != "Todas": filtered = filtered[filtered["cidade"] == cidade_f]
        if nicho_f  != "Todos": filtered = filtered[filtered["nicho"]  == nicho_f]
        if op_f     != "Todas": filtered = filtered[filtered["oportunidade"] == op_f]

        st.caption(f"{len(filtered)} leads encontrados")
        cols = [c for c in ["nome","categoria","telefone","site","avaliacao","oportunidade","cidade","nicho","status_outreach"] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True, hide_index=True)

        st.download_button("Exportar CSV",
            filtered.to_csv(index=False).encode("utf-8"),
            f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv", use_container_width=True)


# ── CONFIGURACOES
elif pagina == "Configuracoes":
    st.markdown("<h1 style='margin-bottom:4px'>⚙ Configuracoes</h1>", unsafe_allow_html=True)
    st.divider()

    try:
        con   = get_connection()
        total = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        logs  = con.execute("SELECT * FROM bronze_log ORDER BY processado_em DESC").df()
        con.close()

        col1, col2 = st.columns(2)
        col1.metric("Total de leads", total)
        col2.metric("Arquivos processados", len(logs))

        if not logs.empty:
            st.markdown("<div class='section-title' style='margin-top:24px;'>Historico</div>", unsafe_allow_html=True)
            st.dataframe(logs, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Erro: {e}")

    st.divider()
    st.markdown("<div class='section-title'>Zona de perigo</div>", unsafe_allow_html=True)
    if st.button("Resetar banco de dados", type="secondary", use_container_width=True):
        reset_db()
        st.success("Banco resetado!")
        time.sleep(1)
        st.rerun()

# ── Page config
st.set_page_config(
    page_title="LeadLakehouse",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Google Fonts + CSS
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
    /* Base */
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background: #080c14; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0d1117;
        border-right: 1px solid #1e2530;
    }
    [data-testid="stSidebar"] * { color: #8892a4 !important; }
    [data-testid="stSidebar"] .stRadio label:hover { color: #fff !important; }

    /* Headings */
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; color: #fff !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #0d1117;
        border: 1px solid #1e2530;
        border-radius: 12px;
        padding: 20px 24px;
    }
    [data-testid="stMetricLabel"] { color: #5a6478 !important; font-size: 0.78rem !important; letter-spacing: 0.08em; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #fff !important; font-family: 'Syne', sans-serif !important; font-size: 2rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

    /* Inputs */
    .stTextInput input, .stSelectbox select {
        background: #0d1117 !important;
        border: 1px solid #1e2530 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }
    .stTextInput input:focus { border-color: #3b82f6 !important; }

    /* Buttons */
    .stButton > button {
        background: #3b82f6 !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;
        padding: 0.6rem 1.4rem !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover { background: #2563eb !important; transform: translateY(-1px); }
    .stButton > button:disabled { background: #1e2530 !important; color: #3a4556 !important; }

    /* Dataframe */
    [data-testid="stDataFrame"] { border: 1px solid #1e2530; border-radius: 10px; overflow: hidden; }

    /* Code block (log) */
    .stCode { background: #0a0e17 !important; border: 1px solid #1e2530 !important; border-radius: 10px !important; font-size: 0.78rem !important; }

    /* Divider */
    hr { border-color: #1e2530 !important; }

    /* Alert / info */
    .stAlert { border-radius: 10px !important; }

    /* Progress bar */
    .stProgress > div > div { background: #3b82f6 !important; }

    /* Slider */
    .stSlider [data-baseweb="slider"] { padding: 0 !important; }

    /* Caption */
    .stCaption { color: #5a6478 !important; }

    /* Badge helper */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .badge-red    { background: #2d1515; color: #f87171; border: 1px solid #7f1d1d; }
    .badge-yellow { background: #2d2515; color: #fbbf24; border: 1px solid #78350f; }
    .badge-green  { background: #152d1e; color: #34d399; border: 1px solid #064e3b; }
    .badge-gray   { background: #1a2030; color: #94a3b8; border: 1px solid #334155; }

    /* Section title */
    .section-title {
        font-family: 'Syne', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #3b82f6;
        margin-bottom: 12px;
    }

    /* Stat number large */
    .stat-big {
        font-family: 'Syne', sans-serif;
        font-size: 3.5rem;
        font-weight: 800;
        color: #fff;
        line-height: 1;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #5a6478;
        margin-top: 6px;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# ── Init
init_db()

# ── Shared state para thread (session_state nao funciona em threads)
_log_buffer     = []
_coleta_pronta  = [False]
_coleta_rodando = [False]


def add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    _log_buffer.append(f"[{ts}] {msg}")


def run_coleta(query: str, max_leads: int):
    """Roda o scraper + pipeline via subprocess."""
    import subprocess

    project_dir   = os.path.dirname(os.path.abspath(__file__))
    scraper_path  = os.path.join(project_dir, "scraper", "google_maps_scraper.py")
    pipeline_path = os.path.join(project_dir, "pipelines", "bronze_pipeline.py")

    try:
        add_log(f"Iniciando coleta: '{query}' | max: {max_leads}")

        result = subprocess.run(
            [sys.executable, scraper_path, "--query", query, "--max", str(max_leads)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=project_dir,
        )
        for line in result.stdout.splitlines():
            if line.strip():
                add_log(line)
        if result.returncode != 0:
            for line in result.stderr.splitlines():
                if line.strip():
                    add_log(f"ERRO: {line}")
            _coleta_rodando[0] = False
            return

        add_log("Rodando pipeline Bronze -> DB...")
        result2 = subprocess.run(
            [sys.executable, pipeline_path],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=project_dir,
        )
        for line in result2.stdout.splitlines():
            if line.strip():
                add_log(line)

        add_log("Coleta finalizada!")
        _coleta_pronta[0]  = True
        _coleta_rodando[0] = False

    except Exception as e:
        add_log(f"ERRO: {e}")
        _coleta_rodando[0] = False