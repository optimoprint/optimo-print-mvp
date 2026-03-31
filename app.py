import streamlit as st
import requests
import os
import aspose.words as aw
import aspose.cells as ac
from PyPDF2 import PdfReader

# --- ВАШИ ДАННЫЕ ---
TELEGRAM_TOKEN = "8542318789:AAGuKJn9MaRkIpsrcvl5LzSYTBJfPIc9wMs"
CHAT_ID = "5271547482"

def send_to_telegram(file_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            response = requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"document": f})
        return response.status_code == 200
    except Exception as e:
        st.error(f"Ошибка отправки в Telegram: {e}")
        return False

# Функция точного подсчета страниц (Aspose)
def get_page_count(uploaded_file):
    temp_name = f"count_{uploaded_file.name}"
    with open(temp_name, "wb") as f:
        f.write(uploaded_file.getbuffer())
    try:
        if temp_name.endswith('.docx'):
            return aw.Document(temp_name).page_count
        elif temp_name.endswith('.xlsx'):
            wb = ac.Workbook(temp_name)
            count = 0
            for i in range(wb.worksheets.count):
                render = ac.SheetRender(wb.worksheets.get(i), ac.ImageOrPrintOptions())
                count += render.page_count
            return count
        elif temp_name.endswith('.pdf'):
            return len(PdfReader(temp_name).pages)
        return 1
    finally:
        if os.path.exists(temp_name): os.remove(temp_name)

# --- ИНТЕРФЕЙС ---
st.title("🖨️ Optimo Print")
files = st.file_uploader("Загрузите файлы", type=['pdf', 'docx', 'xlsx', 'jpg', 'png'], accept_multiple_files=True)

if files:
    total_pages = sum([get_page_count(f) for f in files])
    copies = st.number_input("Кол-во копий каждого файла", min_value=1, value=1)
    
    st.info(f"Всего страниц к печати: {total_pages * copies}")
    check_num = st.text_input("Введите 4 цифры чека:")

    if st.button("🚀 ОПЛАТИТЬ И ПЕЧАТАТЬ", type="primary"):
        if check_num:
            for f in files:
                # Отправляем файл боту
                caption = f"PRINT|COPIES:{copies}|CHECK:{check_num}|FILE:{f.name}"
                
                # Сохраняем временно для отправки
                with open(f.name, "wb") as temp_f:
                    temp_f.write(f.getbuffer())
                
                if send_to_telegram(f.name, caption):
                    st.success(f"Файл {f.name} отправлен!")
                os.remove(f.name)
            st.balloons()
        else:
            st.warning("Введите номер чека!")
            
        
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
