from datetime import datetime, timedelta, timezone

from relocation_groups.filters import apply_filters, merge
from relocation_groups.models import Group
from relocation_groups.queries import build_queries, detect_country
from relocation_groups.storage import Storage


def mk(ext, title, desc="", members=500, days=1, q="a"):
    return Group("telegram", ext, title, f"https://t.me/{ext}", desc, members,
                 datetime.now(timezone.utc) - timedelta(days=days), found_by={q})


def test_build_queries_unique():
    qs = build_queries(["Грузия"])
    assert "релокация Грузия" in qs and len(qs) == len(set(qs))


def test_detect_country():
    assert detect_country("Чат русских в Тбилиси, переезд в Грузию") == "Грузия"
    assert detect_country("просто чат") is None


def test_merge_dedup():
    m = merge([mk("1", "x", q="a"), mk("1", "x", q="b")])
    assert len(m) == 1 and m[0].found_by == {"a", "b"}


def test_filters():
    groups = [
        mk("1", "Релокация в Грузию", "виза, ВНЖ Тбилиси"),
        mk("2", "Мёртвый чат переезд", days=400),
        mk("3", "Маленький переезд чат", members=10),
        mk("4", "Кулинария"),
    ]
    res = apply_filters(groups, min_members=100, max_inactive_days=60)
    assert [g.ext_id for g in res] == ["1"]
    assert res[0].country == "Грузия"


def test_storage(tmp_path):
    st = Storage(str(tmp_path / "t.db"))
    g = apply_filters([mk("1", "Релокация Грузия")])
    assert st.save(g) == 1 and st.save(g) == 0
    assert st.top()[0]["title"] == "Релокация Грузия"
