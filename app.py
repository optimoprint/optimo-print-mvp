import streamlit as st
import sqlite3
import os
import pandas as pd
import qrcode
from io import BytesIO
from datetime import datetime

# Настройки папок
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- ФУНКЦИИ БАЗЫ ДАННЫХ ---
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

def get_orders_data():
    conn = sqlite3.connect('optimo_print.db')
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()
    return df

# --- ИНТЕРФЕЙС ---
st.set_page_config(page_title="Optimo Print System", layout="wide", page_icon="📈")

tab1, tab2 = st.tabs(["📱 Терминал самообслуживания", "📊 Кабинет партнера (Admin)"])

# --- ВКЛАДКА КЛИЕНТА ---
with tab1:
    st.title("🖨️ Optimo Print")
    st.info("Быстрая печать документов и фото")
    
    uploaded_file = st.file_uploader("Загрузите файл", type=['pdf', 'jpg', 'png'])
    
    if uploaded_file:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        col1, col2 = st.columns(2)
        with col1:
            color = st.selectbox("Цветность", ["Черно-белая (100 тг)", "Цветная (250 тг)"])
        with col2:
            copies = st.number_input("Кол-во копий", min_value=1, value=1)
        
        price_per_page = 100 if "Черно-белая" in color else 250
        total_price = price_per_page * copies
        
        st.subheader(f"К оплате: {total_price} тенге")

        if st.button("Сгенерировать Kaspi QR", use_container_width=True):
            order_id = save_order("Point_Almaty_1", total_price, file_path)
            
            # Генерация QR
            qr_link = f"https://kaspi.kz/pay/OptimoPrint?amount={total_price}&order={order_id}"
            qr = qrcode.make(qr_link)
            buf = BytesIO()
            qr.save(buf)
            
            st.image(buf, width=250, caption="Отсканируйте в приложении Kaspi")
            st.warning("⚠️ Нажмите кнопку ниже только ПОСЛЕ успешной оплаты в приложении")
            
            if st.button("✅ Я оплатил"):
                update_order_status(order_id, 'Paid')
                st.success("Оплата получена! Задание отправлено на принтер.")
                st.balloons()

# --- ВКЛАДКА АДМИНКИ ---
with tab2:
    st.title("📊 Панель управления бизнесом")
    
    auth_pass = st.text_input("Введите ключ доступа", type="password")
    
    if auth_pass == "admin777":
        df = get_orders_data()
        
        if not df.empty:
            # Расчет метрик (только для оплаченных заказов)
            paid_orders = df[df['payment_status'] == 'Paid']
            total_revenue = paid_orders['total_amount'].sum()
            our_commission = total_revenue * 0.25 # 25% сервису
            partner_net = total_revenue * 0.75    # 75% партнеру
            
            # Красивые карточки (Metrics)
            m1, m2, m3 = st.columns(3)
            m1.metric("Общая выручка", f"{total_revenue} ₸")
            m2.metric("Комиссия системы (25%)", f"{our_commission} ₸", delta_color="inverse")
            m3.metric("Прибыль партнера (75%)", f"{partner_net} ₸")
            
            st.divider()
            
            # Таблица мониторинга
            st.subheader("📋 Реестр всех операций")
            
            # Подсветка статусов для наглядности
            def highlight_status(val):
                color = 'green' if val == 'Paid' else ('orange' if val == 'Waiting' else 'red')
                return f'color: {color}'
            
            st.dataframe(df.style.applymap(highlight_status, subset=['payment_status']), use_container_width=True)
            
            # Аналитика по принтеру
            st.subheader("🛠 Статус оборудования")
            pending_prints = df[df['print_status'] == 'Pending'].shape[0]
            st.info(f"В очереди на печать: {pending_prints} заказов")
            
        else:
            st.write("Транзакций пока не зафиксировано.")
    elif auth_pass != "":
        st.error("Неверный ключ доступа!")