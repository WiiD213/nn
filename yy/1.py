import sqlite3
import pandas as pd
import os

# Имя файла базы данных
db_file = 'autopark.db'
# Имя файла с данными для импорта (Автопарк)
excel_file_autopark = 'Документы заказчика/Автопарк.xlsx'
# Имена файлов для других таблиц (если есть)
# excel_file_mileage = 'Документы заказчика/Данные по пробегу.xlsx' # Пример
# excel_file_report = 'Документы заказчика/Отчет по автопарку на дату.xlsx' # Пример


# SQL-скрипты для создания таблиц
sql_create_autopark_table = """
CREATE TABLE IF NOT EXISTS Автопарк (
    "ID автомобиля" INTEGER PRIMARY KEY AUTOINCREMENT,
    Марка TEXT,
    Модель TEXT,
    "Год выпуска" INTEGER,
    "Гос. номер" TEXT UNIQUE,
    Статус TEXT
);
"""

sql_create_mileage_table = """
CREATE TABLE IF NOT EXISTS Данные_по_пробегу (
    "ID записи" INTEGER PRIMARY KEY AUTOINCREMENT,
    "ID автомобиля" INTEGER,
    Дата TEXT, -- Возможно, стоит использовать тип DATE или DATETIME
    Пробег REAL,
    "Тип обслуживания" TEXT,
    FOREIGN KEY ("ID автомобиля") REFERENCES Автопарк("ID автомобиля")
);
"""

sql_create_report_table = """
CREATE TABLE IF NOT EXISTS Отчет_по_автопарку (
    "ID отчета" INTEGER PRIMARY KEY AUTOINCREMENT,
    "ID автомобиля" INTEGER,
    "Дата отчета" TEXT, -- Возможно, стоит использовать тип DATE или DATETIME
    "Статус ТО" TEXT,
    "Расход топлива" REAL,
    FOREIGN KEY ("ID автомобиля") REFERENCES Автопарк("ID автомобиля")
);
"""

# Таблица Аренда удалена


def create_connection(db_file):
    """ Создает соединение с базой данных SQLite """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # Включаем поддержку внешних ключей (по умолчанию отключена в старых версиях SQLite)
        conn.execute('PRAGMA foreign_keys = ON;')
        print(f"Подключено к базе данных SQLite: {db_file}")
        return conn
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ Создает таблицу """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(e)

def import_data_from_excel(conn, excel_path, table_name):
    """ Импортирует данные из Excel в указанную таблицу """
    if not os.path.exists(excel_path):
        print(f"Ошибка: файл Excel не найден по пути {excel_path}")
        return

    try:
        df = pd.read_excel(excel_path)

        # Приводим имена колонок DataFrame для соответствия именам в базе данных
        # Удаляем пробелы и точки, заменяем пробелы на подчеркивания, приводим к нижнему регистру
        df.columns = df.columns.str.strip()
        df.columns = df.columns.str.replace('.', '', regex=False)
        df.columns = df.columns.str.replace(' ', '_', regex=False)
        df.columns = df.columns.str.lower()

        # Сопоставление имен колонок Excel (в нижнем регистре) с именами колонок БД
        # !!! ВАЖНО: Убедитесь, что эти сопоставления верны для ваших файлов Excel !!!
        column_map = {}
        if table_name == 'Автопарк':
            column_map = {
                'id_автомобиля': 'ID автомобиля',
                'марка': 'Марка',
                'модель': 'Модель',
                'год_выпуска': 'Год выпуска',
                'гос_номер': 'Гос. номер',
                'статус': 'Статус'
            }
        elif table_name == 'Данные_по_пробегу':
             column_map = {
                'id_записи': 'ID записи',
                'id_автомобиля': 'ID автомобиля',
                'дата': 'Дата',
                'пробег': 'Пробег',
                'тип_обслуживания': 'Тип обслуживания'
             }
        elif table_name == 'Отчет_по_автопарку':
            column_map = {
                'id_отчета': 'ID отчета',
                'id_автомобиля': 'ID автомобиля',
                'дата_отчета': 'Дата отчета',
                'статус_то': 'Статус ТО',
                'расход_топлива': 'Расход топлива'
            }
        # Сопоставление для таблицы Аренда удалено


        # Переименование колонок DataFrame согласно сопоставлению
        df.rename(columns=column_map, inplace=True)

         # Проверка наличия всех необходимых колонок после переименования
        required_cols = list(column_map.values())
        if not all(col in df.columns for col in required_cols):
             print(f"Ошибка: Не все необходимые колонки найдены в файле Excel для таблицы {table_name}. Ожидаемые колонки: {required_cols}. Найденные колонки в Excel (после обработки): {df.columns.tolist()}")
             return


        # Запись данных в таблицу
        df.to_sql(table_name, conn, if_exists='replace', index=False) # Используем 'replace' для простоты при повторных запусках
        print(f"Данные успешно импортированы из {excel_path} в таблицу {table_name}.")

    except FileNotFoundError:
        print(f"Ошибка: файл Excel не найден по пути {excel_path}")
    except ImportError:
        print("Ошибка импорта: пожалуйста, убедитесь, что у вас установлены библиотеки pandas и openpyxl (`pip install pandas openpyxl`)")
    except Exception as e:
        print(f"Произошла ошибка при импорте данных в таблицу {table_name}: {e}")


def calculate_vehicle_utilization_approximate(conn):
    """
    Приближенно вычисляет процент загрузки автомобилей на основе их текущего Статуса.
    Считает автомобиль "в использовании", если его статус - 'в эксплуатации', 'Занят', или 'Назначен к ТО'.
    Процент загрузки для такого автомобиля считается 100%, иначе - 0%.
    """
    print("\n--- Приближенный расчет процента загрузки автомобилей (по статусу) ---")

    # Список статусов, которые считаются "в использовании"
    in_use_statuses = ['в эксплуатации', 'Занят', 'Назначен к ТО']
    # Создаем строку для использования в SQL запросе: "'статус1', 'статус2', ..."
    statuses_sql = ", ".join(f"'{s}'" for s in in_use_statuses)


    # Запрос для получения гос. номера и статуса каждого автомобиля
    query_status = f"""
    SELECT
        "Гос. номер",
        Статус
    FROM
        Автопарк;
    """

    try:
        cur = conn.cursor()
        cur.execute(query_status)
        rows = cur.fetchall()

        if rows:
            print("Гос. номер | Статус        | Процент загрузки (%)")
            print("----------|---------------|---------------------")
            for row in rows:
                gos_number, status = row
                # Определяем процент загрузки на основе статуса
                utilization_percentage = 100.0 if status in in_use_statuses else 0.0
                print(f"{gos_number:<10}| {status:<13}| {utilization_percentage:.2f}")

        else:
            print("Нет данных в таблице Автопарк для расчета процента загрузки.")

    except sqlite3.Error as e:
        print(f"Произошла ошибка при выполнении запроса расчета загрузки: {e}")
    except Exception as e:
        print(f"Произошла неожиданная ошибка при расчете загрузки: {e}")


def main():
    # Создаем или подключаемся к базе данных
    conn = create_connection(db_file)

    if conn is not None:
        # Создаем таблицы (исключая Аренда)
        create_table(conn, sql_create_autopark_table)
        create_table(conn, sql_create_mileage_table)
        create_table(conn, sql_create_report_table)
        print("Таблицы Автопарк, Данные_по_пробегу, Отчет_по_автопарку созданы (если не существовали).")

        # Импортируем данные из Excel в таблицу Автопарк
        # Убедитесь, что файл "Автопарк.xlsx" находится в папке "Документы заказчика"
        import_data_from_excel(conn, excel_file_autopark, 'Автопарк')

        # !!! ВАЖНО !!!
        # Если у вас есть данные для таблиц Данные_по_пробегу и Отчет_по_автопарку
        # в формате Excel, вы можете использовать функцию import_data_from_excel для их импорта.
        # Например:
        # import_data_from_excel(conn, excel_file_mileage, 'Данные_по_пробегу')
        # import_data_from_excel(conn, excel_file_report, 'Отчет_по_автопарку')
        # Импорт для таблицы Аренда удален

        # Вычисляем приближенный процент загрузки автомобилей
        calculate_vehicle_utilization_approximate(conn)

        # Закрываем соединение
        conn.close()
        print("Соединение с базой данных закрыто.")
    else:
        print("Не удалось создать подключение к базе данных.")

if __name__ == '__main__':
    main()