"""CLI do lead-lakehouse (`llh`)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from .. import __version__

app = typer.Typer(help="lead-lakehouse — motor de prospecção multi-fonte", no_args_is_help=True)

# Cada comando importa o que precisa DENTRO da própria função: é isso que faz `llh versao` e
# `llh fontes` responderem sem exigir Postgres, Playwright ou pandas instalados.


@app.command()
def versao() -> None:
    """Mostra a versão."""
    typer.echo(f"lead-lakehouse {__version__}")


@app.command()
def fontes() -> None:
    """Lista as fontes de dados registradas."""
    from ..sources.bootstrap import registrar_todas
    from ..sources.registry import resumo

    registrar_todas()
    for ln in resumo():
        typer.echo(
            f"- {ln['fonte']:<14} {ln['papel']:<14} "
            f"browser={ln['browser']} pago={ln['pago']} tos_ok={ln['tos_ok']}"
        )


@app.command()
def init_db() -> None:
    """Cria as tabelas no Postgres (dev). Em produção, usar Alembic."""
    from ..infra.db.base import criar_tabelas

    criar_tabelas()
    typer.echo("Tabelas criadas.")


@app.command()
def exemplo_icp(saida: str = "icp_exemplo.json") -> None:
    """Gera um arquivo ICP de exemplo para você editar."""
    from ..domain.icp import ICP, Filtros, Regiao

    icp = ICP(
        nome="Salões sem site em João Pessoa",
        nicho=["salão de beleza", "barbearia"],
        regiao=Regiao(municipio="João Pessoa", uf="PB"),
        fontes=["openstreetmap"],
        filtros=Filtros(tem_site=False),
        limite=30,
    )
    Path(saida).write_text(icp.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"ICP de exemplo escrito em {saida}")


@app.command()
def prospectar(
    icp: str = typer.Option(..., help="Caminho de um arquivo JSON de ICP"),
    persistir: bool = typer.Option(True, help="Salvar leads no Postgres"),
    enriquecer: bool = typer.Option(True, help="Rodar enriquecimento (visita-site, CNPJ)"),
    top: int = typer.Option(15, help="Quantos leads mostrar"),
) -> None:
    """Roda a prospecção de um ICP e lista os leads ranqueados."""
    from ..app.prospeccao import prospectar as _prospectar
    from ..domain.icp import ICP
    from ..sources.bootstrap import registrar_todas

    registrar_todas()
    spec = ICP.model_validate_json(Path(icp).read_text(encoding="utf-8"))
    typer.echo(f"Prospectando: {spec.nome}  (fontes: {[str(f) for f in spec.fontes] or 'todas'})")

    leads = asyncio.run(_prospectar(spec, persistir=persistir, enriquecer_flag=enriquecer))

    typer.echo(f"\n{len(leads)} leads. Top {min(top, len(leads))}:\n")
    for ld in leads[:top]:
        b = ld.business
        typer.echo(
            f"  [{ld.score.valor:+.0f} {ld.score.nivel}] {b.nome or '?'}"
            f"  · {b.telefone_e164 or b.telefone or 's/tel'}"
            f"  · {'site' if b.tem_site else 'SEM SITE'}"
            f"  · {b.municipio or ''}"
        )
    if persistir and leads:
        typer.echo("\nLeads salvos no Postgres (tabela leads).")


@app.command(name="enviar-zapagente")
def enviar_zapagente(
    icp_nome: str = typer.Option("", help="Enviar só os leads deste ICP (vazio = todos)"),
    limite: int = typer.Option(0, help="Máximo de leads a enviar (0 = sem limite)"),
    email: str = typer.Option("", help="Login no zapagente (se não usar token)"),
    senha: str = typer.Option("", help="Senha no zapagente"),
    dry_run: bool = typer.Option(False, help="Só conta, não envia"),
) -> None:
    """Envia leads pendentes ao zapagente (contatos + tags)."""
    from ..app.envio import enviar_ao_zapagente
    from ..integrations.zapagente.client import ZapagenteError

    try:
        res = asyncio.run(
            enviar_ao_zapagente(
                icp_nome or None, limite or None, email or None, senha or None, dry_run
            )
        )
    except ZapagenteError as e:
        typer.echo(f"Erro: {e}")
        raise typer.Exit(code=1) from e
    prefixo = "[dry-run] " if dry_run else ""
    typer.echo(f"{prefixo}Enviados: {res['enviados']} | erros: {res['erros']} "
               f"| ignorados (sem telefone): {res['ignorados']}")


if __name__ == "__main__":
    app()
