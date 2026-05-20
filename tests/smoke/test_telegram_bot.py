import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from sgm.infrastructure.database import init_db, clear_db, get_accounts, get_marked_total
from sgm.telegram_bot import SigmaTelegramBot


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    db_path = tmp_path / "sigma.db"

    from sgm.infrastructure import database
    monkeypatch.setattr(database, "get_db_path", lambda: db_path)

    init_db(db_path)
    yield
    clear_db(db_path)


def make_mock_update(user_id: int, text: str) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def test_telegram_unauthorized_user() -> None:
    bot = SigmaTelegramBot(token="test_token", allowed_users=[12345])
    update = make_mock_update(user_id=99999, text="status")
    context = MagicMock()

    asyncio.run(bot.handle_message(update, context))

    # Assert bot did not reply
    update.message.reply_text.assert_not_called()


def test_telegram_help_command() -> None:
    bot = SigmaTelegramBot(token="test_token", allowed_users=[12345])
    update = make_mock_update(user_id=12345, text="/help")
    context = MagicMock()

    asyncio.run(bot.handle_message(update, context))

    update.message.reply_text.assert_called_once()
    args, kwargs = update.message.reply_text.call_args
    assert "Sigma Telegram Bot Help" in args[0]
    assert kwargs.get("parse_mode") == "HTML"


def test_telegram_status_command() -> None:
    # Setup accounts
    from sgm.infrastructure.database import create_account
    create_account("cc", "Credit Card", "credit", 0, 100000)

    bot = SigmaTelegramBot(token="test_token", allowed_users=[12345])
    update = make_mock_update(user_id=12345, text="status")
    context = MagicMock()

    asyncio.run(bot.handle_message(update, context))

    update.message.reply_text.assert_called_once()
    args, kwargs = update.message.reply_text.call_args
    assert "Account Status" in args[0]
    assert "Credit Card" in args[0]
    assert kwargs.get("parse_mode") == "HTML"


def test_telegram_exp_command() -> None:
    from sgm.infrastructure.database import create_account
    create_account("wallet", "Cash Wallet", "debit", 10000)

    bot = SigmaTelegramBot(token="test_token", allowed_users=[12345])
    update = make_mock_update(user_id=12345, text='exp 3000 "lunch time" yes wallet')
    context = MagicMock()

    asyncio.run(bot.handle_message(update, context))

    update.message.reply_text.assert_called_once()
    args, kwargs = update.message.reply_text.call_args
    assert "Recorded Expense" in args[0]
    assert "lunch time" in args[0]
    assert "3000" in args[0]

    # Assert DB update
    accounts = get_accounts()
    assert accounts[0]["balance"] == 7000
    assert get_marked_total() == -3000


def test_telegram_tr_command() -> None:
    from sgm.infrastructure.database import create_account
    create_account("bank", "Bank", "debit", 20000)
    create_account("wallet", "Wallet", "debit", 5000)

    bot = SigmaTelegramBot(token="test_token", allowed_users=[12345])
    update = make_mock_update(user_id=12345, text="/tr bank wallet 5000")
    context = MagicMock()

    asyncio.run(bot.handle_message(update, context))

    update.message.reply_text.assert_called_once()
    args, kwargs = update.message.reply_text.call_args
    assert "Recorded Transfer" in args[0]

    accounts = {acc["id"]: acc["balance"] for acc in get_accounts()}
    assert accounts["bank"] == 15000
    assert accounts["wallet"] == 10000
