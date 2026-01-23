import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- Configuración y Base de Datos ---
st.set_page_config(page_title="Gestión Canina", layout="wide")

def init_db():
    # check_same_thread=False es necesario en Streamlit Cloud
    conn = sqlite3.connect('perros.db', check_same_thread=False)
    c = conn.cursor()
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
    if not birthdate_str: return "Desconocida"
    try:
        birth = datetime.strptime(str(birthdate_str), '%Y-%m-%d').date()
        today = date.today()
        years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        months = (today.year - birth.year) * 12 + today.month - birth.month
        return f"{years} años ({months} meses totales)"
    except:
        return "Fecha inválida"

conn = init_db()

# --- Barra Lateral: Gestión de Perros ---
st.sidebar.header("🐶 Mis Perros")

# Formulario para añadir perro
with st.sidebar.expander("Añadir Nuevo Perro"):
    with st.form("new_dog"):
        name = st.text_input("Nombre")
        breed = st.text_input("Raza")
        color = st.text_input("Color")
        b_date = st.date_input("Fecha Nacimiento")
        sex = st.selectbox("Sexo", ["Macho", "Hembra"])
        photo = st.file_uploader("Foto", type=['png', 'jpg', 'jpeg'])
        submit_dog = st.form_submit_button("Guardar Perro")
        
        if submit_dog and name:
            photo_blob = photo.read() if photo else None
            try:
                c = conn.cursor()
                c.execute("INSERT INTO dogs (name, breed, color, birthdate, sex, photo) VALUES (?,?,?,?,?,?)",
                          (name, breed, color, b_date, sex, photo_blob))
                conn.commit()
                st.success("Perro guardado. Recarga la página si no aparece.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# Selector de perro activo
dogs_df = pd.read_sql("SELECT id, name FROM dogs", conn)
selected_dog_id = None

if not dogs_df.empty:
    selected_dog_name = st.sidebar.selectbox("Seleccionar Perro", dogs_df['name'])
    # CORRECCIÓN IMPORTANTE: Aseguramos que el ID es un entero nativo de Python
    selected_dog_id = int(dogs_df[dogs_df['name'] == selected_dog_name]['id'].values[0])

# --- Vista Principal ---
if selected_dog_id:
    # CORRECCIÓN: Verificamos que la consulta devuelva datos antes de leer
    dog_data = pd.read_sql("SELECT * FROM dogs WHERE id = ?", conn, params=(selected_dog_id,))
    
    if not dog_data.empty:
        dog = dog_data.iloc[0]
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if dog['photo']:
                st.image(dog['photo'], width=200)
            else:
                st.info("Sin foto")
        
        with col2:
            st.title(dog['name'])
            st.markdown(f"**Raza:** {dog['breed']} | **Color:** {dog['color']} | **Sexo:** {dog['sex']}")
            st.markdown(f"**Edad:** {calculate_age(dog['birthdate'])} | **Nacimiento:** {dog['birthdate']}")

        st.divider()

        # --- Gestión de Visitas ---
        col_form, col_data = st.columns([1, 2])

        with col_form:
            st.subheader("Nueva Visita / Gasto")
            with st.form("new_visit"):
                v_date = st.date_input("Fecha", date.today())
                v_weight = st.number_input("Peso (kg)", min_value=0.0, step=0.1, format="%.2f")
                v_meds = st.text_area("Medicaciones")
                v_treat = st.text_input("Tratamientos")
                v_buy = st.text_input("Compras/Gastos")
                submit_visit = st.form_submit_button("Registrar Visita")

                if submit_visit:
                    c = conn.cursor()
                    c.execute('''INSERT INTO visits (dog_id, visit_date, weight, meds, treatment, purchase)
                                 VALUES (?,?,?,?,?,?)''', 
                                 (selected_dog_id, v_date, v_weight, v_meds, v_treat, v_buy))
                    conn.commit()
                    st.rerun()

        with col_data:
            st.subheader("Historial y Gráficas")
            
            # Cargar visitas
            visits = pd.read_sql("SELECT * FROM visits WHERE dog_id = ? ORDER BY visit_date DESC", 
                                 conn, params=(selected_dog_id,))
            
            tab1, tab2 = st.tabs(["📋 Historial Detallado", "📈 Gráfico de Peso"])
            
            with tab1:
                if not visits.empty:
                    st.dataframe(visits[['visit_date', 'weight', 'meds', 'treatment', 'purchase']]
                                 .rename(columns={'visit_date':'Fecha', 'weight':'Peso (kg)', 
                                                  'meds':'Medicación', 'treatment':'Tratamiento', 
                                                  'purchase':'Compra'}), 
                                 hide_index=True, use_container_width=True)
                else:
                    st.info("No hay visitas registradas.")

            with tab2:
                if not visits.empty and visits['weight'].sum() > 0:
                    weight_data = visits[visits['weight'] > 0].sort_values('visit_date')
                    st.line_chart(weight_data, x='visit_date', y='weight')
                else:
                    st.warning("No hay datos de peso suficientes para graficar.")
    else:
        st.warning("No se pudo cargar la información del perro seleccionado.")

else:
    st.info("👈 Añade o selecciona un perro en el menú lateral para comenzar.")
