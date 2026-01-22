import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- Configuración ---
st.set_page_config(page_title="Gestión Canina", layout="wide")

def init_db():
    conn = sqlite3.connect('perros.db')
    c = conn.cursor()
    # Tablas
    c.execute('''CREATE TABLE IF NOT EXISTS dogs
                 (id INTEGER PRIMARY KEY, name TEXT, breed TEXT, color TEXT, 
                  birthdate DATE, sex TEXT, photo BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visits
                 (id INTEGER PRIMARY KEY, dog_id INTEGER, visit_date DATE, 
                  weight REAL, meds TEXT, treatment TEXT, purchase TEXT,
                  FOREIGN KEY(dog_id) REFERENCES dogs(id))''')
    conn.commit()
    return conn

def calculate_age(birthdate_str):
    birth = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
    today = date.today()
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    months = (today.year - birth.year) * 12 + today.month - birth.month
    return f"{years} años ({months} meses totales)"

conn = init_db()

# --- Barra Lateral ---
st.sidebar.header("🐶 Mis Perros")

with st.sidebar.expander("Añadir Nuevo Perro"):
    with st.form("new_dog"):
        name = st.text_input("Nombre")
        breed = st.text_input("Raza")
        color = st.text_input("Color")
        b_date = st.date_input("Fecha Nacimiento")
        sex = st.selectbox("Sexo", ["Macho", "Hembra"])
        photo = st.file_uploader("Foto", type=['png', 'jpg', 'jpeg'])
        if st.form_submit_button("Guardar Perro") and name:
            photo_blob = photo.read() if photo else None
            conn.cursor().execute("INSERT INTO dogs (name, breed, color, birthdate, sex, photo) VALUES (?,?,?,?,?,?)",
                                  (name, breed, color, b_date, sex, photo_blob))
            conn.commit()
            st.rerun()

dogs_df = pd.read_sql("SELECT id, name FROM dogs", conn)
selected_dog_id = None

if not dogs_df.empty:
    selected_dog_name = st.sidebar.selectbox("Seleccionar Perro", dogs_df['name'])
    selected_dog_id = dogs_df[dogs_df['name'] == selected_dog_name]['id'].values[0]

# --- Vista Principal ---
if selected_dog_id:
    dog = pd.read_sql("SELECT * FROM dogs WHERE id = ?", conn, params=(selected_dog_id,)).iloc[0]
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image(dog['photo'], width=200) if dog['photo'] else st.info("Sin foto")
    with col2:
        st.title(dog['name'])
        st.markdown(f"**Raza:** {dog['breed']} | **Color:** {dog['color']} | **Sexo:** {dog['sex']}")
        st.markdown(f"**Edad:** {calculate_age(dog['birthdate'])}")

    st.divider()

    # Formulario Visitas
    col_form, col_data = st.columns([1, 2])
    with col_form:
        st.subheader("Nueva Visita")
        with st.form("new_visit"):
            v_date = st.date_input("Fecha", date.today())
            v_weight = st.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.2f")
            v_meds = st.text_area("Medicaciones")
            v_treat = st.text_input("Tratamientos")
            v_buy = st.text_input("Compras/Gastos")
            if st.form_submit_button("Registrar"):
                conn.cursor().execute('''INSERT INTO visits (dog_id, visit_date, weight, meds, treatment, purchase)
                                         VALUES (?,?,?,?,?,?)''', (int(selected_dog_id), v_date, v_weight, v_meds, v_treat, v_buy))
                conn.commit()
                st.rerun()

    # Datos y Gráficos
    with col_data:
        visits = pd.read_sql("SELECT * FROM visits WHERE dog_id = ? ORDER BY visit_date DESC", conn, params=(selected_dog_id,))
        tab1, tab2 = st.tabs(["📋 Historial", "📈 Peso"])
        
        with tab1:
            if not visits.empty:
                st.dataframe(visits[['visit_date', 'weight', 'meds', 'treatment', 'purchase']], hide_index=True, use_container_width=True)
            else:
                st.info("Sin registros.")
        
        with tab2:
            if not visits.empty and visits['weight'].sum() > 0:
                st.line_chart(visits[visits['weight'] > 0].sort_values('visit_date'), x='visit_date', y='weight')
            else:
                st.warning("Faltan datos de peso.")
else:
    st.info("👈 Añade un perro en el menú lateral.")

