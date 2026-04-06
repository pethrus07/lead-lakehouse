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
        ["Coletar", "Dashboard", "Leads", "Outreach", "Configuracoes"],
        format_func=lambda x: {
            "Coletar":       "⚡  Coletar Leads",
            "Dashboard":     "◈  Dashboard",
            "Leads":         "≡  Leads",
            "Outreach":      "✉  Outreach",
            "Configuracoes": "⚙  Configuracoes",
        }[x],
        label_visibility="collapsed",
        key="nav_radio",
        index=["Coletar", "Dashboard", "Leads", "Outreach", "Configuracoes"].index(
            st.session_state.pagina_atual if st.session_state.pagina_atual in
            ["Coletar", "Dashboard", "Leads", "Outreach", "Configuracoes"] else "Coletar"
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


# ── OUTREACH
elif pagina == "Outreach":
    st.markdown("<h1 style='margin-bottom:4px'>✉ Outreach</h1>", unsafe_allow_html=True)
    st.caption("Selecione os alvos, configure a mensagem e acompanhe o funil.")
    st.divider()

    df = load_leads()

    if df.empty:
        st.info("Nenhum lead no banco ainda.")
    else:
        pendentes   = int(((df["score_digital"] == 0) & (df["status_outreach"] == "pendente") & df["telefone"].notna() & (df["telefone"] != "")).sum())
        contatados  = int(df["status_outreach"].str.startswith("contatado", na=False).sum())
        responderam = int((df["status_outreach"] == "respondeu").sum())
        fechados    = int((df["status_outreach"] == "fechado").sum())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Alvos pendentes",  pendentes)
        c2.metric("Contatados",       contatados)
        c3.metric("Responderam",      responderam)
        c4.metric("Fechados",         fechados)

        st.divider()

        tab1, tab2, tab3 = st.tabs(["🚀  Disparar", "📋  Acompanhar", "✏️  Atualizar Status"])

        with tab1:
            st.markdown("<div class='section-title' style='margin-top:16px;'>Selecionar Alvos</div>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                nicho_f = st.selectbox("Filtrar por nicho", ["Todos"] + sorted(df["nicho"].dropna().unique().tolist()), key="out_nicho")
            with col2:
                cidade_f = st.selectbox("Filtrar por cidade", ["Todas"] + sorted(df["cidade"].dropna().unique().tolist()), key="out_cidade")

            alvos = df[(df["score_digital"] == 0) & (df["status_outreach"] == "pendente") & df["telefone"].notna() & (df["telefone"] != "")].copy()
            if nicho_f  != "Todos": alvos = alvos[alvos["nicho"]  == nicho_f]
            if cidade_f != "Todas": alvos = alvos[alvos["cidade"] == cidade_f]

            st.caption(f"{len(alvos)} alvos disponiveis")
            if not alvos.empty:
                cols_alvos = [c for c in ["nome","categoria","telefone","avaliacao","nicho","cidade"] if c in alvos.columns]
                st.dataframe(alvos[cols_alvos].head(20), use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("<div class='section-title'>Mensagens A/B</div>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Mensagem A — Comercial/Direta**")
                msg_a = st.text_area("msg_a", label_visibility="collapsed", value="Oi, tudo bem? Vi seu negocio no Google Maps e percebi que voce ainda nao tem um site profissional.\n\nHoje, clientes pesquisam antes de visitar — e quem nao aparece online perde espaco para a concorrencia.\n\nTrabalho com criacao de sites profissionais para negocios locais. Posso te enviar uma proposta rapida?", height=160, key="txa")
            with col2:
                st.markdown("**Mensagem B — Pessoal/Indicativa**")
                msg_b = st.text_area("msg_b", label_visibility="collapsed", value="Ola! Me foi indicado seu negocio e fui dar uma olhada no Google — vi que voce ainda nao tem um site.\n\nTenho ajudado negocios aqui da regiao a conseguir mais clientes com um site profissional simples e direto.\n\nPosso te mostrar como funcionaria no seu caso?", height=160, key="txb")

            st.divider()
            limite = st.slider("Quantidade de disparos", 5, max(5, min(50, len(alvos))) if len(alvos) > 0 else 5, min(30, max(5, len(alvos))), 5, key="out_limite")

            st.markdown(f"""
            <div style='background:#0d1117;border:1px solid #1e2530;border-radius:10px;padding:14px 18px;margin-bottom:16px;font-size:0.85rem;color:#8892a4;'>
                <strong style='color:#fff;'>{limite}</strong> disparos —
                <strong style='color:#3b82f6;'>{limite//2} Msg A</strong> e
                <strong style='color:#fbbf24;'>{limite - limite//2} Msg B</strong> · Intervalo de 8s entre cada envio
            </div>
            """, unsafe_allow_html=True)

            if st.button("Iniciar Disparo via WhatsApp", disabled=len(alvos) == 0, use_container_width=True, type="primary", key="btn_disparar"):
                import json as _json
                project_dir  = os.path.dirname(os.path.abspath(__file__))
                msgs_path    = os.path.join(project_dir, "outreach", ".mensagens.json")
                sender_path  = os.path.join(project_dir, "outreach", "whatsapp_sender.py")
                with open(msgs_path, "w", encoding="utf-8") as f:
                    _json.dump({"msg_a": msg_a, "msg_b": msg_b, "nicho": nicho_f, "cidade": cidade_f}, f, ensure_ascii=False)
                with st.spinner("Abrindo WhatsApp Web... Escaneie o QR code se necessario."):
                    result = subprocess.run(
                        [sys.executable, sender_path, "--limite", str(limite)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        cwd=project_dir,
                    )
                log_out = result.stdout + ("\n" + result.stderr if result.stderr.strip() else "")
                st.markdown("<div class='section-title'>Log do disparo</div>", unsafe_allow_html=True)
                st.code(log_out, language="bash")
                if result.returncode == 0:
                    st.success("Disparo concluido!")
                    st.rerun()
                else:
                    st.error("Erro no disparo. Veja o log acima.")

        with tab2:
            st.markdown("<div class='section-title' style='margin-top:16px;'>Funil de Contatos</div>", unsafe_allow_html=True)
            status_f = st.selectbox("Filtrar por status", ["Todos","contatado_msg_A","contatado_msg_B","respondeu","em_negociacao","fechado","perdido"], key="acomp_status")
            acomp = df[df["status_outreach"] != "pendente"].copy()
            if status_f != "Todos":
                acomp = acomp[acomp["status_outreach"] == status_f]
            if acomp.empty:
                st.info("Nenhum contato realizado ainda.")
            else:
                st.caption(f"{len(acomp)} contatos")
                cols_a = [c for c in ["nome","telefone","nicho","cidade","status_outreach"] if c in acomp.columns]
                st.dataframe(acomp[cols_a], use_container_width=True, hide_index=True)

        with tab3:
            st.markdown("<div class='section-title' style='margin-top:16px;'>Atualizar Status Manualmente</div>", unsafe_allow_html=True)
            st.caption("Registre respostas, negociacoes e fechamentos.")
            contatados_df = df[df["status_outreach"] != "pendente"].copy()
            if contatados_df.empty:
                st.info("Nenhum lead contatado ainda.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    nome_sel = st.selectbox("Selecione o lead", contatados_df["nome"].tolist(), key="upd_nome")
                with col2:
                    novo_status = st.selectbox("Novo status", ["contatado_msg_A","contatado_msg_B","respondeu","em_negociacao","fechado","perdido"], key="upd_status")
                if st.button("Atualizar", use_container_width=True, key="btn_atualizar"):
                    lead_row = contatados_df[contatados_df["nome"] == nome_sel].iloc[0]
                    con = get_connection()
                    con.execute("UPDATE leads SET status_outreach = ? WHERE id = ?", [novo_status, int(lead_row["id"])])
                    con.close()
                    st.success(f"'{nome_sel}' atualizado para '{novo_status}'!")
                    time.sleep(1)
                    st.rerun()


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