# Разработка системы визуализации медицинской статистики
Даты проекта: 02.04.2026-18.05.2026

## Заказчик
 ОГБУЗ «Иркутская областная клиническая туберкулезная больница»
 
## Цель проекта 
Создание системы поддержки принятия обоснованных управленческих решений для повышения эффективности противотуберкулезной помощи населению Иркутской области.

## Задачи проекта
1. Сбор, консолидация и приведение к единому формату данных из нескольких источников.
2. Обработка и анализ эпидемиологических показателей, расчёт производных метрик (на 100 тыс. населения, динамика, структура).
3. Разработка интерактивных дашбордов в DataLens для визуализации результатов.
4. Подготовка итогового отчёта и передача результатов заказчику.

## Техническое задание
[pdf](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/TZ_tuberculosis.pdf)

## Навыки и инструменты
+ **Python**
+ **Pandas**
+ **Json**
+ **Numpy**
+ **Jupyter Notebook**

 ## Этапы проекта
 
 ### Этап 1. Обработка и подготовка данных (Python)

 1.1. Извлечение данных из исходных файлов
 
 1.2. Приведение таблиц из широкого формата в длинный
 
 1.3. Сведение таблиц по годам в единую таблицу. 
 
Эти этапы предполагали командную работу, каждый член команды команды обрабатывал одну таблицу отчетной формы № 33 за 3 года. Я занималась предобработкой таблицы 2100 формы  №33 за 2019-2021 годы.

**Исходные данные:**  [zip](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/2100_2019-2021_%D1%88%D0%B8%D1%80%D0%BE%D0%BA%D0%B8%D0%B9.zip)

**Результат:** [zip](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/2100_2019-2021_%D0%B4%D0%BB%D0%B8%D0%BD%D0%BD%D1%8B%D0%B9.zip) средствами Python получена сводная таблица 2100 за 2019-2021 годы в "длинном" формате.

[Jupyter Notebooks](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/transform_table_2100.ipynb) [HTML](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/transform_table_2100.html)

 1.4. Обогащение данных из дополнительных источников 
 
 Дополнтельные источники: 
 - [официальный сайта Иркутскстата](https://38.rosstat.gov.ru/) - для формирования файла со средлнегодовым населением.
 - Официальные сборники Департамента мониторинга, анализа, и стратегического развития здравоохранения МЗ РФ и ФГБУ «ЦНИИОИЗ» МЗ РФ "Социально–значимые заболевания населения России в 20__ году: статистические материалы" - для формирования таблиц с данными по Российской Федерации.
 
 1.5. Очистка и стандартизация
  
Эти этапы также предполагали командную работу.

**Результат:** 

- [объединенный пул таблиц за 2019-2021 годы](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/result_2019-2021.zip)
  
- файл со среднегодовым населением Иркутской области в разрезе года, пола и возраста [population.csv](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/population.csv)
  
- [файлы с данными по туберкулезу по РФ](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/soc_table.zip)
  
### Этап 2. Анализ (Python)
**2.1. Формирование универсального файла-справочника с формулами**

[Формулы от заказчика](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/formulas.pdf)

**Цель этапа:** **создать универсальный файл с формулами**, структуру которого можно использовать для расчета относительных показателей по различным формам медицинской статистики, не только по туберкулезу.

**Результат:**  средствами Python создан файл **indicators.jsonl** для расчета относительных показателей по туберкулезу.

[Jupyter Notebooks](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/make_formula_file.ipynb) [HTML](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/make_formula_file.html)

[indicators.jsonl](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/indicators.jsonl)

**Главное преимущество** такой структуры файла — её масштабируемость, в дальнейшем можно использовать эту структуру для расчета других аналогичных показателей по другим статистическим медицинским формам.

**2.1. Расчёт производных показателей**

**Цель:** Используя универсальный jsonl-файл **indicators.jsonl** с формулами, расчитать и сформировать таблицу с относительными показателями по туберкулезу за 2016-2024 годы.

**Результат:**  средствами Python создан скрипт для расчета показателей.

[Jupyter Notebooks](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/calc_indicators.ipynb) [HTML](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/calc_indicators.html)


[Архив со сводной таблицей с абсолютными значениями 2016-2024 для работы скрипта](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/calc_indicators.zip)

[Итоговый файл с показателями](https://github.com/nina-moise/other_projects/blob/main/tuberculosis/result_2016-2024_%D0%B4%D0%BB%D0%B8%D0%BD%D0%BD%D1%8B%D0%B9.csv)

## Этап 3. Разработка дашбордов
3.1. Проектирование визуализаций (в соответствии с требованиями заказчика)

**Результат:** с помощью BI-система для визуализации и анализа данных Yandex DataLens разработан дашборд ["Сведения о заболеваемости туберкулезом по Российской Федерации и Иркутской области"](https://datalens.yandex/7ik3h5uj969ir)

