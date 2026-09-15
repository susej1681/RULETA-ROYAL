import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Ruleta Royal Pro - Control Total",
    page_icon="🎡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# DICCIONARIO DE ANIMALITOS (REGLAS OFICIALES)
# ==========================================
ANIMALES_MAP = {
    "0": "Tiburón",
    "01": "Carnero", "02": "Toro", "03": "Ciempiés", 
    "04": "Alacrán", "05": "León", "06": "Rana", "07": "Perico", "08": "Ratón", 
    "09": "Águila", "10": "Tigre", "11": "Gato", "12": "Caballo", "13": "Mono", 
    "14": "Paloma", "15": "Zorro", "16": "Oso", "17": "Pavo", "18": "Burro", 
    "19": "Chivo", "20": "Cochino", "21": "Gallo", "22": "Camello", "23": "Cebra", 
    "24": "Iguana", "25": "Gallina", "26": "Vaca", "27": "Perro", "28": "Zamuro", 
    "29": "Elefante", "30": "Caimán", "31": "Lapa", "32": "Ardilla", "33": "Pescado", 
    "34": "Venado", "35": "Pantera", "36": "Culebra"
}

# Horarios exactos de Ruleta Royal (8:30 AM a 8:30 PM)
HORARIOS_ROYAL = [
    "08:30 AM", "09:30 AM", "10:30 AM", "11:30 AM", "12:30 PM", 
    "01:30 PM", "02:30 PM", "03:30 PM", "04:30 PM", "05:30 PM", 
    "06:30 PM", "07:30 PM", "08:30 PM"
]

# ==========================================
# ESTADO INICIAL: 5 DÍAS DE HISTORIAL PRECARGADOS
# ==========================================
if 'df_sorteos_royal' not in st.session_state:
    raw_data = [
        # 11/09/2026 (13 sorteos)
        ("11/09/2026", "08:30 AM", "02"), ("11/09/2026", "09:30 AM", "18"), ("11/09/2026", "10:30 AM", "19"),
        ("11/09/2026", "11:30 AM", "23"), ("11/09/2026", "12:30 PM", "29"), ("11/09/2026", "01:30 PM", "07"),
        ("11/09/2026", "02:30 PM", "31"), ("11/09/2026", "03:30 PM", "22"), ("11/09/2026", "04:30 PM", "19"),
        ("11/09/2026", "05:30 PM", "12"), ("11/09/2026", "06:30 PM", "32"), ("11/09/2026", "07:30 PM", "05"),
        ("11/09/2026", "08:30 PM", "23"),
        
        # 12/09/2026 (13 sorteos)
        ("12/09/2026", "08:30 AM", "11"), ("12/09/2026", "09:30 AM", "29"), ("12/09/2026", "10:30 AM", "16"),
        ("12/09/2026", "11:30 AM", "14"), ("12/09/2026", "12:30 PM", "28"), ("12/09/2026", "01:30 PM", "23"),
        ("12/09/2026", "02:30 PM", "08"), ("12/09/2026", "03:30 PM", "25"), ("12/09/2026", "04:30 PM", "13"),
        ("12/09/2026", "05:30 PM", "22"), ("12/09/2026", "06:30 PM", "07"), ("12/09/2026", "07:30 PM", "13"),
        ("12/09/2026", "08:30 PM", "05"),
        
        # 13/09/2026 (13 sorteos)
        ("13/09/2026", "08:30 AM", "21"), ("13/09/2026", "09:30 AM", "05"), ("13/09/2026", "10:30 AM", "28"),
        ("13/09/2026", "11:30 AM", "04"), ("13/09/2026", "12:30 PM", "13"), ("13/09/2026", "01:30 PM", "09"),
        ("13/09/2026", "02:30 PM", "18"), ("13/09/2026", "03:30 PM", "22"), ("13/09/2026", "04:30 PM", "04"),
        ("13/09/2026", "05:30 PM", "32"), ("13/09/2026", "06:30 PM", "08"), ("13/09/2026", "07:30 PM", "14"),
        ("13/09/2026", "08:30 PM", "24"),
        
        # 14/09/2026 (13 sorteos)
        ("14/09/2026", "08:30 AM", "15"), ("14/09/2026", "09:30 AM", "11"), ("14/09/2026", "10:30 AM", "09"),
        ("14/09/2026", "11:30 AM", "12"), ("14/09/2026", "12:30 PM", "30"), ("14/09/2026", "01:30 PM", "0"),
        ("14/09/2026", "02:30 PM", "33"), ("14/09/2026", "03:30 PM", "31"), ("14/09/2026", "04:30 PM", "03"),
        ("14/09/2026", "05:30 PM", "27"), ("14/09/2026", "06:30 PM", "32"), ("14/09/2026", "07:30 PM", "30"),
        ("14/09/2026", "08:30 PM", "13"),
        
        # 15/09/2026 (Sorteos transcurridos hasta el momento)
        ("15/09/2026", "08:30 AM", "05"), ("15/09/2026", "09:30 AM", "30"), ("15/09/2026", "10:30 AM", "26"),
        ("15/09/2026", "11:30 AM", "17"), ("15/09/2026", "12:30 PM", "03"), ("15/09/2026", "01:30 PM", "06"),
        ("15/09/2026", "02:30 PM", "29"), ("15/09/2026", "03:30 PM", "36"), ("15/09/2026", "04:30 PM", "24"),
        ("15/09/2026", "05:30 PM", "22")
    ]
    
    datos_iniciales = []
    for fecha, hora, num in raw_data:
        datos_iniciales.append({
            "Fecha": fecha,
            "Hora": hora,
            "Numero": num,
            "Animal": ANIMALES_MAP.get(num, "")
        })
    st.session_state['df_sorteos_royal'] = pd.DataFrame(datos_iniciales)

# ==========================================
# MOTOR DE ANÁLISIS ESTADÍSTICO
# ==========================================
def ejecutar_motor_analisis(df_data):
    df_valido = df_data[df_data['Numero'].astype(str).isin(ANIMALES_MAP.keys())].copy()
    total_sorteos = len(df_valido)
    
    if total_sorteos == 0:
        return pd.DataFrame(), "0"
    
    stats = {}
    for num, nombre in ANIMALES_MAP.items():
        apariciones = df_valido[df_valido['Numero'] == num].index.tolist()
        freq = len(apariciones)
        
        if apariciones:
            atraso = total_sorteos - 1 - apariciones[-1]
        else:
            atraso = total_sorteos
            
        stats[num] = {
            "Animal": f"{num} - {nombre}",
            "Frecuencia": freq,
            "Atraso": atraso
        }
        
    df_stats = pd.DataFrame.from_dict(stats, orient='index')
    
    transiciones = {num: {n: 0 for n in ANIMALES_MAP.keys()} for num in ANIMALES_MAP.keys()}
    numeros_sucesion = df_valido['Numero'].tolist()
    for i in range(len(numeros_sucesion) - 1):
        actual = numeros_sucesion[i]
        siguiente = numeros_sucesion[i+1]
        transiciones[actual][siguiente] += 1
        
    ultimo_animal = numeros_sucesion[-1] if numeros_sucesion else "0"
    candidatos_jala = transiciones.get(ultimo_animal, {})
    df_stats['Jala_Score'] = df_stats.index.map(lambda x: candidatos_jala.get(x, 0))
    
    max_atraso = max(1, df_stats['Atraso'].max())
    max_jala = max(1, df_stats['Jala_Score'].max())
    
    df_stats['Score_Zona_Dulce'] = (
        (df_stats['Atraso'] / max_atraso) * 0.4 + 
        (df_stats['Jala_Score'] / max_jala) * 0.6
    ) * 100
    
    df_stats = df_stats.sort_values(by='Score_Zona_Dulce', ascending=False)
    return df_stats, ultimo_animal

# ==========================================
# INTERFAZ DE USUARIO (STREAMLIT)
# ==========================================
def main():
    st.title("🎡 Ruleta Royal Pro - Control Total")
    st.markdown("Motor estadístico con horarios exactos (8:30 AM a 8:30 PM) y 5 días de historial precargados.")

    st.sidebar.header("Opciones")
    if st.sidebar.button("🔄 Restablecer Historial Base"):
        del st.session_state['df_sorteos_royal']
        st.rerun()

    st.sidebar.success("✅ Historial y horarios oficiales activos.")

    st.subheader("📝 Tabla de Sorteos - Ruleta Royal")
    df_editado = st.data_editor(
        st.session_state['df_sorteos_royal'],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_sorteos_royal_tabla"
    )

    for idx, row in df_editado.iterrows():
        num_limpio = str(row['Numero']).strip()
        if num_limpio in ANIMALES_MAP:
            df_editado.at[idx, 'Animal'] = ANIMALES_MAP[num_limpio]
        else:
            df_editado.at[idx, 'Animal'] = ""

    st.session_state['df_sorteos_royal'] = df_editado

    df_analisis, ultimo_salido = ejecutar_motor_analisis(df_editado)

    st.markdown("---")
    col_u1, col_u2 = st.columns([1, 2])
    with col_u1:
        st.metric(label="Último Animal Royal", value=f"{ultimo_salido} - {ANIMALES_MAP.get(ultimo_salido, '')}")
    with col_u2:
        st.info(f"**💡 Análisis Activo:** Último animal: **{ultimo_salido} ({ANIMALES_MAP.get(ultimo_salido, '')})**. Monitoreando ciclos y rachas.")

    st.markdown("---")

    st.subheader("🎯 Top 3 Animalitos en 'Zona Dulce'")
    top_3 = df_analisis.head(3)
    c1, c2, c3 = st.columns(3)
    cols = [c1, c2, c3]
    
    for i, (idx, row) in enumerate(top_3.iterrows()):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"### #{i+1} - {row['Animal']}")
                st.markdown(f"**Puntuación:** {row['Score_Zona_Dulce']:.1f}%")
                st.markdown(f"📊 Frecuencia: {row['Frecuencia']} | ⏳ Atraso: {row['Atraso']}")

    st.markdown("---")

    st.subheader("🔥 Tripleta Fuerte Recomendada")
    top_nums = df_analisis.index.tolist()
    if len(top_nums) >= 3:
        tripleta_principal = f"{top_nums[0]} ({ANIMALES_MAP[top_nums[0]]}) - {top_nums[1]} ({ANIMALES_MAP[top_nums[1]]}) - {top_nums[2]} ({ANIMALES_MAP[top_nums[2]]})"
        st.success(f"✨ **Tripleta Ideal:** {tripleta_principal}")
    else:
        st.warning("Inserta más datos para calcular la tripleta.")

    st.markdown("---")

    st.subheader("🎲 Jugadas Individuales Directas")
    df_individuales = df_analisis[['Animal', 'Frecuencia', 'Atraso', 'Score_Zona_Dulce']].head(5)
    df_individuales.columns = ['Animalito', 'Freq.', 'Atraso', 'Score %']
    st.dataframe(df_individuales, use_container_width=True)

if __name__ == '__main__':
    main()
