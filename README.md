# 🛡 UnlockAntivirus

Лёгкий антивирус с онлайн-обновлением сигнатур. Один файл Python, только стандартная библиотека.

![Version](https://img.shields.io/badge/version-3.5.0-22d3a5)
![Python](https://img.shields.io/badge/python-3.9+-38bdf8)
![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![Dependencies](https://img.shields.io/badge/dependencies-none-success)

---

## Что это

**UnlockAntivirus** — простой антивирус-сканер, который:

- 🔍 Проверяет файлы по **SHA256 / MD5 / SHA1**
- ⬇ Автоматически обновляет базы сигнатур из **открытых источников**
- 🧱 Изолирует найденные угрозы в **карантин**
- 🖥 Работает в **системном трее** (Windows) с фоновой защитой
- 🚀 Запускается **при входе в систему**
- 📦 **Никаких зависимостей** — только стандартная библиотека Python

Не требует установки, не шлёт телеметрию, работает полностью на твоём компьютере.

---

## Возможности

| Функция | Описание |
|---|---|
| **Сканирование** | Файлы и папки, фильтр по расширениям и размеру |
| **Онлайн-базы** | 5 источников: MalwareBazaar, ThreatFox, URLhaus, Feodo Tracker, SSL Blacklist |
| **Карантин** | Файлы перемещаются с метаданными, можно восстановить |
| **Фоновая защита** | Отдельный поток следит за выбранными папками |
| **Трей** | Иконка в системном трее, меню по ПКМ (Windows) |
| **Автозагрузка** | Реестр (Windows), .desktop (Linux), LaunchAgent (macOS) |
| **Тёмная тема** | Кастомный GUI на Tkinter, адаптирован под HiDPI |
| **CLI-режим** | `--cli --update`, `--cli <path>` для скриптов |
| **Автообновление** | Раз в N часов при запуске |

---

## Источники сигнатур

Антивирус умеет тянуть хэши сразу из нескольких открытых фидов:

| Источник | Что содержит | Формат |
|---|---|---|
| [MalwareBazaar](https://bazaar.abuse.ch/) | Свежие SHA256 образцов малвари | plaintext |
| [ThreatFox](https://threatfox.abuse.ch/) | IOC: хэши, домены, IP | CSV |
| [URLhaus](https://urlhaus.abuse.ch/) | Хэши файлов с вредоносных ссылок | plaintext |
| [Feodo Tracker](https://feodotracker.abuse.ch/) | Хэши C&C ботнетов (Dridex, Emotet) | CSV |
| [SSL Blacklist](https://sslbl.abuse.ch/) | SHA1 сертификатов C&C | CSV |

Можно добавить **свои источники** — любой URL, отдающий JSON, plaintext или CSV с хэшами.

Пример своего сервера:

```json
{
  "sources": [
    "https://bazaar.abuse.ch/export/txt/sha256/recent/",
    "https://твой-домен/api/signatures.json",
    "https://твой-домен/hashes.txt"
  ]
}
