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

## Хостинг и расписание

GitHub раздаёт только статику (Pages, ветка `main`, корень): страница живёт на
**https://atytsky.github.io/fuel/** и читает `data/stations.json` из этого же репозитория.
Данные собираются локально и пушатся:

```sh
./install-schedule.sh          # поставить расписание launchd (по умолчанию 1800 с = 30 мин)
./install-schedule.sh 900      # или свой интервал, в секундах
./update.sh                    # прогон вручную: парсер -> коммит -> push
tail -f logs/update.log        # что делает расписание
```

Снять расписание:

```sh
launchctl bootout gui/$(id -u)/dev.andy.fuel-update
rm ~/Library/LaunchAgents/dev.andy.fuel-update.plist
```

Обновление идёт, пока Mac включён; после сна launchd догоняет пропущенный запуск.
Открытая вкладка сама перечитывает JSON раз в 5 минут и показывает возраст снимка.

## Почему парсер не запустить на GitHub

Проверено: с раннеров GitHub (США) `gpnbonus.ru` недоступен на сетевом уровне —
TCP-соединение на 443 порт не устанавливается вообще (DNS отвечает: 213.221.41.242,
дальше пакеты теряются). Недоступен весь сайт, не только API. Из браузера посетителя
тоже не выйдет: в ответах нет заголовка `Access-Control-Allow-Origin`, и `fetch`
падает с `TypeError: Failed to fetch`.

Поэтому парсер и живёт локально, а GitHub Pages получает готовый JSON.

## Логика статуса (повторяет сайт)
- `rest.avail == true` → В наличии
- `rest.avail == false` и `rest.delivery != "no"` (`yes`/`soon`) → В пути (`soon` — «ещё ~2ч»)
- `rest.avail == false` и `delivery == "no"` → Отсутствует
- топлива нет в ответе карточки → Не продаётся
