import streamlit as st
import sqlite3
import os
import pandas as pd
import qrcode
from io import BytesIO

# --- НАСТРОЙКА ПУТЕЙ (Универсально для Windows и Cloud) ---
# Используем текущую директорию скрипта для создания папки uploads
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR)
    except Exception as e:
        st.error(f"Ошибка создания папки: {e}")

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
def init_db():
    conn = sqlite3.connect('optimo_print.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            point_id TEXT,
            total_amount REAL,
            payment_status TEXT,
            print_status TEXT,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- ФУНКЦИИ ---
def save_order(point_id, amount, file_path):
    conn = sqlite3.connect('optimo_print.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (point_id, total_amount, payment_status, print_status, file_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (point_id, amount, 'Waiting', 'Pending', file_path))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

def update_order_status(order_id, status):
    conn = sqlite3.connect('optimo_print.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET payment_status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

# --- ИНТЕРФЕЙС ---
st.set_page_config(page_title="Optimo Print Cloud", layout="centered")
st.title("🖨️ Optimo Print Terminal")

uploaded_file = st.file_uploader("Загрузите документ", type=['pdf', 'jpg', 'png'])

if uploaded_file:
    # Безопасное сохранение файла
    file_name = uploaded_file.name
    save_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Файл {file_name} загружен!")
    
    price = 500 # Тестовая цена
    st.info(f"Сумма к оплате: {price} тенге")

    if st.button("Сгенерировать QR"):
        # Сохраняем в базу путь к файлу
        order_id = save_order("Cloud_Terminal_1", price, save_path)
        
        # Генерация QR
        qr_link = f"https://kaspi.kz/pay/OptimoPrint?amount={price}&order={order_id}"
        qr_img = qrcode.make(qr_link)
        buf = BytesIO()
        qr_img.save(buf)
        
        st.image(buf, width=300, caption=f"Заказ №{order_id}")
        st.write("После оплаты нажмите кнопку ниже")
        
        if st.button("✅ Подтвердить оплату"):
            update_order_status(order_id, 'Paid')
            st.success("Статус обновлен на 'Оплачено'!")
            st.balloons()
