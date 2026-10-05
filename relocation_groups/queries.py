"""Генерация поисковых запросов: ключевые слова × страны."""
from __future__ import annotations

# Корень -> варианты написания, по которым ищем страну в тексте группы
COUNTRIES: dict[str, list[str]] = {
    "Грузия": ["грузия", "грузии", "тбилиси", "батуми", "georgia"],
    "Армения": ["армения", "армении", "ереван", "armenia"],
    "Германия": ["германия", "германии", "берлин", "germany"],
    "Турция": ["турция", "турции", "стамбул", "анталья", "turkey"],
    "Сербия": ["сербия", "сербии", "белград", "serbia"],
    "Португалия": ["португалия", "португалии", "лиссабон", "portugal"],
    "Испания": ["испания", "испании", "барселона", "мадрид", "spain"],
    "Польша": ["польша", "польше", "варшава", "poland"],
    "Черногория": ["черногория", "черногории", "montenegro"],
    "Казахстан": ["казахстан", "алматы", "астана", "kazakhstan"],
    "Узбекистан": ["узбекистан", "ташкент", "uzbekistan"],
    "Кипр": ["кипр", "кипре", "лимассол", "cyprus"],
    "ОАЭ": ["оаэ", "дубай", "эмираты", "uae", "dubai"],
    "Таиланд": ["таиланд", "тайланд", "пхукет", "бангкок", "thailand"],
    "США": ["сша", "америка", "usa"],
    "Канада": ["канада", "канаде", "canada"],
}

# Слова, подтверждающие тему переезда (для оценки релевантности)
RELOCATION_WORDS = [
    "переезд", "релокац", "эмиграц", "иммиграц", "relocat", "expat",
    "migration", "вид на жительство", "внж", "пмж", "виза", "визы",
    "русские в", "наши в", "соотечественник",
]

KEYWORD_TEMPLATES = [
    "переезд в {c}",
    "релокация {c}",
    "эмиграция {c}",
    "русские в {c}",
]

GENERIC_QUERIES = ["релокация", "переезд за границу", "эмиграция чат", "relocation"]


def build_queries(countries: list[str] | None = None, generic: bool = True) -> list[str]:
    names = countries or list(COUNTRIES)
    queries = list(GENERIC_QUERIES) if generic else []
    for c in names:
        queries.extend(t.format(c=c) for t in KEYWORD_TEMPLATES)
    return list(dict.fromkeys(queries))


def detect_country(text: str) -> str | None:
    low = text.lower()
    best, best_hits = None, 0
    for name, aliases in COUNTRIES.items():
        hits = sum(low.count(a) for a in aliases)
        if hits > best_hits:
            best, best_hits = name, hits
    return best
