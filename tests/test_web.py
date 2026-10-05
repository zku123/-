from relocation_groups.sources.web import (extract_usernames, parse_channel_page,
                                           parse_last_post)

SERP = """<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ft.me%2Fgeorgia_relocation&rut=1">x</a>
<a href="https://t.me/s/RelocateTbilisi">y</a> <span>t.me/joinchat/AAAA</span>
<a href="https://t.me/georgia_relocation">dup</a> t.me/share/url t.me/abc"""

CHANNEL = """<meta property="og:title" content="Релокация &amp; Грузия">
<meta property="og:description" content="Чат про ВНЖ и аренду в Тбилиси">
<div class="tgme_page_extra">12&nbsp;345 members, 120 online</div>"""

BOT = '<div class="tgme_page_extra">@some_bot</div>'
PREVIEW = '<time datetime="2026-10-01T10:00:00+00:00"></time><time datetime="2026-10-04T12:30:00+00:00"></time>'


def test_extract_usernames():
    assert extract_usernames(SERP) == ["georgia_relocation", "relocatetbilisi"]


def test_parse_channel():
    g = parse_channel_page(CHANNEL, "Georgia_Relocation")
    assert g.members == 12345 and g.title == "Релокация & Грузия"
    assert g.ext_id == "georgia_relocation" and "Тбилиси" in g.description


def test_parse_ru_subscribers():
    g = parse_channel_page('<div class="tgme_page_extra">1 500 подписчиков</div>', "abcde")
    assert g.members == 1500


def test_not_a_group():
    assert parse_channel_page(BOT, "some_bot") is None
    assert parse_channel_page("<html></html>", "nothing") is None


def test_last_post():
    assert parse_last_post(PREVIEW).day == 4
    assert parse_last_post("") is None
