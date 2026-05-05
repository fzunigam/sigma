import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import typer

from sgm.application.render import MarkedMovement, render_marked_movements
from sgm.domain.accounts import Account, AccountType
from sgm.domain.errors import DomainValidationError, NoMarkedMovementsError
from sgm.domain.movements import Movement, MovementType
from sgm.infrastructure.config import default_db_path
from sgm.infrastructure.db import init_db
from sgm.infrastructure.repositories import (
    AccountRepository,
    MovementRepository,
    RenderHistoryRepository,
    TransferRepository,
)
from sgm.interface.formatting import format_table

app = typer.Typer(help="Sigma CLI finance tracker")
account_app = typer.Typer(help="Account commands")
movement_app = typer.Typer(help="Movement commands")
transfer_app = typer.Typer(help="Transfer commands")
render_app = typer.Typer(help="Render commands")
report_app = typer.Typer(help="Reporting commands")


def _db_path_from_context(ctx: typer.Context) -> Path:
    root_obj = (ctx.find_root().obj or {}) if ctx is not None else {}
    db_path = root_obj.get("db_path", default_db_path())
    return Path(db_path)


def _parse_iso8601(timestamp: str) -> datetime:
    parsed = datetime.fromisoformat(timestamp)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _fail(message: str, code: int = 1) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=code)


@app.callback()
def main(
    ctx: typer.Context,
    db: Path = typer.Option(
        default_db_path(),
        "--db",
        help="Path to SQLite database file.",
        dir_okay=False,
        writable=True,
    ),
) -> None:
    """Sigma CLI finance tracker."""
    ctx.obj = {"db_path": db}


@account_app.command("create")
def account_create(
    ctx: typer.Context,
    account_id: str,
    name: str,
    kind: AccountType,
    balance: int,
) -> None:
    if not account_id.strip():
        raise typer.BadParameter("account_id cannot be empty")
    if not name.strip():
        raise typer.BadParameter("name cannot be empty")

    with closing(init_db(_db_path_from_context(ctx))) as connection:
        try:
            AccountRepository(connection).create(
                Account(id=account_id, name=name, kind=kind, balance=balance)
            )
        except sqlite3.IntegrityError as exc:
            _fail(str(exc))

    typer.echo(f"created account {account_id}")


@account_app.command("list")
def account_list(ctx: typer.Context) -> None:
    with closing(init_db(_db_path_from_context(ctx))) as connection:
        accounts = AccountRepository(connection).list_all()

    rows = [[a.id, a.name, a.kind.value, a.balance] for a in accounts]
    typer.echo(format_table(["id", "name", "kind", "balance"], rows))


@movement_app.command("add")
def movement_add(
    ctx: typer.Context,
    movement_id: str,
    account_id: str,
    description: str,
    amount: int,
    movement_type: MovementType,
) -> None:
    if not movement_id.strip():
        raise typer.BadParameter("movement_id cannot be empty")
    if not account_id.strip():
        raise typer.BadParameter("account_id cannot be empty")
    if not description.strip():
        raise typer.BadParameter("description cannot be empty")

    with closing(init_db(_db_path_from_context(ctx))) as connection:
        try:
            MovementRepository(connection).add(
                Movement.new(description, amount, movement_type, account_id),
                movement_id=movement_id,
            )
        except (DomainValidationError, sqlite3.IntegrityError) as exc:
            _fail(str(exc))

    typer.echo(f"added movement {movement_id}")


@movement_app.command("list-marked")
def movement_list_marked(ctx: typer.Context) -> None:
    with closing(init_db(_db_path_from_context(ctx))) as connection:
        movements = MovementRepository(connection).list_marked()

    rows = [
        [
            movement["id"],
            movement["account_id"],
            movement["type"],
            movement["amount"],
            movement["description"],
        ]
        for movement in movements
    ]
    typer.echo(format_table(["id", "account_id", "type", "amount", "description"], rows))


@transfer_app.command("move")
def transfer_move(
    ctx: typer.Context,
    transfer_id: str,
    source_account_id: str,
    target_account_id: str,
    amount: int,
    created_at: str = typer.Option(..., "--created-at", help="ISO-8601 timestamp"),
) -> None:
    if source_account_id == target_account_id:
        raise typer.BadParameter("source and target accounts must differ")

    try:
        created_at_dt = _parse_iso8601(created_at)
    except ValueError:
        raise typer.BadParameter("created_at must be ISO-8601") from None

    with closing(init_db(_db_path_from_context(ctx))) as connection:
        try:
            TransferRepository(connection).add(
                transfer_id=transfer_id,
                source_account_id=source_account_id,
                target_account_id=target_account_id,
                amount=amount,
                created_at=created_at_dt,
            )
        except sqlite3.IntegrityError as exc:
            _fail(str(exc))

    typer.echo(f"recorded transfer {transfer_id}")


@render_app.command("run")
def render_run(ctx: typer.Context, snapshot_id: str) -> None:
    with closing(init_db(_db_path_from_context(ctx))) as connection:
        movement_repository = MovementRepository(connection)
        movement_rows = movement_repository.list_marked()
        movements = [
            MarkedMovement(
                id=row["id"],
                type=MovementType(row["type"]),
                amount=int(row["amount"]),
                marked=bool(row["marked"]),
            )
            for row in movement_rows
        ]

        try:
            snapshot, processed_ids = render_marked_movements(movements)
        except NoMarkedMovementsError as exc:
            _fail(str(exc))

        movement_repository.unmark_many(processed_ids)

        RenderHistoryRepository(connection).add_snapshot(
            snapshot_id=snapshot_id,
            rendered_at=snapshot.metadata.rendered_at,
            income_total=snapshot.income_total,
            expense_total=snapshot.expense_total,
            net=snapshot.net,
            count=snapshot.metadata.count,
        )

    typer.echo(
        "\n".join(
            [
                f"Income: {snapshot.income_total}",
                f"Expense: {snapshot.expense_total}",
                f"Net: {snapshot.net}",
                f"Count: {snapshot.metadata.count}",
            ]
        )
    )


@report_app.command("balances")
def report_balances(ctx: typer.Context) -> None:
    with closing(init_db(_db_path_from_context(ctx))) as connection:
        accounts = AccountRepository(connection).list_all()

    rows = [[account.id, account.name, account.balance] for account in accounts]
    total_balance = sum(account.balance for account in accounts)
    typer.echo(format_table(["id", "name", "balance"], rows))
    typer.echo(f"total_balance={total_balance}")


@report_app.command("render-history")
def report_render_history(ctx: typer.Context) -> None:
    with closing(init_db(_db_path_from_context(ctx))) as connection:
        history_rows = RenderHistoryRepository(connection).list_all()

    rows = [
        [
            row["id"],
            row["rendered_at"],
            row["income_total"],
            row["expense_total"],
            row["net"],
            row["count"],
        ]
        for row in history_rows
    ]
    typer.echo(
        format_table(
            ["id", "rendered_at", "income_total", "expense_total", "net", "count"], rows
        )
    )


app.add_typer(account_app, name="account")
app.add_typer(movement_app, name="movement")
app.add_typer(transfer_app, name="transfer")
app.add_typer(render_app, name="render")
app.add_typer(report_app, name="report")
