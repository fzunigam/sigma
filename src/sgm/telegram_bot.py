import logging
import shlex
from typing import List

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

from sgm.infrastructure.database import (
    create_movement,
    create_transfer,
    execute_render,
    get_accounts,
    get_marked_total,
    get_recent_logs,
    get_render_history,
    create_account,
)
from sgm.cli import _resolve_account_and_date

logger = logging.getLogger(__name__)


class SigmaTelegramBot:
    def __init__(self, token: str, allowed_users: List[int]):
        self.token = token
        self.allowed_users = allowed_users

    def is_authorized(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id in self.allowed_users

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return

        if not self.is_authorized(update):
            user = update.effective_user
            logger.warning(
                f"Unauthorized message from user {user.id if user else 'unknown'}: {update.message.text}"
            )
            return

        text = update.message.text.strip()
        try:
            # Strip leading slash if it is a slash command
            if text.startswith("/"):
                text = text[1:]
            args = shlex.split(text)
        except ValueError as e:
            await update.message.reply_text(f"❌ Error parsing command: {e}")
            return

        if not args:
            return

        command = args[0].lower()
        cmd_args = args[1:]

        try:
            await self.dispatch_command(command, cmd_args, update)
        except Exception as e:
            logger.exception("Error executing command via Telegram")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def dispatch_command(self, command: str, args: List[str], update: Update) -> None:
        if command in ("help", "start"):
            await self.cmd_help(update)
        elif command == "status":
            await self.cmd_status(update)
        elif command == "exp":
            await self.cmd_exp(args, update)
        elif command == "inc":
            await self.cmd_inc(args, update)
        elif command == "tr":
            await self.cmd_tr(args, update)
        elif command == "log":
            await self.cmd_log(args, update)
        elif command == "render":
            await self.cmd_render(update)
        elif command == "history":
            await self.cmd_history(update)
        elif command == "acc":
            await self.cmd_acc(args, update)
        else:
            await update.message.reply_text(
                f"❓ Unknown command: <code>{command}</code>.\n"
                f"Type <code>help</code> or <code>/help</code> to see available commands.",
                parse_mode="HTML"
            )

    async def cmd_help(self, update: Update) -> None:
        help_text = (
            "🤖 <b>Sigma Telegram Bot Help</b>\n\n"
            "You can use the exact same commands here:\n\n"
            "💸 <b>Logging Transactions</b>\n"
            "• <code>exp &lt;amount&gt; &lt;desc&gt; &lt;mark: yes|no&gt; [acc_id] [date]</code>\n"
            "  <i>e.g. exp 5000 lunch yes</i>\n"
            "• <code>inc &lt;amount&gt; &lt;desc&gt; &lt;mark: yes|no&gt; [acc_id] [date]</code>\n"
            "  <i>e.g. inc 20000 paycheck yes</i>\n"
            "• <code>tr &lt;from_acc&gt; &lt;to_acc&gt; &lt;amount&gt; [date]</code>\n"
            "  <i>e.g. tr bank wallet 10000</i>\n\n"
            "📊 <b>Status &amp; Logs</b>\n"
            "• <code>status</code> - Show account balances and marked total\n"
            "• <code>log [limit]</code> - List recent transactions\n"
            "• <code>history</code> - Show render history\n\n"
            "🔄 <b>Rendering</b>\n"
            "• <code>render</code> - Sum all marked items and create a snapshot\n\n"
            "💳 <b>Accounts</b>\n"
            "• <code>acc list</code> - List all accounts\n"
            "• <code>acc add &lt;id&gt; &lt;name&gt; &lt;type: debit|credit&gt; &lt;bal&gt; [limit]</code>\n"
            "  <i>e.g. acc add cc \"Visa\" credit 0</i>"
        )
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def cmd_exp(self, args: List[str], update: Update) -> None:
        if len(args) < 3:
            await update.message.reply_text(
                "❌ Usage: <code>exp &lt;amount&gt; &lt;desc&gt; &lt;mark: yes|no&gt; [acc_id] [date]</code>",
                parse_mode="HTML"
            )
            return

        try:
            amount = int(args[0])
            desc = args[1]
            mark_str = args[2].lower()
            acc_id = args[3] if len(args) > 3 else None
            date = args[4] if len(args) > 4 else None
        except ValueError:
            await update.message.reply_text("❌ Error: Amount must be an integer.")
            return

        if amount <= 0:
            await update.message.reply_text("❌ Error: Amount must be positive.")
            return

        if mark_str not in ("yes", "no"):
            await update.message.reply_text("❌ Error: Mark must be 'yes' or 'no'.")
            return

        marked = mark_str == "yes"

        try:
            resolved_acc_id, resolved_date = _resolve_account_and_date(acc_id, date, tx_type="expense")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return

        try:
            create_movement(amount, desc, resolved_acc_id, "expense", marked, created_at=resolved_date)
            date_str = f" on <code>{resolved_date}</code>" if resolved_date else ""
            await update.message.reply_text(
                f"💸 <b>Recorded Expense</b>\n"
                f"• Amount: <code>{amount}</code> CLP\n"
                f"• Description: <i>{desc}</i>\n"
                f"• Account: <code>{resolved_acc_id}</code>\n"
                f"• Marked: {'Yes' if marked else 'No'}"
                f"{date_str}",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_inc(self, args: List[str], update: Update) -> None:
        if len(args) < 3:
            await update.message.reply_text(
                "❌ Usage: <code>inc &lt;amount&gt; &lt;desc&gt; &lt;mark: yes|no&gt; [acc_id] [date]</code>",
                parse_mode="HTML"
            )
            return

        try:
            amount = int(args[0])
            desc = args[1]
            mark_str = args[2].lower()
            acc_id = args[3] if len(args) > 3 else None
            date = args[4] if len(args) > 4 else None
        except ValueError:
            await update.message.reply_text("❌ Error: Amount must be an integer.")
            return

        if amount <= 0:
            await update.message.reply_text("❌ Error: Amount must be positive.")
            return

        if mark_str not in ("yes", "no"):
            await update.message.reply_text("❌ Error: Mark must be 'yes' or 'no'.")
            return

        marked = mark_str == "yes"

        try:
            resolved_acc_id, resolved_date = _resolve_account_and_date(acc_id, date, tx_type="income")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            return

        try:
            create_movement(amount, desc, resolved_acc_id, "income", marked, created_at=resolved_date)
            date_str = f" on <code>{resolved_date}</code>" if resolved_date else ""
            await update.message.reply_text(
                f"💰 <b>Recorded Income</b>\n"
                f"• Amount: <code>{amount}</code> CLP\n"
                f"• Description: <i>{desc}</i>\n"
                f"• Account: <code>{resolved_acc_id}</code>\n"
                f"• Marked: {'Yes' if marked else 'No'}"
                f"{date_str}",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_tr(self, args: List[str], update: Update) -> None:
        if len(args) < 3:
            await update.message.reply_text(
                "❌ Usage: <code>tr &lt;from&gt; &lt;to&gt; &lt;amount&gt; [date]</code>",
                parse_mode="HTML"
            )
            return

        try:
            from_acc = args[0]
            to_acc = args[1]
            amount = int(args[2])
            date = args[3] if len(args) > 3 else None
        except ValueError:
            await update.message.reply_text("❌ Error: Amount must be an integer.")
            return

        if amount <= 0:
            await update.message.reply_text("❌ Error: Amount must be positive.")
            return

        if from_acc == to_acc:
            await update.message.reply_text("❌ Error: Source and destination accounts must be different.")
            return

        try:
            create_transfer(from_acc, to_acc, amount, created_at=date)
            date_str = f" on <code>{date}</code>" if date else ""
            await update.message.reply_text(
                f"🔄 <b>Recorded Transfer</b>\n"
                f"• Amount: <code>{amount}</code> CLP\n"
                f"• From: <code>{from_acc}</code>\n"
                f"• To: <code>{to_acc}</code>"
                f"{date_str}",
                parse_mode="HTML"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_status(self, update: Update) -> None:
        accounts = get_accounts()
        marked_total = get_marked_total()

        if not accounts:
            await update.message.reply_text(
                "⚠️ No accounts found. Use <code>acc add</code> to create one.",
                parse_mode="HTML"
            )
            return

        lines = ["📊 <b>Account Status</b>\n"]
        for acc in accounts:
            avail_credit_str = ""
            if acc["type"] == "credit":
                avail = acc["credit_limit"] - acc["balance"]
                avail_credit_str = f" | Avail Credit: <code>{avail}</code>"
            lines.append(
                f"• <b>{acc['name']}</b> (<code>{acc['id']}</code>):\n"
                f"  Balance: <code>{acc['balance']}</code> CLP{avail_credit_str}"
            )

        lines.append(f"\nMarked total for next render: <b>{marked_total}</b> CLP")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_log(self, args: List[str], update: Update) -> None:
        limit = 15
        if args:
            try:
                limit = int(args[0])
            except ValueError:
                await update.message.reply_text("❌ Error: Limit must be an integer.")
                return

        records = get_recent_logs(limit)
        if not records:
            await update.message.reply_text("ℹ️ No recent movements found.")
            return

        lines = [f"📋 <b>Recent Logs (last {min(limit, len(records))})</b>\n"]
        for rec in records:
            type_str = rec["type"]
            emoji = "💰" if type_str == "income" else "💸" if type_str == "expense" else "🔄"

            date_part = rec["created_at"]
            desc_part = rec["description"]
            amt = rec["amount"]
            acc = rec["account_id"]

            if type_str == "transfer":
                lines.append(f"{emoji} <code>{date_part}</code> | <b>{amt}</b> CLP\n  <i>{desc_part}</i>")
            else:
                lines.append(f"{emoji} <code>{date_part}</code> | <code>{acc}</code> | <b>{amt}</b> CLP\n  <i>{desc_part}</i>")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_render(self, update: Update) -> None:
        net_amount, count = execute_render()
        if count == 0:
            await update.message.reply_text("ℹ️ No marked movements to render.")
        else:
            await update.message.reply_text(
                f"✅ <b>Render Completed</b>\n"
                f"• Rendered <b>{count}</b> movements\n"
                f"• Net amount logged: <b>{net_amount}</b> CLP",
                parse_mode="HTML"
            )

    async def cmd_history(self, update: Update) -> None:
        history = get_render_history()
        if not history:
            await update.message.reply_text("ℹ️ No render history found.")
            return

        lines = ["📜 <b>Render History</b>\n"]
        for item in history:
            lines.append(
                f"• ID: <code>{item['id']}</code> | <code>{item['rendered_at']}</code> | Net: <b>{item['net_amount']}</b> CLP"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_acc(self, args: List[str], update: Update) -> None:
        if not args:
            await update.message.reply_text(
                "❌ Usage:\n"
                "• <code>acc list</code> - List all accounts\n"
                "• <code>acc add &lt;id&gt; &lt;name&gt; &lt;type: debit|credit&gt; &lt;bal&gt; [limit]</code>",
                parse_mode="HTML"
            )
            return

        subcommand = args[0].lower()
        subargs = args[1:]

        if subcommand == "list":
            accounts = get_accounts()
            if not accounts:
                await update.message.reply_text("⚠️ No accounts found.")
                return

            lines = ["💳 <b>Accounts</b>\n"]
            for acc in accounts:
                limit_str = (
                    f" | Limit: <code>{acc['credit_limit']}</code>"
                    if acc["type"] == "credit"
                    else ""
                )
                lines.append(
                    f"• <b>{acc['name']}</b> (<code>{acc['id']}</code>) | {acc['type'].capitalize()} | Balance: <b>{acc['balance']}</b> CLP{limit_str}"
                )
            await update.message.reply_text("\n".join(lines), parse_mode="HTML")

        elif subcommand == "add":
            if len(subargs) < 4:
                await update.message.reply_text(
                    "❌ Usage: <code>acc add &lt;id&gt; &lt;name&gt; &lt;type: debit|credit&gt; &lt;bal&gt; [limit]</code>",
                    parse_mode="HTML"
                )
                return

            try:
                acc_id = subargs[0]
                name = subargs[1]
                acc_type = subargs[2].lower()
                balance = int(subargs[3])
                limit = int(subargs[4]) if len(subargs) > 4 else 0
            except ValueError:
                await update.message.reply_text("❌ Error: Balance and Limit must be integers.")
                return

            if acc_type not in ("debit", "credit"):
                await update.message.reply_text("❌ Error: Account type must be 'debit' or 'credit'.")
                return

            try:
                create_account(acc_id, name, acc_type, balance, limit)
                await update.message.reply_text(
                    f"✅ Account <b>{name}</b> (<code>{acc_id}</code>) created successfully!",
                    parse_mode="HTML"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error creating account: {e}")
        else:
            await update.message.reply_text(f"❓ Unknown account subcommand: <code>{subcommand}</code>", parse_mode="HTML")


def run_telegram_bot(token: str, allowed_users: List[int]) -> None:
    bot = SigmaTelegramBot(token, allowed_users)
    application = Application.builder().token(token).build()

    # Route all text messages to the bot's handle_message handler
    application.add_handler(MessageHandler(filters.TEXT, bot.handle_message))

    application.run_polling()
