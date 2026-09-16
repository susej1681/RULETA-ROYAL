import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Ruleta Royal - Casi Adivino",
    page_icon="👑",
    layout="centered"
)

GOOGLE_SHEET_ID = "1ZQuqWAsZ2odO7VPppTOB8BhNWg6ktDr8LPGMdEFElrg"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

SORTEOS_POR_DIA = 13
DIAS_VENTANA = 5
VENTANA_SORTEOS = SORTEOS_POR_DIA * DIAS_VENTANA

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

@st.cache_data(ttl=120)
def cargar_historial_google_sheets():
    try:
        df_raw = pd.read_csv(GOOGLE_SHEET_URL, header=None)

        # Encontrar todas las fechas válidas en cualquier celda
        fechas_encontradas = []
        for col in df_raw.columns:
            for fila in range(len(df_raw)):
                val = str(df_raw.iloc[fila, col]).strip()
                if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val):
                    try:
                        fecha_dt = pd.to_datetime(val, format="%d/%m/%Y", errors="coerce")
                        if pd.notna(fecha_dt):
                            fechas_encontradas.append({
                                "col": col,
                                "fila": fila,
                                "fecha_str": fecha_dt.strftime("%d/%m/%Y"),
                                "fecha_dt": fecha_dt
                            })
                    except:
                        pass

        if not fechas_encontradas:
            return pd.DataFrame(columns=["fecha", "numero", "nombre"])

        # Agrupar por columna: nos quedamos con la fecha MÁS RECIENTE de cada columna
        cols_con_fecha = {}
        for f in fechas_encontradas:
            col = f["col"]
            if col not in cols_con_fecha:
                cols_con_fecha[col] = f
            else:
                if f["fecha_dt"] > cols_con_fecha[col]["fecha_dt"]:
                    cols_con_fecha[col] = f

        # Ordenar columnas por fecha real
        cols_ordenadas = sorted(cols_con_fecha.items(), key=lambda x: x[1]["fecha_dt"])

        registros = []
        for col, info in cols_ordenadas:
            fecha = info["fecha_str"]
            fila_ini = info["fila"] + 1
            for fila in range(fila_ini, len(df_raw)):
                val = str(df_raw.iloc[fila, col]).strip()
                if not val or val.lower() == "nan":
                    continue
                match = re.search(r'\((\d+)\)', val)
                if match:
                    num = int(match.group(1))
                    nombre = ANIMALITOS_DICT.get(num, re.sub(r'\s*\(\d+\)', '', val).strip())
                    registros.append({
                        "fecha": fecha,
                        "numero": num,
                        "nombre": nombre
                    })

        df = pd.DataFrame(registros)
        if not df.empty:
            df["fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
            df = df.sort_values(["fecha_dt"]).reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Error al leer Google Sheet: {e}")
        return pd.DataFrame(columns=["fecha", "numero", "nombre"])


def motor_casi_adivino(df):
    if df.empty or len(df) < 20:
        return {}, {}, None, []

    df_ventana = df.tail(VENTANA_SORTEOS).copy()
    freq_ventana = Counter(df_ventana["numero"].tolist())
    freq_rec20 = Counter(df.tail(20)["numero"].tolist())
    freq_rec30 = Counter(df.tail(30)["numero"].tolist())

    atrasos = {}
    total = len(df)
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        atrasos[num] = total - 1 - idxs[-1] if idxs else total

    jales_aprendidos = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums_lista = df["numero"].tolist()
    for i in range(len(nums_lista) - 1):
        jales_aprendidos[nums_lista[i]][nums_lista[i + 1]] += 1

    ultimos_10 = df.tail(10)["numero"].tolist()
    jales_entrantes = Counter()
    for nr in ultimos_10:
        for pj in TABLA_JALES_BASE.get(nr, []):
            jales_entrantes[pj] += 1

    max_fv = max(freq_ventana.values()) if freq_ventana else 1
    max_f20 = max(freq_rec20.values()) if freq_rec20 else 1
    max_atr = max(atrasos.values()) if atrasos else 1
    max_jal = max(jales_entrantes.values()) if jales_entrantes else 1

    # Detectar repetidores: animales que salieron ayer y hoy
    fechas_unicas = df["fecha"].unique().tolist()
    ayer_nums = set()
    if len(fechas_unicas) >= 2:
        fecha_ayer = fechas_unicas[-2]
        ayer_nums = set(df[df["fecha"] == fecha_ayer]["numero"].tolist())

    scores = {}
    detalles = {}

    for num in ANIMALITOS_DICT.keys():
        fv = freq_ventana.get(num, 0)
        f20 = freq_rec20.get(num, 0)
        f30 = freq_rec30.get(num, 0)
        atr = atrasos.get(num, 0)
        jal = jales_entrantes.get(num, 0)

        n_fv = fv / max_fv if max_fv else 0
        n_f20 = f20 / max_f20 if max_f20 else 0
        n_atr = atr / max_atr if max_atr else 0
        n_jal = jal / max_jal if max_jal else 0

        bonus_caliente = 0.08 if f30 >= 3 else (0.04 if f30 == 2 else 0)
        penal_frio = 0
        if atr > 60:
            penal_frio = -0.35
        elif atr > 45:
            penal_frio = -0.20
        elif atr > 30:
            penal_frio = -0.10

        score = (
            n_fv * 0.25 +
            n_f20 * 0.25 +
            n_atr * 0.20 +
            n_jal * 0.15 +
            bonus_caliente +
            penal_frio
        )

        if fv == 0:
            score *= 0.4

        scores[num] = round(max(score, 0) * 100, 2)
        detalles[num] = {
            "freq_ventana": fv,
            "freq_20": f20,
            "atraso": atr,
            "jales_in": jal,
            "caliente": bonus_caliente > 0,
            "repetidor": num in ayer_nums,
            "penal": penal_frio < 0
        }

    top_ordenado = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return scores, detalles, top_ordenado, df


def armar_resultados(scores, detalles, top_ordenado):
    top3 = []
    for num, sc in top_ordenado[:3]:
        top3.append({
            "numero": f"{num:02d}",
            "int_num": num,
            "nombre": ANIMALITOS_DICT[num],
            "score": sc,
            "detalle": detalles[num]
        })

    individual = top3[0] if top3 else None

    candidatos_tripleta = [num for num, sc in top_ordenado if sc > 0][:15]
    tripleta_nums = candidatos_tripleta[:3]

    tripleta = []
    for num in tripleta_nums:
        tripleta.append({
            "numero": f"{num:02d}",
            "int_num": num,
            "nombre": ANIMALITOS_DICT[num],
            "score": scores[num],
            "detalle": detalles[num]
        })

    return individual, top3, tripleta


def main():
    st.title("👑 Ruleta Royal Pro")
    st.caption("Casi Adivino · Ventana 65 sorteos · Tripleta 11 sorteos")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja de cálculo..."):
        df = cargar_historial_google_sheets()

    if df.empty:
        st.error("No se pudieron cargar datos. Verifica que la hoja sea pública.")
        return

    scores, detalles, top_ordenado, df = motor_casi_adivino(df)
    if not top_ordenado:
        st.warning("Datos insuficientes.")
        return

    individual, top3, tripleta = armar_resultados(scores, detalles, top_ordenado)
    ultimo = df.iloc[-1]

    st.markdown("### 🎯 Último resultado")
    st.markdown(f"## {ultimo['numero']:02d} - {ultimo['nombre']}")
    st.caption(f"Fecha: {ultimo['fecha']}")

    st.markdown("---")

    if individual:
        st.markdown("### 🎯 Animal Individual (el más fuerte)")
        d = individual["detalle"]
        st.markdown(f"## {individual['numero']} - {individual['nombre']}")
        st.markdown(f"**Score: {individual['score']}%**")
        marcas = []
        if d["caliente"]: marcas.append("🔥 Caliente")
        if d["repetidor"]: marcas.append("🔁 Repetidor de ayer")
        if d["penal"]: marcas.append("⚠️ Enjaulado")
        if marcas:
            st.markdown(" · ".join(marcas))
        st.caption(f"Freq(65): {d['freq_ventana']} | Freq(20): {d['freq_20']} | Atraso: {d['atraso']} | Jales: {d['jales_in']}")

    st.markdown("---")

    st.markdown("### 🏆 Top 3")
    for i, item in enumerate(top3, 1):
        d = item["detalle"]
        marcas = []
        if d["caliente"]: marcas.append("🔥")
        if d["repetidor"]: marcas.append("🔁")
        if d["penal"]: marcas.append("⚠️")
        st.markdown(f"**#{i} - {item['numero']} {item['nombre']}** — {item['score']}% {' '.join(marcas)}")
        st.caption(f"Freq(65): {d['freq_ventana']} | Freq(20): {d['freq_20']} | Atraso: {d['atraso']} | Jales: {d['jales_in']}")

    st.markdown("---")

    st.markdown("### ✨ Tripleta (cubre 11 sorteos)")
    if len(tripleta) >= 3:
        linea = " - ".join([f"{t['numero']} {t['nombre']}" for t in tripleta])
        st.success(linea)
        st.caption("Juega estos 3. Si los 3 salen en los próximos 11 sorteos, ganaste.")
        for t in tripleta:
            d = t["detalle"]
            marcas = []
            if d["caliente"]: marcas.append("🔥")
            if d["repetidor"]: marcas.append("🔁 Repetidor de ayer")
            st.write(f"- **{t['numero']} {t['nombre']}** ({t['score']}%) {' '.join(marcas)}")

    st.markdown("---")

    st.markdown("### 🔁 Observación: Repetidores de ayer")
    repetidores_hoy = [n for n in detalles if detalles[n]["repetidor"]]
    if repetidores_hoy:
        for num in repetidores_hoy[:10]:
            st.write(f"- {num:02d} - {ANIMALITOS_DICT[num]}")
    else:
        st.caption("Ninguno todavía.")

    with st.expander("📋 Ver últimos 30 sorteos"):
        st.dataframe(df.tail(30)[["fecha", "numero", "nombre"]], use_container_width=True)


if __name__ == "__main__":
    main()
