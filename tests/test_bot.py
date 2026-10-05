from datetime import datetime, timezone

from relocation_groups.bot import PAGE, COUNTRY_LIST, countries_view, groups_view
from relocation_groups.filters import apply_filters
from relocation_groups.models import Group
from relocation_groups.storage import Storage


def make_db(tmp_path, n=12):
    st = Storage(str(tmp_path / "b.db"))
    gs = [Group("telegram", str(i), f"Релокация Грузия <{i}>", f"https://t.me/g{i}",
                "переезд, виза, Тбилиси", 100 + i, datetime.now(timezone.utc))
          for i in range(n)]
    gs.append(Group("vk", "x", "Переезд в Германию", "https://vk.com/x",
                    "эмиграция Берлин", 500, datetime.now(timezone.utc)))
    st.save(apply_filters(gs))
    return st


def test_countries_view(tmp_path):
    text, kb = countries_view(make_db(tmp_path))
    labels = [b["text"] for row in kb["inline_keyboard"] for b in row]
    assert "Грузия (12)" in labels and "Германия (1)" in labels
    assert not any(l.startswith("Армения") for l in labels)
    assert all(len(b["callback_data"].encode()) <= 64
               for row in kb["inline_keyboard"] for b in row)


def test_groups_view_filter_and_paging(tmp_path):
    st = make_db(tmp_path)
    i = COUNTRY_LIST.index("Грузия")
    text, kb = groups_view(st, str(i), 0)
    assert "из 12" in text and "Германию" not in text
    assert "&lt;" in text  # экранирование HTML в названиях
    nav = [b["callback_data"] for b in kb["inline_keyboard"][0]]
    assert nav == [f"c:{i}:{PAGE}"]
    _, kb2 = groups_view(st, str(i), PAGE)
    assert [b["text"] for b in kb2["inline_keyboard"][0]] == ["⬅️ Назад"]


def test_empty_and_all(tmp_path):
    st = make_db(tmp_path)
    assert "групп пока нет" in groups_view(st, str(COUNTRY_LIST.index("Армения")), 0)[0]
    assert "из 13" in groups_view(st, "all", 0)[0]
