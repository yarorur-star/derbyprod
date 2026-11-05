# -*- coding: utf-8 -*-
"""
Программа формирования финального Excel-файла (результата работы) по базе
данных ФАО мирового производства (переработки) рыбной продукции (Apache Derby
Embedded, схема FISHSTAT).

План:
  1. Подготовка локальной копии БД из CSV-дампов (pp_ddl.sql + /CSV) - load_db.py.
  2. Выполнение SQL-запросов в диалекте Apache Derby из папки sql/ (q1..q13).
  3. Пост-обработка каждой таблицы по правилам задания и запись результата
     в Excel-файл result.xlsx, где каждый лист = одна финальная таблица.

Использование:  python build_excel.py
               (при отсутствии каталога БД ./fishdb он создается автоматически
                загрузкой CSV-дампов; повторная загрузка -- опция --reload)

Требования: python 3.x, pandas, openpyxl, jaydebeapi, jpype1; jar-файлы драйвера
Derby лежат в ./lib (используются локально, без загрузки чего-либо из интернета).
"""
import argparse
import os
import re
import sys

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.join(BASE_DIR, "sql")
DB_DIR = os.path.join(BASE_DIR, "fishdb")
RESULT_XLSX = os.path.join(BASE_DIR, "result.xlsx")

YEARS = [2020, 2021, 2022, 2023, 2024]
TOTAL_LABEL = "ВСЕГО (итог)"

# описание финальных таблиц: номер запроса -> имя листа Excel
TABLES = {
    1:  "Таблица 1",
    2:  "Таблица 2",
    3:  "Таблица 3",
    4:  "Таблица 4 (гр.1)",
    5:  "Таблица 5 (гр.2)",
    6:  "Таблица 6 (гр.3)",
    7:  "Таблица 7 (гр.4)",
    8:  "Таблица 8 (гр.5)",
    9:  "Таблица 9 (гр.6)",
    10: "Таблица 10 (гр.7)",
    11: "Таблица 11 (гр.8)",
    12: "Таблица 12 (гр.9)",
    13: "Таблица 13 (гр.A)",
}


# --------------------------------------------------------------------------- #
# Доступ к базе Derby и выполнение SQL-запросов                               #
# --------------------------------------------------------------------------- #
def get_connection():
    import jaydebeapi
    jars = [os.path.join(BASE_DIR, "lib", j) for j in
            ("derby.jar", "derbyshared.jar", "derbytools.jar", "derbyclient.jar")]
    return jaydebeapi.connect(
        "org.apache.derby.jdbc.EmbeddedDriver",
        f"jdbc:derby:{DB_DIR};user=fishstat",
        ["fishstat", "fishstat"],
        jars,
    )


def strip_sql_comments(text):
    """Убирает построчные комментарии '--' (для выполнения через JDBC)."""
    return "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))


def run_query(conn, num):
    """Выполняет sql/q{num}_*.sql и возвращает DataFrame сырых результатов."""
    fname = next(f for f in sorted(os.listdir(SQL_DIR))
                 if re.match(rf"q{num}_.*\.sql$", f))
    with open(os.path.join(SQL_DIR, fname), encoding="utf-8") as fh:
        sql = strip_sql_comments(fh.read())
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows, columns=cols)
    # числовые колонки по годам (Y2020..Y2024) приводим к float (None -> 0)
    for c in df.columns:
        if re.match(r"^Y\d{4}$", str(c)):
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        else:
            df[c] = df[c].map(lambda v: "" if v is None else v)
    return fname, df


# --------------------------------------------------------------------------- #
# Вспомогательные функции пост-обработки                                      #
# --------------------------------------------------------------------------- #
def year_cols(df):
    # явный выбор колонок по годам (а не "последние N"), чтобы не зависеть от порядка
    return [c for c in df.columns if str(c) in [str(y) for y in YEARS]]


def ensure_numeric_years(df):
    """Гарантирует числовой тип годовых колонок (строки/None -> float, NaN -> 0).

    В таблицах 4-13 колонки переименовываются в '2020'..'2024', и если группа
    пуста (SQL вернул 0 строк), dtypes могут остаться объектовыми - без этого
    приведения .abs() падает с TypeError: bad operand type for abs(): 'str'.
    """
    for c in year_cols(df):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


def drop_all_zero_rows(df, total_labels=(TOTAL_LABEL,)):
    """Удаляет строки, где все значения годов равны 0 (строки итогов не трогаем)."""
    yc = year_cols(df)
    mask_nonzero = df[yc].abs().sum(axis=1) > 0
    keep_total = df[df.columns[0]].isin(total_labels) | \
                 df[df.columns[min(1, len(df.columns) - 1)]].isin(total_labels)
    return df[mask_nonzero | keep_total].copy()


def post_table1(df):
    """Таблица 1: производство по странам.

    Вход SQL: COUNTRY_NAME, Y2020..Y2024 (последняя строка 'ВСЕ СТРАНЫ' - итог).
    Правила python: верхняя строка заголовка, строка 'ВСЕГО (итог)' под заголовком,
    удаление полностью нулевых строк, сортировка по убыванию за 2024 г.
    """
    df = df.rename(columns={"COUNTRY_NAME": "Страны"})
    df.columns = ["Страны"] + [str(y) for y in YEARS]
    total_row = df[df["Страны"] == "ВСЕ СТРАНЫ"].copy()
    body = df[df["Страны"] != "ВСЕ СТРАНЫ"].copy()
    body = drop_all_zero_rows(body)
    body = body.sort_values("2024", ascending=False)
    total_row["Страны"] = TOTAL_LABEL
    out = pd.concat([total_row, body], ignore_index=True)
    header = pd.DataFrame([["Страны"] + [str(y) for y in YEARS]], columns=out.columns)
    return pd.concat([header, out], ignore_index=True)


def post_table2(df):
    """Таблица 2: продукция по группам FAO major group и видам.

    Вход SQL: GROUP_NAME, GROUP_CODE, COMMODITY_NAME, Y2020..Y2024;
    строки 'ИТОГ' в колонке видов - итоги по группе, ('ВСЕ ГРУППЫ','','ИТОГ') - общий.
    Правила python: заголовок '| Группы | #группы | Виды | годы |', строка
    'ВСЕГО (итог)' под заголовком, итоги по каждой группе (0 вместо названия вида),
    удаление полностью нулевых строк.
    """
    df.columns = ["Группы", "#группы", "Виды"] + [str(y) for y in YEARS]
    grand = df[(df["Группы"] == "ВСЕ ГРУППЫ") & (df["Виды"] == "ИТОГ")].copy()
    group_totals = df[(df["Группы"] != "ВСЕ ГРУППЫ") & (df["Виды"] == "ИТОГ")].copy()
    items = df[(df["Группы"] != "ВСЕ ГРУППЫ") & (df["Виды"] != "ИТОГ")].copy()
    # итоги групп: 0 вместо названия вида (для последующей сортировки в пределах группы)
    group_totals["Виды"] = 0
    grand["Виды"] = TOTAL_LABEL
    grand["Группы"] = TOTAL_LABEL
    data = pd.concat([grand, group_totals, items], ignore_index=True)
    data = drop_all_zero_rows(data)
    # сортировка: по группе (по её коду: цифры затем A), внутри - итоги первыми,
    # далее виды по алфавиту
    def gkey(code):
        s = str(code)
        return int(s) if s.isdigit() else (10 if s == "" else 99)
    data["_g"] = data["#группы"].map(gkey)
    data["_t"] = (data["Виды"] != 0).astype(int)
    data = data.sort_values(["_g", "_t", "Виды"], kind="stable").drop(columns=["_g", "_t"])
    header = pd.DataFrame([["Группы", "#группы", "Виды"] + [str(y) for y in YEARS]],
                          columns=data.columns)
    return pd.concat([header, data], ignore_index=True)


GROUP_ORDER = [("1", "Группа1"), ("2", "Группа2"), ("3", "Группа3"), ("4", "Группа4"),
               ("5", "Группа5"), ("6", "Группа6"), ("7", "Группа7"), ("8", "Группа8"),
               ("9", "Группа9"), ("A", "ГруппаA")]


def post_table3(df):
    """Таблица 3: продукция по странам и товарным группам (транспонированная).

    Вход SQL: COUNTRY_NAME, GROUP_NAME, GROUP_CODE, Y2020..Y2024;
    'ИТОГ' вместо группы - итог по стране; ('ВСЕ СТРАНЫ','ИТОГ',...) - общий итог.
    Правила python (в указанном порядке):
      а) добавить строку итогов по каждой стране (0 вместо группы для сортировки);
      а) отсортировать нетранспонированную таблицу по возрастанию: страны, # группы;
      б) достроить недостающие группы каждой страны нулевыми строками;
      в) удалить страны с нулевыми итогоми по всем 5 годам;
      г) транспонировать каждую страну отдельно: строки - годы, колонки - группы;
      добавить запись 'ВСЕ СТРАНЫ' с итогами по всем 10 группам и заголовок
      '| Страны | Годы | ВСЕГО | Группа1 | ... | ГруппаA |'.
    """
    df.columns = ["Страны", "Группы", "#группы"] + [str(y) for y in YEARS]
    yc = [str(y) for y in YEARS]
    grand = df[(df["Страны"] == "ВСЕ СТРАНЫ") & (df["Группы"] == "ИТОГ")].copy()
    country_totals = df[(df["Группы"] == "ИТОГ") & (df["Страны"] != "ВСЕ СТРАНЫ")].copy()
    items = df[df["Группы"] != "ИТОГ"].copy()
    # итоги стран: 0 вместо группы (колонки №2 и №3) для сортировки
    country_totals[["Группы", "#группы"]] = 0
    data = pd.concat([country_totals, items], ignore_index=True)

    # в) страны с нулевым итогом по всем 5 годам удаляются целиком (со всеми группами)
    nonzero_countries = set(
        country_totals.loc[country_totals[yc].abs().sum(axis=1) > 0, "Страны"])
    data = data[data["Страны"].isin(nonzero_countries)].copy()

    # а) сортировка нетранспонированной таблицы: страны, затем # группы (0->цифры->A)
    def gkey(v):
        s = str(v)
        if s == "0":
            return -1          # строка итогов страны - первой
        if s.isdigit():
            return int(s)
        return 99              # 'A' - последней
    data["_g"] = data["#группы"].map(gkey)
    data = data.sort_values(["Страны", "_g"], kind="stable").drop(columns=["_g"])

    col_names = ["Группа" + c for c, _ in GROUP_ORDER]

    def transpose_country(sub, country_label):
        """Транспонирование одной страны: строки - годы + ВСЕГО, колонки - группы."""
        total = sub[sub["#группы"].astype(str) == "0"]
        groups = sub[sub["#группы"].astype(str) != "0"]
        rec = {"Страны": [country_label] * (len(YEARS) + 1),
               "Годы": [str(y) for y in YEARS] + ["ВСЕГО"]}
        # колонка ВСЕГО - итоги страны по годам (транспонируется строка итогов)
        if len(total):
            tv = total[yc].iloc[0].tolist()
            rec["ВСЕГО"] = tv + [sum(tv)]
        else:
            rec["ВСЕГО"] = [0.0] * (len(YEARS) + 1)
        # колонки по группам: значения за годы + итог группы за 5 лет
        for code, label in GROUP_ORDER:
            g = groups[groups["#группы"].astype(str) == code]
            vals = g[yc].iloc[0].tolist() if len(g) else [0.0] * len(YEARS)
            rec[label] = vals + [sum(vals)]
        return pd.DataFrame(rec)

    blocks = []
    # итоговая запись "ВСЕ СТРАНЫ" с данными по всем 10 группам:
    # строки групп формируются суммой по всем оставшимся странам
    all_groups = (data[data["#группы"].astype(str) != "0"]
                  .groupby("#группы", sort=False)[yc].sum().reset_index())
    all_groups.insert(0, "Группы", "")
    all_groups.insert(0, "Страны", "ВСЕ СТРАНЫ")
    all_total = pd.DataFrame([["ВСЕ СТРАНЫ", "ИТОГ", 0] +
                              [grand[c].iloc[0] for c in yc]],
                             columns=["Страны", "Группы", "#группы"] + yc)
    ws = pd.concat([all_total, all_groups], ignore_index=True)
    blocks.append(transpose_country(ws, "ВСЕ СТРАНЫ"))

    for country, sub in data.groupby("Страны", sort=True):
        blocks.append(transpose_country(sub, country))

    out = pd.concat(blocks, ignore_index=True)
    header = pd.DataFrame([["Страны", "Годы", "ВСЕГО"] + col_names], columns=out.columns)
    return pd.concat([header, out], ignore_index=True)


def post_table_group(df):
    """Таблицы 4-13: продукция по видам, способам обработки и странам (по группе).

    Вход SQL: COMMODITY_NAME, COUNTRY_NAME, Y2020..Y2024; 'ИТОГ' вместо страны -
    итог по виду; ('ИТОГ','ИТОГ') - общий итог.
    Правила python: заголовок '| Виды | Страны | годы |', строка 'ВСЕГО (итог)'
    под заголовком, итоги по каждому виду (0 вместо страны), сортировка по
    возрастанию: виды, страны.
    """
    df.columns = ["Виды", "Страны"] + [str(y) for y in YEARS]
    df = ensure_numeric_years(df)
    if df.empty or df[year_cols(df)].abs().sum().sum() == 0:
        header = pd.DataFrame([["Виды", "Страны"] + [str(y) for y in YEARS]],
                              columns=df.columns)
        return header  # группа целиком нулевая (пустой лист с заголовком)
    grand = df[(df["Виды"] == "ИТОГ") & (df["Страны"] == "ИТОГ")].copy()
    totals = df[(df["Страны"] == "ИТОГ") & (df["Виды"] != "ИТОГ")].copy()
    items = df[df["Страны"] != "ИТОГ"].copy()
    totals["Страны"] = 0                       # 0 вместо страны для сортировки
    grand["Страны"] = TOTAL_LABEL
    grand["Виды"] = TOTAL_LABEL
    data = pd.concat([grand, totals, items], ignore_index=True)
    data = drop_all_zero_rows(data)
    data["_t"] = (data["Страны"] != 0).astype(int)
    data = data.sort_values(["Виды", "_t", "Страны"], kind="stable") \
                .drop(columns=["_t"])
    header = pd.DataFrame([["Виды", "Страны"] + [str(y) for y in YEARS]],
                          columns=data.columns)
    return pd.concat([header, data], ignore_index=True)


POSTPROCESS = {
    1: post_table1,
    2: post_table2,
    3: post_table3,
    **{n: post_table_group for n in range(4, 14)},
}


# --------------------------------------------------------------------------- #
# Основная программа                                                          #
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Формирование result.xlsx из базы Derby.")
    ap.add_argument("--reload", action="store_true",
                    help="пересоздать локальную копию БД fishdb из CSV-дампов")
    args = ap.parse_args()

    if args.reload or not os.path.isdir(DB_DIR):
        print("Подготовка локальной копии базы Derby из CSV...")
        import load_db
        load_db.main()

    conn = get_connection()
    sheets = {}
    try:
        for num, sheet_name in TABLES.items():
            fname, raw = run_query(conn, num)
            final = POSTPROCESS[num](raw)
            sheets[sheet_name] = final
            print(f"{sheet_name:<20} <- {fname}: SQL {len(raw)} стр. -> финал {len(final)} стр.")
    finally:
        conn.close()

    with pd.ExcelWriter(RESULT_XLSX, engine="openpyxl") as xw:
        for name, df in sheets.items():
            # первая строка DataFrame - заголовок таблицы, пишем как есть (index=False)
            startrow = 1 if name.startswith("Таблица 3") else 0
            df.to_excel(xw, sheet_name=name[:31], index=False, header=False)
            ws = xw.sheets[name[:31]]
            # ширина колонок
            for i, col in enumerate(df.columns, start=1):
                width = max(12, min(45, int(df.shape[0] and
                            max([len(str(col))] + [len(str(v)) for v in df.iloc[:, i-1].head(50)]) * 1.1)))
                ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = width
    print(f"Готово: {RESULT_XLSX}")


if __name__ == "__main__":
    main()
