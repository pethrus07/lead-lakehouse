# -*- coding: utf-8 -*-
"""
LeadLakehouse – WhatsApp Outreach
Autor: Pedro Michael

Dispara mensagens via WhatsApp Web usando Selenium.
A/B Test: mensagem A (comercial) vs mensagem B (pessoal/indicativa).
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import sys
import urllib.parse
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_connection

# ─────────────────────────────────────────────
# 💬  MENSAGENS A/B
# ─────────────────────────────────────────────

MENSAGEM_A = """Oi, tudo bem? Vi seu negocio no Google Maps e percebi que voce ainda nao tem um site profissional.

Hoje, clientes pesquisam antes de visitar — e quem nao aparece online perde espaco para a concorrencia.

Trabalho com criacao de sites profissionais para negocios locais. Posso te enviar uma proposta rapida?"""

MENSAGEM_B = """Ola! Me foi indicado seu negocio e fui dar uma olhada no Google — vi que voce ainda nao tem um site.

Tenho ajudado negocios aqui da regiao a conseguir mais clientes com um site profissional simples e direto.

Posso te mostrar como funcionaria no seu caso?"""

# Tenta carregar mensagens customizadas salvas pelo Streamlit
_msgs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mensagens.json")
_nicho_filtro  = None
_cidade_filtro = None

if os.path.exists(_msgs_path):
    try:
        with open(_msgs_path, "r", encoding="utf-8") as f:
            _cfg = json.load(f)
        MENSAGEM_A     = _cfg.get("msg_a", MENSAGEM_A)
        MENSAGEM_B     = _cfg.get("msg_b", MENSAGEM_B)
        _nicho_filtro  = _cfg.get("nicho")
        _cidade_filtro = _cfg.get("cidade")
    except Exception:
        pass

# ─────────────────────────────────────────────


def setup_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    # Salva sessao do WhatsApp para nao precisar escanear QR sempre
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".wpp_session")
    os.makedirs(profile_dir, exist_ok=True)
    options.add_argument(f"--user-data-dir={os.path.abspath(profile_dir)}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def aguardar_whatsapp(driver: webdriver.Chrome) -> bool:
    """Aguarda o WhatsApp Web carregar (QR code ou já logado)."""
    print("Abrindo WhatsApp Web...")
    driver.get("https://web.whatsapp.com")

    print("Aguardando login (escaneie o QR code se necessario)...")
    try:
        # Aguarda até 60s pelo elemento principal do chat
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//div[@id="side"]'))
        )
        print("WhatsApp Web carregado!")
        return True
    except Exception:
        print("ERRO: Timeout aguardando WhatsApp Web.")
        return False


def enviar_mensagem(driver: webdriver.Chrome, telefone: str, mensagem: str) -> bool:
    """
    Envia mensagem para um numero via WhatsApp Web.
    Telefone deve estar no formato: 83999991234 (sem + ou espacos)
    """
    # Limpa o telefone
    telefone_limpo = "".join(filter(str.isdigit, telefone))

    # Adiciona DDI 55 se nao tiver
    if len(telefone_limpo) <= 11:
        telefone_limpo = "55" + telefone_limpo

    if len(telefone_limpo) < 12:
        print(f"  Telefone invalido: {telefone}")
        return False

    try:
        # Abre conversa direta pela URL
        encoded_msg = urllib.parse.quote(mensagem)
        url = f"https://web.whatsapp.com/send?phone={telefone_limpo}&text={encoded_msg}"
        driver.get(url)

        # Aguarda campo de mensagem
        wait = WebDriverWait(driver, 20)
        input_box = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
        ))
        time.sleep(2)

        # Verifica se nao apareceu erro de numero invalido
        try:
            erro = driver.find_element(By.XPATH, '//div[contains(text(),"Phone number shared via url is invalid")]')
            print(f"  Numero invalido no WhatsApp: {telefone}")
            return False
        except Exception:
            pass

        # Envia a mensagem
        input_box.send_keys(Keys.ENTER)
        time.sleep(2)
        print(f"  Mensagem enviada para {telefone_limpo}")
        return True

    except Exception as e:
        print(f"  Erro ao enviar para {telefone}: {e}")
        return False


def marcar_contatado(lead_id: int, versao_msg: str) -> None:
    """Atualiza status do lead no banco."""
    con = get_connection()
    con.execute("""
        UPDATE leads
        SET status_outreach = ?
        WHERE id = ?
    """, [f"contatado_msg_{versao_msg}", lead_id])
    con.close()


def carregar_alvos(limite: int = 30) -> list:
    """Carrega leads alvos que ainda não foram contatados."""
    con = get_connection()

    filtros = """
        WHERE score_digital = 0
          AND telefone IS NOT NULL
          AND telefone != ''
          AND status_outreach = 'pendente'
    """
    params = []

    if _nicho_filtro and _nicho_filtro != "Todos":
        filtros += " AND nicho = ?"
        params.append(_nicho_filtro)

    if _cidade_filtro and _cidade_filtro != "Todas":
        filtros += " AND cidade = ?"
        params.append(_cidade_filtro)

    filtros += " ORDER BY avaliacao DESC NULLS LAST LIMIT ?"
    params.append(limite)

    rows = con.execute(f"SELECT id, nome, telefone, nicho, cidade FROM leads {filtros}", params).fetchall()
    con.close()

    return [
        {"id": r[0], "nome": r[1], "telefone": r[2], "nicho": r[3], "cidade": r[4]}
        for r in rows
    ]


def run(limite: int = 30, log_fn=None) -> dict:
    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    alvos = carregar_alvos(limite)

    if not alvos:
        log("Nenhum alvo disponivel para disparar.")
        return {"enviados": 0, "erros": 0, "total": 0}

    log(f"{len(alvos)} alvos carregados para disparo")

    driver = setup_driver()
    enviados = 0
    erros    = 0

    try:
        if not aguardar_whatsapp(driver):
            log("Falha ao carregar WhatsApp Web.")
            return {"enviados": 0, "erros": 0, "total": len(alvos)}

        for i, lead in enumerate(alvos, 1):
            # A/B: pares recebem A, impares recebem B
            versao  = "A" if i % 2 == 0 else "B"
            msg     = MENSAGEM_A if versao == "A" else MENSAGEM_B

            log(f"[{i}/{len(alvos)}] {lead['nome']} | {lead['telefone']} | Msg {versao}")

            ok = enviar_mensagem(driver, lead["telefone"], msg)

            if ok:
                marcar_contatado(lead["id"], versao)
                enviados += 1
            else:
                erros += 1

            # Intervalo entre mensagens (evita ban)
            time.sleep(8)

    finally:
        driver.quit()

    log(f"Concluido! {enviados} enviados | {erros} erros")
    return {"enviados": enviados, "erros": erros, "total": len(alvos)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=30)
    args = parser.parse_args()
    run(limite=args.limite)