# G-95 на АЗС Газпромнефть (Свердловская область)

Парсер `parser.py` ходит в открытый API карты https://gpnbonus.ru/fuel/refuel-map
(`POST /api/stations/list` → список АЗС региона, `POST /api/stations/{GPNAZSID}` → цены и остатки)
и складывает результат в `data/stations.json`. Страница `index.html` (SPA без сборки) читает этот JSON
и показывает по каждой АЗС статус G-95: **Отсутствует**, **🚚 В пути**, В наличии, Не продаётся.

## Запуск

```sh
./serve.sh                 # спарсить (≈1.5 мин, 145 АЗС, пауза 0.5 с) и открыть http://localhost:8765
python3 parser.py          # только обновить данные
python3 parser.py --city Екатеринбург --delay 1   # только город, медленнее
python3 -m http.server 8765                       # только показать страницу
```

Нужен только Python 3, зависимостей нет. Открывать `index.html` нужно через http-сервер (fetch JSON не работает с file://).

## GitHub Pages + Actions

Расписание живёт в `.github/workflows/update.yml`: каждый час (cron `7 * * * *`, UTC) Actions
запускает `parser.py`, свежий `data/stations.json` попадает прямо в артефакт GitHub Pages —
в репозиторий он не коммитится, история остаётся чистой. Запустить вручную можно кнопкой
«Run workflow» во вкладке Actions.

Включить один раз: **Settings → Pages → Source: GitHub Actions**.

Интервал: cron GitHub может опаздывать на 5–15 минут. Для публичного репозитория минуты Actions
бесплатны и не ограничены; для приватного — 2000 мин/мес (один прогон ≈ 2 мин, т.е. раз в час
укладывается с запасом).

## Логика статуса (повторяет сайт)
- `rest.avail == true` → В наличии
- `rest.avail == false` и `rest.delivery != "no"` (`yes`/`soon`) → В пути (`soon` — «ещё ~2ч»)
- `rest.avail == false` и `delivery == "no"` → Отсутствует
- топлива нет в ответе карточки → Не продаётся
