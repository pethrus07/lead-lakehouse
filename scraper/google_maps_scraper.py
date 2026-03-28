# -*- coding: utf-8 -*-
"""
LeadLakehouse – Google Maps Scraper v0.2
Autor: Pedro Michael
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
from webdriver_manager.chrome import ChromeDriverManager
import unicodedata
import urllib.parse
import time
import json
import csv
import os
from datetime import datetime

SEARCH_QUERY = "saloes de beleza em Bayeux PB"
MAX_LEADS    = 20
OUTPUT_DIR   = "data/bronze/google_maps"

# Sinonimos para reconhecimento de nicho
SINONIMOS = {
    "petshop":     ["pet", "animal", "veterinari", "canil", "banho", "tosa"],
    "informatica": ["inform", "computador", "notebook", "celular", "tecnic", "eletron"],
    "salao":       ["cabeleir", "beleza", "estetica", "studio", "hair", "nail"],
    "restaurante": ["restaur", "lanchon", "pizzar", "hamburguer", "comida"],
    "farmacia":    ["farmac", "drogari"],
    "mecanica":    ["mecanic", "automovel", "carro", "auto", "oficin"],
    "odonto":      ["odont", "dentist", "clinica"],
    "academia":    ["academ", "fitness", "gym"],
}


def normalizar(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()


def setup_driver(headless: bool = False) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def dismiss_consent(driver: webdriver.Chrome) -> None:
    try:
        btns = driver.find_elements(By.XPATH,
            '//button[.//span[contains(text(),"Aceitar") or contains(text(),"Accept")]]')
        if btns:
            btns[0].click()
            time.sleep(1.5)
    except Exception:
        pass


def search_google_maps(driver: webdriver.Chrome, query: str) -> None:
    encoded = urllib.parse.quote_plus(query)
    driver.get(f"https://www.google.com/maps/search/{encoded}")
    time.sleep(3)
    dismiss_consent(driver)
    time.sleep(2)


def scroll_results(driver: webdriver.Chrome, max_results: int) -> None:
    try:
        feed = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
        )
    except Exception:
        return

    last_count = 0
    attempts   = 0

    while attempts < 15:
        cards = driver.find_elements(By.XPATH, '//div[@role="feed"]//a[@href]')
        count = len(cards)
        if count >= max_results:
            break
        if count == last_count:
            attempts += 1
        else:
            attempts = 0
        last_count = count
        driver.execute_script("arguments[0].scrollTop += 800;", feed)
        time.sleep(1.5)


def get_result_links(driver: webdriver.Chrome, max_results: int) -> list:
    cards = driver.find_elements(By.XPATH,
        '//div[@role="feed"]//a[contains(@href, "maps/place")]')
    links = []
    seen  = set()
    for card in cards:
        href = card.get_attribute("href")
        if href and href not in seen:
            seen.add(href)
            links.append(href)
        if len(links) >= max_results:
            break
    return links


def extract_lead(driver: webdriver.Chrome, url: str) -> dict:
    driver.get(url)
    time.sleep(2)

    lead = {
        "nome":             None,
        "categoria":        None,
        "telefone":         None,
        "site":             None,
        "avaliacao":        None,
        "total_avaliacoes": None,
        "redes_sociais":    [],
        "tem_site":         False,
        "score_digital":    0,
        "url_maps":         url,
        "coletado_em":      datetime.now().isoformat(),
    }

    try:
        lead["nome"] = driver.find_element(
            By.XPATH, '//h1[contains(@class,"DUwDvf")]').text.strip()
    except Exception:
        pass

    try:
        lead["categoria"] = driver.find_element(
            By.XPATH, '//button[contains(@jsaction,"pane.rating.category")]').text.strip()
    except Exception:
        pass

    try:
        r = driver.find_element(By.XPATH, '//span[@class="ceNzKf"]')
        lead["avaliacao"] = float(r.get_attribute("aria-label").split()[0].replace(",", "."))
    except Exception:
        pass

    try:
        rv = driver.find_element(By.XPATH,
            '//span[contains(@aria-label,"avaliações") or contains(@aria-label,"reviews")]')
        digits = "".join(filter(str.isdigit, (rv.get_attribute("aria-label") or "").split()[0]))
        if digits:
            lead["total_avaliacoes"] = int(digits)
    except Exception:
        pass

    try:
        ph = driver.find_element(By.XPATH,
            '//button[contains(@aria-label,"Telefone") or contains(@aria-label,"Phone")]')
        lead["telefone"] = ph.get_attribute("aria-label").split(":")[-1].strip()
    except Exception:
        pass

    try:
        s = driver.find_element(By.XPATH,
            '//a[contains(@aria-label,"Site") or contains(@aria-label,"Website") or @data-item-id="authority"]')
        lead["site"]     = s.get_attribute("href")
        lead["tem_site"] = True
    except Exception:
        pass

    social_kw = ["instagram", "facebook", "tiktok", "twitter", "linkedin", "youtube"]
    try:
        for link in driver.find_elements(By.TAG_NAME, "a"):
            href = link.get_attribute("href") or ""
            for kw in social_kw:
                if kw in href.lower() and href not in lead["redes_sociais"]:
                    lead["redes_sociais"].append(href)
    except Exception:
        pass

    score = 0
    if lead["tem_site"]:        score += 2
    if lead["redes_sociais"]:   score += 1
    lead["score_digital"] = score

    if score == 0:   lead["oportunidade"] = "Alta - sem presenca digital"
    elif score == 1: lead["oportunidade"] = "Media - so redes sociais"
    elif score == 2: lead["oportunidade"] = "Baixa - tem site"
    else:            lead["oportunidade"] = "Nenhuma - presenca completa"

    return lead


def is_relevant(lead: dict, query: str) -> bool:
    stopwords = {"de","do","da","em","no","na","e","o","a","os","as","para","com",
                 "pb","rj","sp","mg","ba","ce","pe","rn","pi","ma","al","se"}

    palavras = [normalizar(p) for p in query.split()
                if normalizar(p) not in stopwords and len(p) > 2]

    nome      = normalizar(lead.get("nome")      or "")
    categoria = normalizar(lead.get("categoria") or "")
    texto     = nome + " " + categoria

    # Correspondencia direta
    for p in palavras[:3]:
        if p in texto:
            return True

    # Sinonimos
    for p in palavras[:3]:
        for chave, sins in SINONIMOS.items():
            if chave in p or p in chave:
                for s in sins:
                    if s in texto:
                        return True

    # Fallback: sem categoria capturada, aceita
    if not lead.get("categoria"):
        return True

    return False


def save_results(leads: list, query: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = query.replace(" ", "_")[:50]
    base       = f"{timestamp}_{safe_query}"

    json_path = os.path.join(output_dir, f"{base}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"query": query, "leads": leads}, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(output_dir, f"{base}.csv")
    if leads:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(leads[0].keys()))
            writer.writeheader()
            for lead in leads:
                row = lead.copy()
                row["redes_sociais"] = " | ".join(lead["redes_sociais"])
                writer.writerow(row)

    return json_path


def run(query: str = SEARCH_QUERY, max_leads: int = MAX_LEADS,
        log_fn=None, headless: bool = False) -> list:
    """
    log_fn: funcao opcional para receber mensagens de log (ex: para o Streamlit).
    """
    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    driver = setup_driver(headless=headless)
    leads  = []

    try:
        log(f"Buscando: '{query}'")
        search_google_maps(driver, query)

        log(f"Carregando resultados...")
        scroll_results(driver, max_leads)

        links = get_result_links(driver, max_leads)
        log(f"{len(links)} resultados encontrados")

        ignorados = 0
        for i, link in enumerate(links, 1):
            try:
                lead = extract_lead(driver, link)
                if not is_relevant(lead, query):
                    ignorados += 1
                    log(f"  [{i}/{len(links)}] IGNORADO: {lead['nome']} ({lead['categoria']})")
                    continue
                leads.append(lead)
                log(f"  [{i}/{len(links)}] OK: {lead['nome']} | {lead['oportunidade']}")
            except Exception as e:
                log(f"  [{i}/{len(links)}] Erro: {e}")
            time.sleep(1)

    finally:
        driver.quit()

    if leads:
        path = save_results(leads, query, OUTPUT_DIR)
        log(f"Salvo em: {path}")
        log(f"Total: {len(leads)} leads | {ignorados} ignorados")

    return leads


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query",   type=str,  default=SEARCH_QUERY)
    parser.add_argument("--max",     type=int,  default=MAX_LEADS)
    parser.add_argument("--headless",action="store_true")
    args = parser.parse_args()
    run(query=args.query, max_leads=args.max, headless=args.headless)