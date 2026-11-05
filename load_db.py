# -*- coding: utf-8 -*-
"""
Служебный скрипт подготовки локальной копии базы Apache Derby Embedded (схема FISHSTAT)
из CSV-дампов таблиц из папки /CSV. Загружает данные через JDBC-драйвер Derby
(jaydebeapi + jpype1), используя штатную DDL-структуру pp_ddl.sql.

Использование:  python load_db.py
Результат:      каталог БД ./fishdb с заполненными таблицами FISHSTAT.*
"""
import csv
import os
import re
import shutil

import jaydebeapi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "fishdb")
CSV_DIR = os.path.join(BASE_DIR, "CSV")
DDL_FILE = os.path.join(BASE_DIR, "pp_ddl.sql")
LIB_JARS = [os.path.join(BASE_DIR, "lib", j) for j in
            ("derby.jar", "derbyshared.jar", "derbytools.jar", "derbyclient.jar")]

DRIVER = "org.apache.derby.jdbc.EmbeddedDriver"


def get_connection(create=True):
    return jaydebeapi.connect(
        DRIVER,
        f"jdbc:derby:{DB_DIR};create={'true' if create else 'false'};user=fishstat",
        ["fishstat", "fishstat"],
        LIB_JARS,
    )


def split_statements(sql_text):
    """Разбивает DDL на инструкции (простейший разделитель ';' вне комментариев)."""
    # убираем построчные комментарии --
    lines = []
    for line in sql_text.splitlines():
        lines.append(re.sub(r"--.*$", "", line))
    text = "\n".join(lines)
    return [s.strip() for s in text.split(";") if s.strip()]


def load_csv(cur, table, columns):
    path = os.path.join(CSV_DIR, table + ".csv")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [[r.get(c) if r.get(c) not in ("", None) else None for c in columns]
                for r in reader]
    placeholders = ",".join(["?"] * len(columns))
    sql = f"INSERT INTO FISHSTAT.{table} ({','.join(columns)}) VALUES ({placeholders})"
    cur.executemany(sql, rows)
    return len(rows)


def table_columns(cur, table):
    cur.execute(f"SELECT * FROM FISHSTAT.{table} WHERE 1=0")
    return [d[0] for d in cur.description]


def main():
    if os.path.isdir(DB_DIR):
        shutil.rmtree(DB_DIR)
    conn = get_connection(create=True)
    try:
        cur = conn.cursor()
        # 1. создаём таблицы по штатной DDL
        with open(DDL_FILE, encoding="utf-8") as f:
            ddl = f.read()
        for stmt in split_statements(ddl):
            try:
                cur.execute(stmt)
            except Exception as e:
                print("DDL skip:", str(e)[:120])
        conn.commit()
        # 2. загружаем CSV-дампы (порядок важен из-за внешних ключей)
        for table in ("REF_COMMODITY_MAJOR2", "REF_COUNTRY", "REF_MEASURE",
                      "REF_COMMODITY", "REL_COMMODITY_MAJOR", "TSD_TRADE_PP_QUANTITY"):
            cols = table_columns(cur, table)
            n = load_csv(cur, table, cols)
            conn.commit()
            print(f"{table}: {n} строк")
        cur.close()
    finally:
        conn.close()
    print("Готово: база fishdb создана и заполнена.")


if __name__ == "__main__":
    main()
