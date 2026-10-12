import streamlit as st
import pandas as pd
import re
from collections import Counter
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Ruleta Repetidor",
    page_icon="🔁",
    layout="centered"
)

GOOGLE_SHEET_ID = "1ZQuqWAsZ2odO7VPppTOB8BhNWg6ktDr8LPGMdEFElrg"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

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

DIAS = {0: "LUNES", 1: "MARTES", 2: "MIÉRCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SÁBADO", 6: "DOMINGO"}


def ahora_venezuela():
    return datetime.utcnow() - timedelta(hours=4)


def fmt_num(n):
    if n == 0: return "0"
    return f"{n:02d}"


def extraer_hora(hora_str):
    m = re.match(r'^(\d+):(\d+)\s*(AM|PM)$', str(hora_str).strip().upper())
    if not m: return 99
    h = int(m.group(1))
    suf = m.group(3)
    if suf == "AM":
        if h == 12: h = 0
    else:
        if h != 12: h += 12
    return h


def formatear_hora(hora_num):
    if hora_num == 0: return "12:00 AM"
    if hora_num < 12: return f"{hora_num:02d}:00 AM"
    if hora_num == 12: return "12:00 PM"
    return f"{hora_num-12:02d}:00 PM"


@st.cache_data(ttl=120)
def cargar_historial():
    try:
        df_raw = pd.read_csv(GOOGLE_SHEET_URL, header=None)
        filas_enc = []
        for fila in range(len(df_raw)):
            val = str(df_raw.iloc[fila, 0]).strip().lower()
            if val == "hora":
                filas_enc.append(fila)
        registros = []
        for idx, fe in enumerate(filas_enc):
            ff = filas_enc[idx + 1] if idx + 1 < len(filas_enc) else len(df_raw)
            fechas_col = {}
            for col in range(1, len(df_raw.columns)):
                val = str(df_raw.iloc[fe, col]).strip()
                if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val):
                    try:
                        fd = pd.to_datetime(val, format="%d/%m/%Y", errors="coerce")
                        if pd.notna(fd):
                            fechas_col[col] = fd
                    except: pass
            ffd = min(ff, fe + 14)
            for col, fd in fechas_col.items():
                for fila in range(fe + 1, ffd):
                    hv = str(df_raw.iloc[fila, 0]).strip()
                    val = str(df_raw.iloc[fila, col]).strip()
                    if not val or val.lower() == "nan" or val.lower() == "hora":
                        continue
                    m = re.search(r'\((\d+)\)', val)
                    if m:
                        ns = m.group(1)
                        n = int(ns)
                        hora_n = extraer_hora(hv)
                        registros.append({
                            "fecha_dt": fd,
                            "fecha": fd.strftime("%d/%m/%Y"),
                            "hora_num": hora_n,
                            "hora_str": hv,
                            "numero": n,
                            "nombre": ANIMALITOS_DICT.get(n, val)
                        })
        df = pd.DataFrame(registros)
        if not df.empty:
            df = df.sort_values(["fecha_dt", "hora_num"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["fecha", "numero", "nombre"])


def analizar_3_dias(df):
    """Analiza los últimos 3 días completos."""
    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    if len(fechas_unicas) < 3:
        return None, None, None, None

    # Últimos 3 días completos (excluye hoy si está parcial)
    hoy_real = ahora_venezuela().date()
    fechas_completas = [f for f in fechas_unicas if pd.Timestamp(f).date() < hoy_real]

    if len(fechas_completas) >= 3:
        ultimos_3 = fechas_completas[-3:]
    else:
        ultimos_3 = fechas_unicas[-3:]

    dias_dict = {}
    for fecha in ultimos_3:
        df_dia = df[df["fecha_dt"] == fecha]
        dias_dict[fecha] = set(df_dia["numero"].tolist())

    return ultimos_3, dias_dict, fechas_completas, hoy_real


def clasificar_animalitos(df, ultimos_3, dias_dict):
    """Clasifica en: 3 días, 2 días, 1 día."""
    if not ultimos_3:
        return [], [], []

    todos = set()
    for dia in dias_dict.values():
        todos.update(dia)

    repetidores_3 = []
    repetidores_2 = []
    repetidores_1 = []

    for num in todos:
        dias_aparece = [i for i, f in enumerate(ultimos_3) if num in dias_dict[f]]
        total_dias = len(dias_aparece)

        if total_dias == 3:
            repetidores_3.append(num)
        elif total_dias == 2:
            repetidores_2.append(num)
        else:
            repetidores_1.append(num)

    return repetidores_3, repetidores_2, repetidores_1


def calcular_cadencia(df, num, dias_semana=15):
    """Calcula cada cuántos días aparece un animalito."""
    nums = df["numero"].tolist()
    fechas = df["fecha"].tolist()

    # Posiciones del animalito
    posiciones_dias = []
    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    fechas_recientes = fechas_unicas[-dias_semana:] if len(fechas_unicas) >= dias_semana else fechas_unicas

    posiciones = []
    for i, f in enumerate(fechas_recientes):
        df_dia = df[df["fecha_dt"] == f]
        if num in df_dia["numero"].tolist():
            posiciones.append(i)

    if len(posiciones) < 2:
        return 999

    diffs = [posiciones[k + 1] - posiciones[k] for k in range(len(posiciones) - 1)]
    return round(sum(diffs) / len(diffs), 1)


def calcular_propensos(df, repetidores_2, ultimos_3, dias_dict):
    """Los que salieron los últimos 2 días (en racha)."""
    if not ultimos_3 or len(ultimos_3) < 2:
        return []

    ultimo = ultimos_3[-1]
    penultimo = ultimos_3[-2]

    propensos = []
    for num in repetidores_2:
        if num in dias_dict.get(ultimo, set()) and num in dias_dict.get(penultimo, set()):
            propensos.append(num)
    return propensos


def armar_tripletas(df, ultimos_3, dias_dict):
    """Arma 2 tripletas."""
    rep3, rep2, rep1 = clasificar_animalitos(df, ultimos_3, dias_dict)

    # Ordenar rep2 y rep1 por cadencia (los que están "más cerca" de salir)
    rep2_sorted = sorted(rep2, key=lambda n: calcular_cadencia(df, n))
    rep1_sorted = sorted(rep1, key=lambda n: calcular_cadencia(df, n))

    # TRIPLETA 1: los 3 más repetidores
    trip1 = []
    if len(rep3) >= 3:
        trip1 = rep3[:3]
    elif len(rep3) + len(rep2_sorted) >= 3:
        trip1 = rep3 + rep2_sorted[:3 - len(rep3)]
    elif len(rep3) + len(rep2_sorted) + len(rep1_sorted) >= 3:
        trip1 = rep3 + rep2_sorted + rep1_sorted[:3 - len(rep3) - len(rep2_sorted)]

    # TRIPLETA 2: mezcla inteligente
    trip2 = []
    # 1 de los repetidores puros (3 días)
    if rep3:
        trip2.append(rep3[0])
    # 1 en racha (últimos 2 días)
    propensos = calcular_propensos(df, rep2, ultimos_3, dias_dict)
    for p in propensos:
        if p not in trip2:
            trip2.append(p)
            break
    # 1 por cadencia (o el siguiente repetidor)
    for r in rep2_sorted:
        if r not in trip2:
            trip2.append(r)
            break
    if len(trip2) < 3:
        for r in rep1_sorted:
            if r not in trip2:
                trip2.append(r)
                break

    return trip1[:3], trip2[:3], rep3, rep2, rep1


def calcular_favorito(df, ultimos_3, dias_dict, trip1):
    """El favorito del día: el más repetidor + con mejor cadencia."""
    if not trip1:
        return None
    # El primero de la tripleta 1 = el más fuerte
    return trip1[0]


def main():
    st.title("🔁 Ruleta Repetidor")
    st.caption("3 días · 2 tripletas · Favorito del día · Ruleta Royal")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja de Ruleta Royal..."):
        df = cargar_historial()

    if df.empty:
        st.error("No se pudieron cargar datos.")
        return

    ahora = ahora_venezuela()
    st.caption(f"📊 Data: {len(df)} sorteos · 🕐 {ahora.strftime('%H:%M')} Venezuela")

    # ÚLTIMO RESULTADO
    ultimo = df.iloc[-1]
    st.markdown("## 🎯 ÚLTIMO RESULTADO")
    st.markdown(f"# {fmt_num(int(ultimo['numero']))} - {ultimo['nombre']}")
    st.caption(f"📅 {ultimo['fecha']} · 🕐 {ultimo['hora_str']}")

    st.markdown("---")

    # ANALIZAR 3 DÍAS
    ultimos_3, dias_dict, fechas_completas, hoy_real = analizar_3_dias(df)

    if not ultimos_3:
        st.warning("⚠️ Necesitas al menos 3 días de data. Espera mañana.")
        return

    st.markdown("## 📊 ANÁLISIS DE LOS ÚLTIMOS 3 DÍAS")

    nombres_dias = []
    for f in ultimos_3:
        d = pd.Timestamp(f).date()
        nombres_dias.append(f"{DIAS[d.weekday()]} {d.strftime('%d/%m')}")

    st.markdown(f"Analizando: **{' · '.join(nombres_dias)}**")

    rep3, rep2, rep1 = clasificar_animalitos(df, ultimos_3, dias_dict)

    # Tabla
    st.markdown("### 📋 Tabla de apariciones")
    st.markdown(f"| Animalito | {nombres_dias[0][:5]} | {nombres_dias[1][:5]} | {nombres_dias[2][:5]} | Total |")
    st.markdown("|---|---|---|---|---|")

    todos = sorted(set(rep3 + rep2 + rep1))
    for num in todos:
        fila = f"| {fmt_num(num)} {ANIMALITOS_DICT[num]} |"
        for f in ultimos_3:
            fila += f" {'✅' if num in dias_dict[f] else '❌'} |"
        total = sum(1 for f in ultimos_3 if num in dias_dict[f])
        fila += f" {total} |"
        st.markdown(fila)

    st.markdown("---")

    # TRIPLETAS
    trip1, trip2, r3, r2, r1 = armar_tripletas(df, ultimos_3, dias_dict)

    st.markdown("## 🎯 TRIPLETAS PARA JUGAR")

    if len(trip1) >= 3:
        st.markdown("### 🎯 TRIPLETA 1 (Los más repetidores)")
        st.success(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip1]))
        for n in trip1:
            dias_ap = sum(1 for f in ultimos_3 if n in dias_dict[f])
            st.caption(f"• {fmt_num(n)} {ANIMALITOS_DICT[n]} → apareció {dias_ap} de 3 días")

    if len(trip2) >= 3:
        st.markdown("### ⚡ TRIPLETA 2 (Mezcla inteligente)")
        st.info(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip2]))
        for n in trip2:
            dias_ap = sum(1 for f in ultimos_3 if n in dias_dict[f])
            st.caption(f"• {fmt_num(n)} {ANIMALITOS_DICT[n]} → apareció {dias_ap} de 3 días")

    st.markdown("---")

    # FAVORITO DEL DÍA
    favorito = calcular_favorito(df, ultimos_3, dias_dict, trip1)
    if favorito is not None:
        st.markdown("## 🔥 FAVORITO DEL DÍA")
        st.success(f"# {fmt_num(favorito)} {ANIMALITOS_DICT[favorito]}")
        dias_ap = sum(1 for f in ultimos_3 if favorito in dias_dict[f])
        cad = calcular_cadencia(df, favorito)
        st.caption(f"Apareció {dias_ap}/3 días · Cadencia: cada {cad} días")

    st.markdown("---")

    # SUGERENCIA
    st.markdown("## 💡 SUGERENCIA DE JUEGO")
    st.markdown(f"""
    **Hoy lunes → observa los sistemas**
    **Empieza a jugar cuando tengas 3-4 días de data**

    Si vas a jugar:
    - 🎯 **Tripleta 1** → 100 Bs
    - ⚡ **Tripleta 2** → 100 Bs
    - 🔥 **Favorito** → 100 Bs individual

    **Total: 300 Bs**

    **Recuerda:** Ruleta Royal repite 4-6 del día anterior.
    """)

    st.markdown("---")

    # VISTA DE LOS ÚLTIMOS 3 DÍAS
    st.markdown("## 📅 VISTA DÍA POR DÍA")

    for f in ultimos_3:
        d = pd.Timestamp(f).date()
        nombre = DIAS[d.weekday()]
        st.markdown(f"**{nombre} {d.strftime('%d/%m/%Y')}**")
        df_dia = df[df["fecha_dt"] == f].sort_values("hora_num")
        for _, row in df_dia.iterrows():
            st.write(f"**{row['hora_str']}** → {fmt_num(row['numero'])} {row['nombre']}")
        st.markdown("")


if __name__ == "__main__":
    main()
