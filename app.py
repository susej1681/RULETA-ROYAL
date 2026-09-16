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

@st.cache_data(ttl=120)
def cargar_historial_google_sheets():
    try:
        df_raw = pd.read_csv(GOOGLE_SHEET_URL, header=None)

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

        cols_con_fecha = {}
        for f in fechas_encontradas:
            col = f["col"]
            if col not in cols_con_fecha:
                cols_con_fecha[col] = f
            else:
                if f["fecha_dt"] > cols_con_fecha[col]["fecha_dt"]:
                    cols_con_fecha[col] = f

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


def aprender_jales(df, max_atraso=3):
    jales = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums = df["numero"].tolist()
    for i in range(len(nums) - 1):
        origen = nums[i]
        for j in range(i + 1, min(i + 1 + max_atraso, len(nums))):
            jales[origen][nums[j]] += 1
    return jales


def detectar_alineaciones(df, min_repeticiones=2):
    nums = df["numero"].tolist()
    total = len(nums)
    alineaciones = []

    for i in range(total - 10):
        ventana = nums[i:i + 5]
        unicos = list(dict.fromkeys(ventana))
        for a in range(len(unicos)):
            for b in range(a + 1, len(unicos)):
                par = tuple(sorted([unicos[a], unicos[b]]))
                alineaciones.append(par)

    conteo_parejas = Counter(alineaciones)
    parejas_top = [p for p, c in conteo_parejas.most_common(5) if c >= min_repeticiones]

    resultado = []
    for par in parejas_top:
        posiciones = []
        for i in range(total - 5):
            ventana = set(nums[i:i + 5])
            if par[0] in ventana and par[1] in ventana:
                posiciones.append(i)
        if len(posiciones) >= 2:
            ultima = posiciones[-1]
            atraso = total - 1 - ultima
            diffs = [posiciones[k + 1] - posiciones[k] for k in range(len(posiciones) - 1)]
            promedio = sum(diffs) / len(diffs) if diffs else 0
            if promedio > 0 and atraso >= promedio * 0.6:
                resultado.append({
                    "par": par,
                    "veces": len(posiciones),
                    "atraso": atraso,
                    "promedio": round(promedio, 1)
                })

    return resultado


def motor_casi_adivino(df):
    if df.empty or len(df) < 20:
        return {}, {}, None, [], []

    df_ventana = df.tail(VENTANA_SORTEOS).copy()
    freq_ventana = Counter(df_ventana["numero"].tolist())
    freq_rec20 = Counter(df.tail(20)["numero"].tolist())
    freq_rec30 = Counter(df.tail(30)["numero"].tolist())

    atrasos = {}
    total = len(df)
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        atrasos[num] = total - 1 - idxs[-1] if idxs else total

    jales_aprendidos = aprender_jales(df, max_atraso=3)

    ultimos_10 = df.tail(10)["numero"].tolist()
    jales_entrantes = Counter()
    for nr in ultimos_10:
        for siguiente, c in jales_aprendidos.get(nr, Counter()).most_common(3):
            jales_entrantes[siguiente] += c

    max_fv = max(freq_ventana.values()) if freq_ventana else 1
    max_f20 = max(freq_rec20.values()) if freq_rec20 else 1
    max_atr = max(atrasos.values()) if atrasos else 1
    max_jal = max(jales_entrantes.values()) if jales_entrantes else 1

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
    alineaciones = detectar_alineaciones(df, min_repeticiones=2)

    return scores, detalles, top_ordenado, jales_aprendidos, alineaciones


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
    st.caption("Casi Adivino · Ventana 65 sorteos · Tripleta 11 sorteos · Jales aprendidos")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja de cálculo..."):
        df = cargar_historial_google_sheets()

    if df.empty:
        st.error("No se pudieron cargar datos. Verifica que la hoja sea pública.")
        return

    scores, detalles, top_ordenado, jales_aprendidos, alineaciones = motor_casi_adivino(df)
    if not top_ordenado:
        st.warning("Datos insuficientes.")
        return

    individual, top3, tripleta = armar_resultados(scores, detalles, top_ordenado)
    ultimo = df.iloc[-1]

    if alineaciones:
        st.markdown("### 🔗 Alineación Caliente Detectada")
        for al in alineaciones[:3]:
            a, b = al["par"]
            st.markdown(f"**{a:02d} {ANIMALITOS_DICT[a]} + {b:02d} {ANIMALITOS_DICT[b]}**")
            st.caption(f"Se han alineado {al['veces']} veces · Promedio cada {al['promedio']} sorteos · Atraso: {al['atraso']}")
        st.markdown("---")

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

    st.markdown("### 🔗 Jales Aprendidos (Top 3 del último resultado)")
    ultimo_num = int(ultimo["numero"])
    jales_ult = jales_aprendidos.get(ultimo_num, Counter())
    if jales_ult:
        for jale, c in jales_ult.most_common(3):
            st.write(f"- Después de **{ultimo['numero']} {ultimo['nombre']}** → **{jale:02d} {ANIMALITOS_DICT[jale]}** ({c} veces)")
    else:
        st.caption("Sin datos suficientes.")

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
