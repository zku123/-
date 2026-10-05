"""Telegram-бот: выбор страны -> список лучших групп о переезде из БД.

Работает через Bot API (long polling), без дополнительных зависимостей.
Запуск: BOT_TOKEN=... python -m relocation_groups bot
"""
from __future__ import annotations

import html
import logging
import time

import requests

from .queries import COUNTRIES
from .storage import Storage

log = logging.getLogger(__name__)

PAGE = 8
COUNTRY_LIST = list(COUNTRIES)  # индекс страны идёт в callback_data (лимит 64 байта)


def _row_text(r) -> str:
    members = f"{r['members']:,}".replace(",", " ") if r["members"] is not None else "?"
    icon = "✈️" if r["platform"] == "telegram" else "🔷"
    return (f"{icon} <a href=\"{html.escape(r['url'])}\">{html.escape(r['title'] or r['url'])}</a>"
            f" — {members} уч.")


def countries_view(st: Storage) -> tuple[str, dict]:
    counts = st.country_counts()
    buttons = [
        {"text": f"{c} ({counts[c]})", "callback_data": f"c:{i}:0"}
        for i, c in enumerate(COUNTRY_LIST) if counts.get(c)
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([{"text": f"🌍 Все страны ({sum(counts.values())})",
                  "callback_data": "c:all:0"}])
    return "Выберите страну переезда:", {"inline_keyboard": rows}


def groups_view(st: Storage, key: str, offset: int) -> tuple[str, dict]:
    country = None if key == "all" else COUNTRY_LIST[int(key)]
    rows, total = st.page(country, PAGE, offset)
    title = country or "Все страны"
    if not rows:
        text = f"<b>{html.escape(title)}</b>: групп пока нет."
    else:
        body = "\n".join(f"{offset + i + 1}. {_row_text(r)}" for i, r in enumerate(rows))
        text = (f"<b>{html.escape(title)}</b> — {offset + 1}–{offset + len(rows)} "
                f"из {total}\n\n{body}")
    nav = []
    if offset > 0:
        nav.append({"text": "⬅️ Назад", "callback_data": f"c:{key}:{max(offset - PAGE, 0)}"})
    if offset + PAGE < total:
        nav.append({"text": "Ещё ➡️", "callback_data": f"c:{key}:{offset + PAGE}"})
    kb = [nav] if nav else []
    kb.append([{"text": "🌐 К списку стран", "callback_data": "home"}])
    return text, {"inline_keyboard": kb}


class Bot:
    def __init__(self, token: str, db_path: str = "groups.db"):
        self.api = f"https://api.telegram.org/bot{token}/"
        self.st = Storage(db_path)

    def call(self, method: str, **params) -> dict:
        r = requests.post(self.api + method, json=params, timeout=70).json()
        if not r.get("ok"):
            raise RuntimeError(f"{method}: {r.get('description')}")
        return r["result"]

    def _show(self, chat_id: int, view: tuple[str, dict], message_id: int | None = None):
        text, kb = view
        common = dict(chat_id=chat_id, text=text, parse_mode="HTML",
                      reply_markup=kb, disable_web_page_preview=True)
        if message_id:
            self.call("editMessageText", message_id=message_id, **common)
        else:
            self.call("sendMessage", **common)

    def handle(self, update: dict) -> None:
        if msg := update.get("message"):
            cmd = (msg.get("text") or "").split()[:1]
            if cmd and cmd[0].split("@")[0] in ("/start", "/countries", "/help"):
                self._show(msg["chat"]["id"], countries_view(self.st))
            elif cmd and cmd[0].split("@")[0] == "/top":
                self._show(msg["chat"]["id"], groups_view(self.st, "all", 0))
        elif cb := update.get("callback_query"):
            self.call("answerCallbackQuery", callback_query_id=cb["id"])
            m, data = cb["message"], cb["data"]
            if data == "home":
                view = countries_view(self.st)
            elif data.startswith("c:"):
                _, key, off = data.split(":")
                view = groups_view(self.st, key, int(off))
            else:
                return
            try:
                self._show(m["chat"]["id"], view, m["message_id"])
            except RuntimeError as e:  # "message is not modified" и т.п.
                log.info("%s", e)

    def run(self) -> None:
        offset = 0
        print("Бот запущен. Ctrl+C для остановки.")
        while True:
            try:
                updates = self.call("getUpdates", offset=offset, timeout=50,
                                    allowed_updates=["message", "callback_query"])
            except Exception as e:
                log.warning("getUpdates: %s", e)
                time.sleep(5)
                continue
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    self.handle(u)
                except Exception:
                    log.exception("ошибка обработки апдейта")
