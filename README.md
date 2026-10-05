# relocation_groups

Инструмент поиска групп и чатов о переездах (релокации) в **Telegram** и **VK**.
Использует только официальные API, собирает данные о самих группах (не об участниках).

## Установка
```bash
pip install -r requirements.txt
cp .env.example .env   # заполнить ключи
export $(grep -v '^#' .env | xargs)
```
- Telegram: `TG_API_ID` / `TG_API_HASH` с https://my.telegram.org. При первом запуске Telethon попросит номер телефона и код.
- VK: `VK_TOKEN` — сервисный ключ приложения (https://dev.vk.com).

## Использование
```bash
# поиск по всем странам и обеим платформам
python -m relocation_groups search

# только Грузия и Армения, только Telegram
python -m relocation_groups search --platform telegram --country Грузия Армения

# свой запрос, VK с проверкой активности
python -m relocation_groups search --platform vk --query "переезд в Испанию" --check-activity

python -m relocation_groups show --only-country Грузия   # лучшие из БД
python -m relocation_groups export --out groups.csv      # выгрузка в CSV
```

## Режим без API (`--no-api`)
Только Telegram, ключи Telegram/VK не нужны:
```bash
python -m relocation_groups search --no-api --country Грузия
```
Запросы идут в поисковик (`site:t.me ...`), затем читаются открытые страницы `t.me/<имя>` (название, описание, число участников) и превью `t.me/s/<имя>` (дата последнего поста, только у каналов и открытых групп). Ограничения: выдача поисковика короче и менее полная, он может блокировать автоматические запросы (тогда запрос пропускается с сообщением), у закрытых чатов нет даты активности. Паузы между запросами — 2 с, поэтому запуск по всем странам идёт долго; для начала указывайте одну-две страны.

## Telegram-бот
Бот показывает группы из `groups.db` с фильтром по стране (кнопки, пагинация по 8 штук).
```bash
# 1. создать бота у @BotFather, положить токен в BOT_TOKEN
# 2. наполнить базу командой search
export BOT_TOKEN=...
python -m relocation_groups bot
```
Команды: `/start` (список стран с числом групп), `/top` (лучшие по всем странам). Бот читает базу при каждом запросе, поэтому новые результаты `search` появляются без перезапуска.

## Как это работает
1. `queries.py` — запросы «ключевое слово × страна».
2. `sources/` — коллекторы Telegram (Telethon) и VK (`groups.search`).
3. `filters.py` — дедупликация, определение страны, отсев мёртвых/маленьких/нерелевантных групп, ранжирование
   (релевантность текста + размер + свежесть + число запросов, нашедших группу).
4. `storage.py` — SQLite (`groups.db`), повторные запуски обновляют данные и показывают число новых групп.

## Тесты
```bash
python -m pytest
```

Добавить страну: `COUNTRIES` в `queries.py`. Добавить платформу: новый класс в `sources/` с методом `search(query, limit) -> list[Group]`.
