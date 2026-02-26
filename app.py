import streamlit as st
import sqlite3
import os
import pandas as pd
import qrcode
from io import BytesIO

# --- НАСТРОЙКА ПУТЕЙ ---
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
st.title("🖨️ Optimo Print")
st.caption("Сервис мгновенной печати")

uploaded_file = st.file_uploader("1. Загрузите документ (PDF, JPG, PNG)", type=['pdf', 'jpg', 'png'])

if uploaded_file:
    # Сохранение файла
    file_name = uploaded_file.name
    save_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"✅ Файл {file_name} загружен")
    
    st.divider()
    st.subheader("2. Параметры печати")
    
    col1, col2 = st.columns(2)
    with col1:
        color_option = st.radio("Цветность", ["Черно-белая (100 ₸)", "Цветная (250 ₸)"])
    with col2:
        copies = st.number_input("Количество копий", min_value=1, value=1, step=1)
    
    # Расчет цены
    price_per_page = 100 if "Черно-белая" in color_option else 250
    total_price = price_per_page * copies
    
    st.metric("Итого к оплате", f"{total_price} тенге")
    
    st.divider()
    st.subheader("3. Оплата")

    # Используем session_state, чтобы QR не исчезал при нажатии кнопок
    if st.button("Сформировать Kaspi QR", use_container_width=True):
        order_id = save_order("Cloud_Terminal_Almaty", total_price, save_path)
        st.session_state['current_order_id'] = order_id
        
        # Ссылка для QR
        qr_link = f"https://kaspi.kz/pay/OptimoPrint?amount={total_price}&order={order_id}"
        qr_img = qrcode.make(qr_link)
        buf = BytesIO()
        qr_img.save(buf)
        
        st.image(buf, width=250, caption=f"Заказ №{order_id}")
        st.warning("Отсканируйте QR в приложении Kaspi и оплатите")

    # Кнопка подтверждения оплаты
    if 'current_order_id' in st.session_state:
        if st.button(f"✅ Я оплатил заказ №{st.session_state['current_order_id']}", use_container_width=True):
            update_order_status(st.session_state['current_order_id'], 'Paid')
            st.success("Оплата подтверждена! Документ отправлен в очередь печати.")
            st.balloons()
            # Очищаем состояние после успеха
            del st.session_state['current_order_id']
