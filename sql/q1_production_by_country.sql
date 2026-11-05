-- ============================================================================
-- Запрос 1. Таблица 1 "Производство по странам, тонн"
-- Колонки: страна (NAME_EN в REF_COUNTRY), данные за 2020-2024 гг.
-- Последняя строка результата ("ВСЕ СТРАНЫ") - общий итог по всем странам;
-- остальная пост-обработка (заголовок, удаление нулевых строк, сортировка
-- по убыванию за 2024 г.) добавляется python-программой.
-- Примечание по диалекту: в Derby ROLLUP не поддерживает выражения/псевдонимы
-- в списке GROUP BY и функция GROUPING() отсутствует, поэтому для итоговой
-- строки использовано отдельное агрегатное предложение UNION ALL.
-- Диалект: Apache Derby.
-- ============================================================================
select cnt.NAME_EN                                     as COUNTRY_NAME,
       sum(t.VALUE_Y2020)                              as Y2020,
       sum(t.VALUE_Y2021)                              as Y2021,
       sum(t.VALUE_Y2022)                              as Y2022,
       sum(t.VALUE_Y2023)                              as Y2023,
       sum(t.VALUE_Y2024)                              as Y2024
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COUNTRY cnt on cnt.UN_CODE = t.COUNTRY
group by cnt.NAME_EN
union all
select 'ВСЕ СТРАНЫ',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
order by 1
