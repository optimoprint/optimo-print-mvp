import streamlit as st
import requests
import os
import aspose.words as aw
import aspose.cells as ac

# Данные вашего бота (заполните своими)
TELEGRAM_TOKEN = "ВАШ_ТОКЕН"
CHAT_ID = "ID_ВАШЕЙ_ГРУППЫ"

def send_to_telegram(file_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})

# Функция конвертации и отправки
def process_and_send(uploaded_file, copies, check_num):
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Конвертируем все в PDF для единообразия
    pdf_path = temp_path.replace(os.path.splitext(temp_path)[1], ".pdf")
    
    if temp_path.endswith('.docx'):
        aw.Document(temp_path).save(pdf_path)
    elif temp_path.endswith('.xlsx'):
        ac.Workbook(temp_path).save(pdf_path)
    else:
        pdf_path = temp_path # Если уже PDF

    # Отправляем в Telegram с пометкой для Агента
    caption = f"PRINT|COPIES:{copies}|CHECK:{check_num}"
    send_to_telegram(pdf_path, caption)
    
    # Чистим временные файлы на сервере
    os.remove(temp_path)
    if os.path.exists(pdf_path) and pdf_path != temp_path:
        os.remove(pdf_path)
        
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
