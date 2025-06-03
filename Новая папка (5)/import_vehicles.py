import sqlite3
from datetime import datetime

DB_FILENAME = 'autopark.db'

def import_vehicles_from_txt():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    try:
        with open('Автопарк.txt', 'r', encoding='utf-8') as file:
            # Пропускаем заголовок
            next(file)
            
            # Читаем и импортируем данные
            for line in file:
                number, model, category = line.strip().split(',')
                try:
                    cursor.execute('''
                    INSERT INTO Vehicles (vehicle_number, model, category)
                    VALUES (?, ?, ?)
                    ''', (number, model, category))
                except sqlite3.IntegrityError:
                    print(f"Автомобиль с номером {number} уже существует")
                except Exception as e:
                    print(f"Ошибка при импорте автомобиля {number}: {e}")
        
        conn.commit()
        print("Импорт данных успешно завершен")
        
    except FileNotFoundError:
        print("Файл Автопарк.txt не найден")
    except Exception as e:
        print(f"Произошла ошибка при импорте: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import_vehicles_from_txt() 