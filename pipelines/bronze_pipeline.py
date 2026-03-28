"""
LeadLakehouse – Pipeline Bronze → DB
Autor: Pedro Michael
"""

import json
import os
import re
import glob
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import get_connection, init_db, DB_PATH

BRONZE_DIR = "data/bronze/google_maps"


def parse_cidade_nicho(filename: str) -> tuple:
    name  = os.path.splitext(os.path.basename(filename))[0]
    parts = name[16:].replace("_", " ")
    match = re.split(r"\s+em\s+", parts, maxsplit=1, flags=re.IGNORECASE)
    if len(match) == 2:
        return match[0].strip(), match[1].strip()
    return parts.strip(), "desconhecida"


def insert_leads(con, rows: list, cidade: str, nicho: str) -> tuple:
    inseridos  = 0
    duplicados = 0

    for row in rows:
        try:
            con.execute("""
                INSERT INTO leads (
                    id, nome, categoria, telefone, site, avaliacao, total_avaliacoes,
                    redes_sociais, tem_site, score_digital, oportunidade,
                    url_maps, coletado_em, fonte, cidade, nicho, status_outreach
                ) VALUES (
                    nextval('leads_id_seq'),
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
            """, [
                row.get("nome"),
                row.get("categoria"),
                row.get("telefone"),
                row.get("site"),
                row.get("avaliacao"),
                row.get("total_avaliacoes"),
                " | ".join(row.get("redes_sociais") or []),
                bool(row.get("tem_site", False)),
                int(row.get("score_digital", 0)),
                row.get("oportunidade"),
                row.get("url_maps"),
                row.get("coletado_em"),
                "google_maps",
                cidade,
                nicho,
                "pendente",
            ])
            inseridos += 1
        except Exception:
            duplicados += 1

    return inseridos, duplicados


def run_pipeline(bronze_dir: str = BRONZE_DIR, log_fn=None) -> dict:
    def log(msg):
        print(msg)
        if log_fn:
            log_fn(msg)

    init_db()
    con = get_connection()

    json_files = sorted(glob.glob(os.path.join(bronze_dir, "*.json")))
    if not json_files:
        log("Nenhum arquivo JSON encontrado.")
        con.close()
        return {"inseridos": 0, "duplicados": 0, "arquivos": 0}

    total_inseridos  = 0
    total_duplicados = 0
    total_arquivos   = 0

    for filepath in json_files:
        filename = os.path.basename(filepath)

        already = con.execute(
            "SELECT COUNT(*) FROM bronze_log WHERE arquivo = ?", [filename]
        ).fetchone()[0]

        if already:
            log(f"Ja processado: {filename}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        leads = data.get("leads", [])
        nicho, cidade = parse_cidade_nicho(filename)

        inseridos, duplicados = insert_leads(con, leads, cidade, nicho)

        con.execute("""
            INSERT INTO bronze_log (id, arquivo, fonte, total_bruto, inseridos, duplicados)
            VALUES (nextval('bronze_log_id_seq'), ?, ?, ?, ?, ?)
        """, [filename, "google_maps", len(leads), inseridos, duplicados])

        log(f"OK: {filename} | {inseridos} inseridos | {duplicados} duplicados")
        total_inseridos  += inseridos
        total_duplicados += duplicados
        total_arquivos   += 1

    total_db = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    alvos    = con.execute("SELECT COUNT(*) FROM leads WHERE score_digital = 0").fetchone()[0]
    con.close()

    log(f"Concluido | Total no banco: {total_db} | Alvos: {alvos}")
    return {
        "inseridos":  total_inseridos,
        "duplicados": total_duplicados,
        "arquivos":   total_arquivos,
        "total_db":   total_db,
        "alvos":      alvos,
    }


if __name__ == "__main__":
    result = run_pipeline()
    print(result)