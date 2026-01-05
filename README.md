# Zashapon Testnet Automation

Автоматизация фарма билетов на портале [Zashapon](https://www.zashapon.com/) с использованием AdsPower и Patchright.

## Возможности

- 🎮 Автоматическая игра и сбор карточек
- 🌐 Интеграция с AdsPower (антидетект браузер)
- 📊 Запись результатов в Google Sheets
- 🧵 Многопоточная обработка профилей
- ⏹️ Graceful shutdown (Ctrl+C)

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

### 1. Google Sheets

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите **Google Sheets API** и **Google Drive API**
3. Создайте Service Account → скачайте JSON-ключ
4. Сохраните как `service_account.json` в папку проекта
5. Расшарьте таблицу на email сервисного аккаунта (права Editor)

### 2. config.yaml

```yaml
adspower:
  base_url: "http://localhost:50325"

google_sheets:
  credentials_file: "service_account.json"
  spreadsheet_id: "YOUR_SPREADSHEET_ID"  # Из URL таблицы
  sheet_name: "Sheet1"

threading:
  max_workers: 3  # Количество параллельных профилей
```

### 3. Структура таблицы

| A | B | C | D | E | F | G | H | I | J | K | L | M | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Profile Number | Address | mail | Daruma Zama | Daruma Monk | Daruma Wave | Daruma Devil | Daruma Fox | Daruma Lantern | Daruma Cat | Daruma Kumo | Daruma Sakura | All_ready | Status |

- **Колонка A**: serial_number профилей AdsPower
- **Колонки D-L**: карточки (записывается "ok" если есть)
- **Колонка N**: статус выполнения

## Запуск

```bash
python main.py
```

Для остановки нажмите **Ctrl+C** — программа корректно завершит работу.

## Логика работы

1. Читает serial_number профилей из Google Sheets
2. Для каждого профиля параллельно:
   - Запускает AdsPower профиль
   - Переходит на zashapon.com
   - Играет пока есть билеты (Play → Add to Collection)
   - Парсит коллекцию карточек
   - Записывает результаты в таблицу
