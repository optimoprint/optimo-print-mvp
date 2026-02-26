import sqlite3

def create_db():
    conn = sqlite3.connect('optimo_print.db')
    cursor = conn.cursor()

    # 1. Пользователи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT CHECK(role IN ('Admin', 'Partner', 'Operator')),
            email TEXT UNIQUE,
            password TEXT
        )
    ''')

    # 2. Точки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id INTEGER,
            address TEXT,
            status TEXT DEFAULT 'offline',
            FOREIGN KEY (partner_id) REFERENCES users (id)
        )
    ''')

    # 3. Заказы (Теперь точно с file_path)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            point_id INTEGER,
            total_amount REAL,
            payment_status TEXT DEFAULT 'Awaiting payment',
            print_status TEXT DEFAULT 'Pending',
            file_path TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (point_id) REFERENCES points (id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ База данных пересоздана успешно!")

if __name__ == "__main__":
    create_db()