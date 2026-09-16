import streamlit as st
import pandas as pd
import re
from collections import Counter

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Ruleta Royal - Casi Adivino",
    page_icon="👑",
    layout="centered"
)

GOOGLE_SHEET_ID = "1ZQuqWAsZ2odO7VPppTOB8BhNWg6ktDr8LPGMdEFElrg"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

SORTEOS_POR_DIA = 13
DIAS_VENTANA = 5
VENTANA_SORTEOS = SORTEOS_POR_DIA * DIAS_VENTANA  # 65 sorteos

ANIMALITOS_DICT = {
    0: "Tiburón", 1: "Carnero", 2: "Toro", 3: "Ciempiés", 4: "Alacrán",
    5: "León", 6: "Rana", 7: "Perico", 8: "Ratón", 9: "Águila",
    10: "Tigre", 11: "Gato", 12: "Caballo", 13: "Mono", 14: "Paloma",
    15: "Zorro", 16: "Oso", 17: "Pavo", 18: "Burro", 19: "Chivo",
    20: "Cochino", 21: "Gallo", 22: "Camello", 23: "Cebra", 24: "Iguana",
    25: "Gallina", 26: "Vaca", 27: "Perro", 28: "Zamuro", 29: "Elefante",
    30: "Caimán", 31: "Lapa", 32: "Ardilla", 33: "Pescado", 34: "Venado",
    35: "Pantera", 36: "Culebra"
}

TABLA_JALES_BASE = {
    0: [10, 16, 28], 1: [2, 12], 2: [1, 22], 3: [14, 25], 4: [9, 15],
    5: [11, 21], 6: [8, 17], 7: [27, 32], 8: [6, 18], 9: [4, 29],
    10: [0, 16], 11: [5, 19], 12: [1, 26], 13: [20, 28], 14: [3, 21],
    15: [4, 34], 16: [0, 27], 17: [6, 30], 18: [8, 13], 19: [11, 28],
    20: [13, 32], 21: [5, 14], 22: [2, 23], 23: [22, 36], 24: [31, 34],
    25: [3, 12], 26: [12, 29], 27: [7, 16], 28: [0, 19], 29: [9, 26],
    30: [17, 33], 31: [24, 35], 32: [7, 20], 33: [30, 36], 34: [15, 24],
    35: [0, 5, 36], 36: [23, 33]
}

# ============================================================
# CARGA AUTOMÁTICA DESDE GOOGLE SHEETS
# ============================================================
@st.cache_data(ttl=120)
def cargar_historial_google_sheets():
    try:
        df_raw = pd.read_csv(GOOGLE_SHEET_URL)
        date_cols = [col for col in df_raw.columns if '/' in str(col)]
        hora_col = df_raw.columns[0]

        registros = []
        for _, row in df_raw.iterrows():
            sorteo_hora = str(row[hora_col]).strip()
            if not sorteo_hora or 'Hora' in sorteo_hora or sorteo_hora.lower() == 'nan':
                continue

            for fecha in date_cols:
                val = row[fecha]
                if pd.isna(val) or str(val).strip() == "" or str(val).startswith("-"):
                    continue

                match = re.search(r'\((\d+)\)', str(val))
                if match:
                    num = int(match.group(1))
                    nombre = ANIMALITOS_DICT.get(num, re.sub(r'\s*\(\d+\)', '', str(val)).strip())
                    registros.append({
                        "fecha": str(fecha).strip(),
                        "sorteo": sorteo_hora,
                        "numero": num,
                        "nombre": nombre
                    })

        df = pd.DataFrame(registros)
        if not df.empty:
            df = df.reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame(columns=["fecha", "sorteo", "numero", "nombre"])


# ============================================================
# MOTOR CASI ADIVINO — DINÁMICO CON RESCATE
# ============================================================
def motor_casi_adivino(df):
    if df.empty or len(df) < 20:
        return [], {}, None

    # Ventana corrediza de 65 sorteos (5 días × 13)
    df_ventana = df.tail(VENTANA_SORTEOS).copy()

    # Frecuencias en distintas ventanas
    freq_ventana = Counter(df_ventana["numero"].tolist())
    freq_rec20 = Counter(df.tail(20)["numero"].tolist())
    freq_rec30 = Counter(df.tail(30)["numero"].tolist())

    # Atraso real = sorteos desde la última aparición
    atrasos = {}
    total = len(df)
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        if idxs:
            atrasos[num] = total - 1 - idxs[-1]
        else:
            atrasos[num] = total

    # Jales aprendidos del historial real
    jales_aprendidos = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums_lista = df["numero"].tolist()
    for i in range(len(nums_lista) - 1):
        actual = nums_lista[i]
        siguiente = nums_lista[i + 1]
        if actual in jales_aprendidos:
            jales_aprendidos[actual][siguiente] += 1

    # Jales entrantes: cuántos números recientes lo jalan
    ultimos_10 = df.tail(10)["numero"].tolist()
    jales_entrantes = Counter()
    for num_reciente in ultimos_10:
        for posible_jale in TABLA_JALES_BASE.get(num_reciente, []):
            jales_entrantes[posible_jale] += 1

    # Normalizadores
    max_freq_v = max(freq_ventana.values()) if freq_ventana else 1
    max_freq_20 = max(freq_rec20.values()) if freq_rec20 else 1
    max_atraso = max(atrasos.values()) if atrasos else 1
    max_jales = max(jales_entrantes.values()) if jales_entrantes else 1

    scores = {}
    detalles = {}

    for num in ANIMALITOS_DICT.keys():
        f_v = freq_ventana.get(num, 0)
        f_20 = freq_rec20.get(num, 0)
        f_30 = freq_rec30.get(num, 0)
        atr = atrasos.get(num, 0)
        jales_in = jales_entrantes.get(num, 0)

        # Normalizar a escala 0-1
        n_fv = f_v / max_freq_v if max_freq_v else 0
        n_f20 = f_20 / max_freq_20 if max_freq_20 else 0
        n_atr = atr / max_atraso if max_atraso else 0
        n_jal = jales_in / max_jales if max_jales else 0

        # Bonus caliente (salió 2+ veces en últimos 30)
        bonus = 0.05 if f_30 >= 2 else 0

        # Score ponderado
        score = (
            n_fv * 0.30 +      # Frecuencia en ventana 65
            n_f20 * 0.25 +     # Frecuencia reciente (últimos 20)
            n_atr * 0.25 +     # Atraso real
            n_jal * 0.15 +     # Jales entrantes
            bonus              # Bonus caliente
        )

        # PENALIZACIÓN: sin frecuencia en ventana = castigo
        if f_v == 0:
            score *= 0.5

        scores[num] = round(score * 100, 2)
        detalles[num] = {
            "freq_ventana": f_v,
            "freq_20": f_20,
            "atraso": atr,
            "jales_entrantes": jales_in,
            "bonus_caliente": bonus > 0
        }

    # RESCATE: fuera de ventana + atraso alto + jalado por recientes
    nums_en_ventana = set(df_ventana["numero"].tolist())
    rescatados = []
    for num in ANIMALITOS_DICT.keys():
        if num not in nums_en_ventana and atrasos[num] > 20:
            if jales_entrantes.get(num, 0) >= 1:
                scores[num] = max(scores.get(num, 0), 55.0)
                rescatados.append(num)

    # Top 3
    top_3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]

    resultado = []
    for num, score in top_3:
        resultado.append({
            "numero": f"{num:02d}",
            "int_num": num,
            "nombre": ANIMALITOS_DICT[num],
            "score": score,
            "detalle": detalles[num],
            "rescatado": num in rescatados
        })

    ultimo = df.iloc[-1].to_dict() if not df.empty else None
    return resultado, jales_aprendidos, ultimo


# ============================================================
# JALES COMBINADOS (BASE + APRENDIDOS)
# ============================================================
def calcular_jales(top_3, jales_aprendidos):
    sugerencias = []
    for item in top_3:
        num = item["int_num"]
        base = set(TABLA_JALES_BASE.get(num, []))
        aprendidos = jales_aprendidos.get(num, Counter())
        top_aprendidos = set([n for n, c in aprendidos.most_common(3) if c >= 2])
        combinados = base | top_aprendidos
        for j in sorted(combinados):
            sugerencias.append({
                "origen": f"[{item['numero']}] {item['nombre']}",
                "jale_num": f"{j:02d}",
                "jale_nombre": ANIMALITOS_DICT.get(j, ""),
                "es_aprendido": j in top_aprendidos and j not in base
            })
    return sugerencias


# ============================================================
# INTERFAZ PRINCIPAL
# ============================================================
def main():
    st.title("👑 Ruleta Royal Pro")
    st.caption("Motor Casi Adivino dinámico · Ventana 65 sorteos · Auto-sync Google Sheets")

    col_a, col_b = st.columns([3, 1])
    with col_b:
        if st.button("🔄 Recargar"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Sincronizando historial desde Google Sheets..."):
        df = cargar_historial_google_sheets()

    if df.empty:
        st.error("No se pudieron cargar datos. Verifica que el Google Sheet sea público.")
        return

    top3, jales_aprendidos, ultimo = motor_casi_adivino(df)

    tab1, tab2, tab3 = st.tabs(["🎯 Zona Dulce & Jales", "📊 Historial", "ℹ️ Info"])

    with tab1:
        if ultimo:
            st.markdown("### 🎯 Último Animal Royal")
            st.markdown(f"## {ultimo['numero']:02d} - {ultimo['nombre']}")
            st.info(f"Fecha: {ultimo['fecha']} · Hora: {ultimo['sorteo']}")

        st.markdown("---")
        st.markdown("### 🔥 Top 3 - Zona Dulce")

        for i, item in enumerate(top3, 1):
            d = item["detalle"]
            marca_rescate = " 🚨 RESCATADO" if item["rescatado"] else ""
            st.markdown(f"#### #{i} - {item['numero']} {item['nombre']}{marca_rescate}")
            st.markdown(f"**Puntuación: {item['score']}%**")
            st.markdown(
                f"Freq(65): {d['freq_ventana']} | "
                f"Freq(20): {d['freq_20']} | "
                f"Atraso: {d['atraso']} | "
                f"Jales in: {d['jales_entrantes']}"
                + (" | 🔥 Caliente" if d["bonus_caliente"] else "")
            )
            st.markdown("")

        if len(top3) >= 3:
            st.markdown("---")
            st.markdown("### ✨ Tripleta Ideal")
            tripleta = " - ".join([f"{i['numero']} {i['nombre']}" for i in top3])
            st.success(tripleta)

        st.markdown("---")
        st.markdown("### 🔗 Jales Recomendados")
        jales = calcular_jales(top3, jales_aprendidos)
        for j in jales:
            marca = " ⭐ (aprendido)" if j["es_aprendido"] else ""
            st.write(f"- **{j['origen']}** → **[{j['jale_num']}] {j['jale_nombre']}**{marca}")

    with tab2:
        st.subheader("📋 Historial Sincronizado")
        st.write(f"Total de sorteos cargados: {len(df)}")
        st.dataframe(df.tail(100), use_container_width=True)

    with tab3:
        st.subheader("ℹ️ Cómo funciona el motor")
        st.markdown("""
        **Ventana dinámica:** analiza los últimos 65 sorteos (5 días × 13 sorteos).
        
        **Score explicable, 5 componentes:**
        - Frecuencia en ventana 65 (peso 30%)
        - Frecuencia reciente últimos 20 (peso 25%)
        - Atraso real (peso 25%)
        - Jales entrantes de recientes (peso 15%)
        - Bonus caliente si salió 2+ en últimos 30 (5%)
        
        **Penalización:** si un animalito no ha salido en la ventana, su score se divide a la mitad.
        
        **Rescate:** si un animalito fuera de la ventana tiene atraso > 20 y es jalado por algún reciente, entra con boost de 55%.
        
        **Jales:** se combinan la tabla base + los aprendidos del historial real.
        """)


if __name__ == "__main__":
    main()
