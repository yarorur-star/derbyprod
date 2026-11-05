-- ============================================================================
-- Запрос 2. Таблица 2 "Продукция по способам обработки и видам продукции, тонн"
-- Колонки: группа FAO major group (NAME_EN в REF_COMMODITY_MAJOR2),
--          номер группы (CODE в REF_COMMODITY_MAJOR2),
--          вид продукции (NAME_EN в REF_COMMODITY), данные за 2020-2024 гг.
-- Строки с 'ИТОГ' вместо названия вида - итоги по каждой группе;
-- строка ('ВСЕ ГРУППЫ','','ИТОГ') - общий итог; метки и оформление - python.
-- Примечание: все товары, присутствующие в таблице данных, имеют группу
-- в REL_COMMODITY_MAJOR, поэтому внутренние соединения ничего не теряют.
-- Примечание по диалекту: Derby не поддерживает GROUPING() и выражения в
-- GROUP BY ROLLUP, поэтому итоги набраны отдельными предложениями UNION ALL.
-- Диалект: Apache Derby.
-- ============================================================================
select mg.NAME_EN                                      as GROUP_NAME,
       mg.CODE                                         as GROUP_CODE,
       cm.NAME_EN                                      as COMMODITY_NAME,
       sum(t.VALUE_Y2020)                              as Y2020,
       sum(t.VALUE_Y2021)                              as Y2021,
       sum(t.VALUE_Y2022)                              as Y2022,
       sum(t.VALUE_Y2023)                              as Y2023,
       sum(t.VALUE_Y2024)                              as Y2024
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
join FISHSTAT.REF_COMMODITY_MAJOR2 mg on mg.ID = r.PARENT_ID
group by mg.NAME_EN, mg.CODE, cm.NAME_EN
union all
select mg.NAME_EN, mg.CODE, 'ИТОГ',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
join FISHSTAT.REF_COMMODITY_MAJOR2 mg on mg.ID = r.PARENT_ID
group by mg.NAME_EN, mg.CODE
union all
select 'ВСЕ ГРУППЫ', '', 'ИТОГ',
       sum(t.VALUE_Y2020),
       sum(t.VALUE_Y2021),
       sum(t.VALUE_Y2022),
       sum(t.VALUE_Y2023),
       sum(t.VALUE_Y2024)
from FISHSTAT.TSD_TRADE_PP_QUANTITY t
join FISHSTAT.REF_COMMODITY cm on cm.FAO_CODE = t.COMMODITY
join FISHSTAT.REL_COMMODITY_MAJOR r on r.CHILD_ID = cm.ID
order by 1, 2, 3
