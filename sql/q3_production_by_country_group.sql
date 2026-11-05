-- ============================================================================
-- Запрос 3. Таблица 3 "Продукция по странам и товарным группам, тонн"
-- Колонки: страна (NAME_EN в REF_COUNTRY), группа FAO major group
--          (NAME_EN в REF_COMMODITY_MAJOR2), номер группы (CODE),
--          данные за 2020-2024 гг.
-- Строка с 'ИТОГ' вместо группы - итог по стране; строка ('ВСЕ СТРАНЫ','ИТОГ',...)
-- - общий итог по всем странам. Метки, достройка недостающих групп нулями и
-- транспонирование - python-программа.
-- Примечание по диалекту: Derby не поддерживает GROUPING() и выражения в
-- GROUP BY ROLLUP, поэтому итоги набраны отдельными предложениями UNION ALL.
-- Диалект: Apache Derby.
-- ============================================================================
select cnt.NAME_EN                                     as COUNTRY_NAME,
       mg.NAME_EN                                      as GROUP_NAME,
       mg.CODE                                         as GROUP_CODE,
       sum(t.VALUE_Y2020)                              as Y2020,
       sum(t.VALUE_Y2021)                              as Y2021,
       sum(t.VALUE_Y2022)                              as Y2022,
       sum(t.VALUE_Y2023)                              as Y2023,
       sum(t.VALUE_Y2024)                              as Y2024
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COUNTRY cnt on cnt.UN_CODE = t.COUNTRY
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
join FISHSTAT.REF_COMMODITY_MAJOR2 mg on mg.ID = r.PARENT_ID
group by cnt.NAME_EN, mg.NAME_EN, mg.CODE
union all
select cnt.NAME_EN, 'ИТОГ', '',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COUNTRY cnt on cnt.UN_CODE = t.COUNTRY
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
group by cnt.NAME_EN
union all
select 'ВСЕ СТРАНЫ', 'ИТОГ', '',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
order by 1, 2, 3
