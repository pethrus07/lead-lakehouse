"""
LeadLakehouse – Database (DuckDB)
Autor: Pedro Michael
"""

import duckdb
import os

DB_PATH = "data/leads.duckdb"


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return duckdb.connect(DB_PATH, read_only=read_only)


def init_db() -> None:
    con = get_connection()
    con.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id                   INTEGER PRIMARY KEY,
            nome                 VARCHAR,
            categoria            VARCHAR,
            telefone             VARCHAR,
            site                 VARCHAR,
            avaliacao            FLOAT,
            total_avaliacoes     INTEGER,
            redes_sociais        VARCHAR,
            tem_site             BOOLEAN,
            score_digital        INTEGER,
            oportunidade         VARCHAR,
            url_maps             VARCHAR UNIQUE,
            coletado_em          TIMESTAMP,
            fonte                VARCHAR,
            cidade               VARCHAR,
            nicho                VARCHAR,
            status_outreach      VARCHAR DEFAULT 'pendente'
        )
    """)
    con.execute("CREATE SEQUENCE IF NOT EXISTS leads_id_seq START 1")
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze_log (
            id            INTEGER PRIMARY KEY,
            arquivo       VARCHAR UNIQUE,
            fonte         VARCHAR,
            total_bruto   INTEGER,
            inseridos     INTEGER,
            duplicados    INTEGER,
            processado_em TIMESTAMP DEFAULT current_timestamp
        )
    """)
    con.execute("CREATE SEQUENCE IF NOT EXISTS bronze_log_id_seq START 1")
    con.close()


def reset_db() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    print("Banco resetado com sucesso.")


if __name__ == "__main__":
    init_db()