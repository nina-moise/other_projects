# Разработка дашборда аналитики League of Legends
Проект реализован в рамках **Яндекс Мастерской**. Даты проекта: 29.05.2026-26.06.2026

## Заказчик
Игровой блогер-стример и тренер, обучающий игроков. 
 
## Цель проекта 
Разработать интерактивный дашборд, отображающий статистику матчей, игроков и чемпионов League of Legends за текущий месяц для регионов Европа и США. Дашборд должен быть реализован на Python с использованием официального API Riot Games.

## Задачи проекта
1. Extract. Извлечение данных с использованием официального APIRiot Games. 
2. Transform обработка извлеченных данных
3. Load Разработка интерактивных дашбордов в DataLens для визуализации результатов.
4. Dashboard Подготовка итогового отчёта и передача результатов заказчику.

## Техническое задание
[pdf]()

## Использованные технологии и навыки
* **Data Sourcing**: Интеграция с официальным **Riot Games API** (отправка запросов, обработка JSON, обход лимитов).
* **Backend & DB**: Python (Pandas, Requests, Gc, Logging), Supabase (PostgreSQL), SQLAlchemy.
* **Frontend**: Streamlit, Plotly.
* **Jupyter Notebook**, **DBeaver**

 ## Этапы проекта
 
 ### Этап 1. Extract - Извлечение данных с использованием официального API Riot Games 

 1.1. Регистрация на	портале	разработчиков	[Riot Games](https://www.riotgames.com)
 
 1.2. Получение личного [Development	API	Key](https://developer.riotgames.com/)
 
 1.3. Изучение [документации эндпоинтов](https://developer.riotgames.com/apis)
 
 1.2. Получение и сохранение данных с помощью личного API	Key за **май 2026** по следующей схеме:

- запрос списка активных игроков через эндпоинт `/lol/league/v4/`
- получение истории матчей (`matchIds`) для каждого игрока через `/lol/match/v5/`
- выгрузка детальной статистики каждого матча (тайминги, KDA, золото)

 **Результат:** 
 
- Скрипт для сбора данных [Jupyter Notebooks](https://github.com/nina-moise/other_projects/blob/main/LOL/LOL_extract.ipynb) [HTML](https://github.com/nina-moise/other_projects/blob/main/LOL/LOL_extract.html)

- Пример файла с настройками [lol.env](https://github.com/nina-moise/other_projects/blob/main/LOL/lol.env)

- Данные: архив *.csv и *.log: [7z](https://github.com/nina-moise/other_projects/blob/main/LOL/LOL_data_05_2026.7z)

- Данные за май 2026: собирались в период 14.06.2026-15.06.2026. 

### Этап 2.Transform & Load

