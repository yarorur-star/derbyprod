-- ============================================================================
-- Запрос 4. Таблица 4 "Продукция по видам, способам обработки и странам,
-- группа FAO major group 1 (Fish, fresh, chilled or frozen), тонн"
-- Колонки: вид продукции (NAME_EN в REF_COMMODITY), страна (NAME_EN в
--          REF_COUNTRY), данные за 2020-2024 гг.
-- Строки с 'ИТОГ' вместо страны - итоги по каждому виду продукции;
-- строка ('ИТОГ','','ИТОГ') - общий итог таблицы. Метки и оформление - python.
-- Примечание по диалекту: Derby не поддерживает GROUPING() и выражения в
-- GROUP BY ROLLUP, поэтому итоги набраны отдельными предложениями UNION ALL.
-- Диалект: Apache Derby.
-- ============================================================================
select cm.NAME_EN                                      as COMMODITY_NAME,
       cnt.NAME_EN                                     as COUNTRY_NAME,
       sum(t.VALUE_Y2020)                              as Y2020,
       sum(t.VALUE_Y2021)                              as Y2021,
       sum(t.VALUE_Y2022)                              as Y2022,
       sum(t.VALUE_Y2023)                              as Y2023,
       sum(t.VALUE_Y2024)                              as Y2024
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
join FISHSTAT.REF_COMMODITY_MAJOR2 mg on mg.ID = r.PARENT_ID
join FISHSTAT.REF_COUNTRY cnt on cnt.UN_CODE = t.COUNTRY
where mg.CODE = '1'
group by cm.NAME_EN, cnt.NAME_EN
union all
select cm.NAME_EN, 'ИТОГ',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
join FISHSTAT.REF_COMMODITY_MAJOR2 mg on mg.ID = r.PARENT_ID
where mg.CODE = '1'
group by cm.NAME_EN
union all
select 'ИТОГ', 'ИТОГ',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
join FISHSTAT.REF_COMMODITY_MAJOR2 mg on mg.ID = r.PARENT_ID
where mg.CODE = '1'
order by 1, 2
