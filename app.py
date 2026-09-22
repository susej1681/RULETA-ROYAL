import streamlit as st
import pandas as pd
import re
from collections import Counter
from itertools import combinations

st.set_page_config(
    page_title="Ruleta Royal Pro",
    page_icon="👑",
    layout="centered"
)

GOOGLE_SHEET_ID = "1ZQuqWAsZ2odO7VPppTOB8BhNWg6ktDr8LPGMdEFElrg"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

SORTEOS_POR_DIA = 13
DIAS_VENTANA = 5
VENTANA_SORTEOS = SORTEOS_POR_DIA * DIAS_VENTANA
DESCARTE_ATRASO = 60
PERSISTENCIA_LIMITE = 3
UMBRAL_ESPEJO = 15

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

ECOSISTEMAS = {
    "PLUMAS": [6, 7, 9, 11, 14, 18, 28, 36],
    "DEPREDADORES": [5, 10, 15, 16, 24, 30, 35],
    "CUADRÚPEDOS": [1, 2, 12, 13, 20, 21, 22, 23, 25, 26, 29, 32, 34],
    "RASTREROS": [3, 4, 31],
    "ACUÁTICOS": [0, 17, 19, 27, 33],
}

SERIES = {
    "Serie 0 (00-09)": list(range(0, 10)),
    "Serie 10 (10-19)": list(range(10, 20)),
    "Serie 20 (20-29)": list(range(20, 30)),
    "Serie 30 (30-36)": list(range(30, 37)),
}


def ecosistema_de(num):
    for eco, lista in ECOSISTEMAS.items():
        if num in lista:
            return eco
    return "?"


def serie_de(num):
    for nombre, lista in SERIES.items():
        if num in lista:
            return nombre
    return "?"


def fmt_num(n):
    if n == 0: return "0"
    return f"{n:02d}"


@st.cache_data(ttl=120)
def cargar_historial_google_sheets():
    try:
        df_raw = pd.read_csv(GOOGLE_SHEET_URL, header=None)
        filas_encabezado = []
        for fila in range(len(df_raw)):
            val = str(df_raw.iloc[fila, 0]).strip().lower()
            if val == "hora":
                filas_encabezado.append(fila)
        registros = []
        for idx, fila_enc in enumerate(filas_encabezado):
            fila_fin = filas_encabezado[idx + 1] if idx + 1 < len(filas_encabezado) else len(df_raw)
            fechas_col = {}
            for col in range(1, len(df_raw.columns)):
                val = str(df_raw.iloc[fila_enc, col]).strip()
                if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val):
                    try:
                        fecha_dt = pd.to_datetime(val, format="%d/%m/%Y", errors="coerce")
                        if pd.notna(fecha_dt):
                            fechas_col[col] = fecha_dt.strftime("%d/%m/%Y")
                    except: pass
            fila_fin_datos = min(fila_fin, fila_enc + 14)
            for col, fecha in fechas_col.items():
                for fila_dato in range(fila_enc + 1, fila_fin_datos):
                    val = str(df_raw.iloc[fila_dato, col]).strip()
                    if not val or val.lower() == "nan" or val.lower() == "hora":
                        continue
                    match = re.search(r'\((\d+)\)', val)
                    if match:
                        num_str = match.group(1)
                        num = int(num_str)
                        nombre = ANIMALITOS_DICT.get(num, re.sub(r'\s*\(\d+\)', '', val).strip())
                        registros.append({"fecha": fecha, "numero": num, "nombre": nombre})
        df = pd.DataFrame(registros)
        if not df.empty:
            df["fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
            df = df.sort_values(["fecha_dt"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["fecha", "numero", "nombre"])


def aprender_jales(df, max_atraso=3):
    jales = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums = df["numero"].tolist()
    for i in range(len(nums) - 1):
        origen = nums[i]
        for j in range(i + 1, min(i + 1 + max_atraso, len(nums))):
            jales[origen][nums[j]] += 1
    return jales


def aprender_cadenas(df, max_salto=3):
    cadenas = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums = df["numero"].tolist()
    for i in range(len(nums) - 1):
        for j in range(i + 1, min(i + 1 + max_salto, len(nums))):
            cadenas[nums[i]][nums[j]] += 1
    return cadenas


def detectar_alineaciones(df, salieron_hoy, min_repeticiones=2):
    nums = df["numero"].tolist()
    total = len(nums)
    alineaciones = []
    for i in range(total - 10):
        ventana = nums[i:i + 5]
        unicos = list(dict.fromkeys(ventana))
        for a in range(len(unicos)):
            for b in range(a + 1, len(unicos)):
                alineaciones.append(tuple(sorted([unicos[a], unicos[b]])))
    conteo = Counter(alineaciones)
    parejas_top = [p for p, c in conteo.most_common(10) if c >= min_repeticiones]
    resultado = []
    for par in parejas_top:
        if par[0] in salieron_hoy and par[1] in salieron_hoy: continue
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
                resultado.append({"par": par, "veces": len(posiciones), "atraso": atraso, "promedio": round(promedio, 1)})
    return resultado


def calcular_ritmo_historico(df):
    nums = df["numero"].tolist()
    ritmos = {}
    for num in ANIMALITOS_DICT.keys():
        posiciones = [i for i, n in enumerate(nums) if n == num]
        if len(posiciones) >= 2:
            diffs = [posiciones[k + 1] - posiciones[k] for k in range(len(posiciones) - 1)]
            ritmos[num] = {"promedio": round(sum(diffs) / len(diffs), 1), "apariciones": posiciones}
        else:
            ritmos[num] = {"promedio": 999, "apariciones": posiciones}
    return ritmos


def calcular_congelados(df, ritmos):
    total = len(df)
    congelados = set()
    for num in ANIMALITOS_DICT.keys():
        if num not in ritmos: continue
        ritmo = ritmos[num]["promedio"]
        if ritmo <= 0 or ritmo >= 500: continue
        pos = ritmos[num]["apariciones"]
        if not pos: continue
        atraso = total - 1 - pos[-1]
        if atraso >= ritmo * 2:
            congelados.add(num)
    return congelados


def calcular_penal_ayer(df):
    if df.empty: return set()
    fechas = sorted(df["fecha_dt"].unique())
    if len(fechas) < 2: return set()
    fecha_ayer = fechas[-2]
    df_ayer = df[df["fecha_dt"] == fecha_ayer]
    conteo = Counter(df_ayer["numero"].tolist())
    return set([n for n, c in conteo.items() if c >= 4])


def calcular_ecosistema_top(df):
    if df.empty or len(df) < 20: return None
    df_rec = df.tail(65)
    conteo = Counter([ecosistema_de(n) for n in df_rec["numero"].tolist()])
    if not conteo: return None
    return conteo.most_common(1)[0][0]


def calcular_prob_dia_semana(df, fecha_actual):
    if df.empty or fecha_actual is None: return {}
    ds = fecha_actual.weekday()
    df_dia = df[df["fecha_dt"].apply(lambda x: x.weekday() == ds)]
    if df_dia.empty: return {}
    total = len(df_dia)
    conteo = Counter(df_dia["numero"].tolist())
    return {num: round(c / total * 100, 2) for num, c in conteo.items()}


def calcular_carga_banca(df, scores, detalles, salieron_hoy):
    if df.empty: return []
    fecha_hoy_str = df["fecha"].iloc[-1]
    total_hoy = len(df[df["fecha"] == fecha_hoy_str])
    if total_hoy < PERSISTENCIA_LIMITE: return []
    top = [(n, s) for n, s in sorted(scores.items(), key=lambda x: x[1], reverse=True) if n not in salieron_hoy][:15]
    cargados = []
    for num, sc in top[:3]:
        if detalles[num]["freq_20"] >= 2 or detalles[num]["jales_in"] >= 2:
            cargados.append({"num": num, "score_original": sc, "atraso_hoy": total_hoy})
    return cargados


def aplicar_anti_bloqueo(scores, detalles, carga_banca):
    scores_ajustados = scores.copy()
    detalles_ajustados = {k: v.copy() for k, v in detalles.items()}
    cargados_nums = [c["num"] for c in carga_banca]
    for c in carga_banca:
        num = c["num"]
        scores_ajustados[num] = round(scores_ajustados[num] * 0.5, 2)
        detalles_ajustados[num]["cargado_banca"] = True
    return scores_ajustados, detalles_ajustados, cargados_nums


def calcular_animal_espejo(df, congelados):
    if df.empty or not congelados: return {}
    nums = df["numero"].tolist()
    total = len(nums)
    espejos = {}
    for num_congelado in congelados:
        posiciones = [i for i, n in enumerate(nums) if n == num_congelado]
        if not posiciones: continue
        liberadores = Counter()
        prev = -1
        for pos in posiciones:
            if prev >= 0:
                gap = pos - prev
                if gap >= UMBRAL_ESPEJO:
                    if prev + 1 < total:
                        liberadores[nums[prev + 1]] += 1
            prev = pos
        if liberadores:
            espejos[num_congelado] = liberadores.most_common(3)
    return espejos


def predecir_proximo_espejo(df, congelados):
    if df.empty or not congelados: return []
    espejos = calcular_animal_espejo(df, congelados)
    recomendaciones = []
    for num_congelado, tops in espejos.items():
        for num_liberador, veces in tops:
            recomendaciones.append({"congelado": num_congelado, "liberador": num_liberador, "veces": veces})
    recomendaciones.sort(key=lambda x: x["veces"], reverse=True)
    vistos = set()
    finales = []
    for r in recomendaciones:
        if r["liberador"] not in vistos:
            finales.append(r)
            vistos.add(r["liberador"])
    return finales[:5]


# ═══════════════════════════════════════════════════
# CANDIDATOS A REPETIR MAÑANA (especial Ruleta Royal)
# ═══════════════════════════════════════════════════
def calcular_candidatos_repetir_manana(df, dias_analisis=30):
    """Ruleta Royal repite 4-6 del día anterior.
    Calcula la tasa de repetición de cada animal que salió HOY."""
    if df.empty: return []

    fechas_unicas = sorted(df["fecha_dt"].unique())
    if len(fechas_unicas) < 5: return []

    fechas_recientes = fechas_unicas[-dias_analisis:] if len(fechas_unicas) >= dias_analisis else fechas_unicas

    dias_dict = {}
    for fecha in fechas_recientes:
        df_dia = df[df["fecha_dt"] == fecha]
        dias_dict[fecha] = set(df_dia["numero"].tolist())

    fecha_hoy = fechas_recientes[-1]
    hoy_nums = dias_dict[fecha_hoy]

    stats = {}
    for num in hoy_nums:
        # Buscar en qué días salió
        apariciones = [i for i, f in enumerate(fechas_recientes) if num in dias_dict[f]]
        if len(apariciones) < 2:
            stats[num] = {"tasa": 0, "apariciones": len(apariciones), "veces_repitio": 0}
            continue

        # Contar cuántas veces, al día siguiente de salir, volvió a salir
        veces_repitio = 0
        oportunidades = 0
        for i in apariciones:
            if i + 1 < len(fechas_recientes):
                oportunidades += 1
                if num in dias_dict[fechas_recientes[i + 1]]:
                    veces_repitio += 1

        tasa = (veces_repitio / oportunidades * 100) if oportunidades > 0 else 0
        stats[num] = {
            "tasa": round(tasa, 1),
            "apariciones": len(apariciones),
            "veces_repitio": veces_repitio
        }

    # Ordenar por tasa
    top = sorted(stats.items(), key=lambda x: x[1]["tasa"], reverse=True)
    return [{"num": n, **s} for n, s in top if s["tasa"] > 0][:8]


def analizar_patrones(df, dias_analisis=30):
    if df.empty: return {}, [], [], [], [], []
    fechas_unicas = sorted(df["fecha_dt"].unique())
    fechas_recientes = fechas_unicas[-dias_analisis:] if len(fechas_unicas) >= dias_analisis else fechas_unicas
    dias_dict = {}
    for fecha in fechas_recientes:
        df_dia = df[df["fecha_dt"] == fecha]
        dias_dict[fecha] = set(df_dia["numero"].tolist())
    n_dias = len(fechas_recientes)
    hoy_idx = n_dias - 1
    ayer_idx = n_dias - 2
    repetidores = []
    alternadores = []
    cada_2 = []
    cada_3 = []
    cada_4_5 = []
    for num in ANIMALITOS_DICT.keys():
        apariciones = [i for i, f in enumerate(fechas_recientes) if num in dias_dict[f]]
        if len(apariciones) < 2: continue
        gaps = [apariciones[k + 1] - apariciones[k] for k in range(len(apariciones) - 1)]
        gap_actual = n_dias - 1 - apariciones[-1]
        salio_hoy = hoy_idx in apariciones
        salio_ayer = ayer_idx in apariciones
        promedio_gap = sum(gaps) / len(gaps) if gaps else 0
        if salio_hoy:
            repetidas = sum(1 for g in gaps if g == 1)
            tasa = (repetidas / len(gaps) * 100) if gaps else 0
            if tasa >= 25:
                repetidores.append({"num": num, "tasa": round(tasa, 1), "apariciones": len(apariciones)})
        if salio_ayer and not salio_hoy and len(gaps) >= 2:
            gaps_2 = sum(1 for g in gaps if g == 2)
            tasa_2 = (gaps_2 / len(gaps) * 100)
            if tasa_2 >= 30:
                alternadores.append({"num": num, "tasa": round(tasa_2, 1), "gap_actual": gap_actual})
        if not salio_hoy and gap_actual >= 1 and len(gaps) >= 2:
            if 1.8 <= promedio_gap <= 2.5:
                cada_2.append({"num": num, "promedio": round(promedio_gap, 1), "gap_actual": gap_actual})
            elif 2.5 < promedio_gap <= 3.5 and gap_actual >= 2:
                cada_3.append({"num": num, "promedio": round(promedio_gap, 1), "gap_actual": gap_actual})
            elif 3.5 < promedio_gap <= 5.5 and gap_actual >= 3:
                cada_4_5.append({"num": num, "promedio": round(promedio_gap, 1), "gap_actual": gap_actual})
    repetidores.sort(key=lambda x: x["tasa"], reverse=True)
    alternadores.sort(key=lambda x: x["tasa"], reverse=True)
    cada_2.sort(key=lambda x: -x["gap_actual"])
    cada_3.sort(key=lambda x: -x["gap_actual"])
    cada_4_5.sort(key=lambda x: -x["gap_actual"])
    return dias_dict, repetidores, alternadores, cada_2, cada_3, cada_4_5


def buscar_trios_historicos(df, dias_analisis=60, min_rep=2, ventana=11):
    if df.empty or len(df) < ventana: return []
    fechas_unicas = sorted(df["fecha_dt"].unique())
    if len(fechas_unicas) > dias_analisis:
        fecha_min = fechas_unicas[-dias_analisis]
        df = df[df["fecha_dt"] >= fecha_min].reset_index(drop=True)
    nums = df["numero"].tolist()
    total = len(nums)
    if total < ventana: return []
    conteo = Counter()
    for i in range(total - ventana + 1):
        ventana_nums = nums[i:i + ventana]
        unicos = list(set(ventana_nums))
        if len(unicos) < 3: continue
        for trio in combinations(sorted(unicos), 3):
            conteo[trio] += 1
    filtrados = [(t, c) for t, c in conteo.items() if c >= min_rep]
    filtrados.sort(key=lambda x: x[1], reverse=True)
    return filtrados[:50]


def calcular_tripleta_pensante(df, detalles, scores, ritmos, cadenas, trios_hist, salieron_hoy, congelados, penal_ayer, cargados_nums, excluir=None):
    if excluir is None: excluir = set()
    candidatos_1 = []
    for num in ANIMALITOS_DICT.keys():
        if num in salieron_hoy or num in excluir or num in congelados: continue
        if detalles[num]["enjaulado"]: continue
        if num not in ritmos or ritmos[num]["promedio"] >= 500: continue
        pos = ritmos[num]["apariciones"]
        if not pos: continue
        atraso = len(df) - 1 - pos[-1]
        ritmo = ritmos[num]["promedio"]
        if ritmo <= 0: continue
        ratio = atraso / ritmo
        if ratio >= 1.5: prob = 0.85
        elif ratio >= 1.0: prob = 0.70
        elif ratio >= 0.7: prob = 0.55
        elif ratio >= 0.5: prob = 0.40
        else: prob = 0.20
        if ratio > 4: prob *= 0.5
        if detalles[num]["atraso_hoy"] <= 1: prob *= 0.3
        sf = prob * 100 + scores.get(num, 0) * 0.3
        if num in penal_ayer: sf *= 0.80
        if num in cargados_nums: sf *= 0.50
        candidatos_1.append({"num": num, "score": sf, "atraso": atraso, "ritmo": ritmo, "ratio": round(ratio, 2)})
    candidatos_1.sort(key=lambda x: x["score"], reverse=True)
    if not candidatos_1: return None, []
    num1 = candidatos_1[0]["num"]
    c1 = candidatos_1[0]
    exp = [f"🎯 **{fmt_num(num1)} {ANIMALITOS_DICT[num1]}**: atraso {c1['atraso']} · ritmo {c1['ritmo']} · ratio {c1['ratio']}"]
    if num1 in penal_ayer: exp.append(f"⚠️ penalizado por ayer")
    if num1 in cargados_nums: exp.append(f"🚫 cargado por banca")
    cadena_1 = cadenas.get(num1, Counter())
    candidatos_2 = []
    for num2, veces in cadena_1.most_common(20):
        if num2 == num1 or num2 in salieron_hoy or num2 in excluir or num2 in congelados: continue
        if detalles[num2]["enjaulado"]: continue
        sc = veces * 10
        if 3 <= detalles[num2]["atraso"] <= 40: sc += 15
        sc += detalles[num2]["freq_20"] * 5
        if num2 in penal_ayer: sc *= 0.80
        if num2 in cargados_nums: sc *= 0.50
        candidatos_2.append({"num": num2, "score": sc, "veces": veces})
    if not candidatos_2:
        for c in candidatos_1[1:]:
            if c["num"] not in salieron_hoy:
                candidatos_2.append({"num": c["num"], "score": c["score"], "veces": 0})
                break
    if not candidatos_2: return None, []
    candidatos_2.sort(key=lambda x: x["score"], reverse=True)
    num2 = candidatos_2[0]["num"]
    v2 = candidatos_2[0]["veces"]
    if v2 > 0: exp.append(f"🔗 **{fmt_num(num2)} {ANIMALITOS_DICT[num2]}**: después de {ANIMALITOS_DICT[num1]} → {v2} veces")
    else: exp.append(f"📊 **{fmt_num(num2)} {ANIMALITOS_DICT[num2]}**: segundo más maduro")
    candidatos_3 = []
    for num3 in ANIMALITOS_DICT.keys():
        if num3 in (num1, num2) or num3 in salieron_hoy or num3 in excluir or num3 in congelados: continue
        if detalles[num3]["enjaulado"]: continue
        s3 = 0
        razones = []
        for trio, veces in trios_hist[:30]:
            if num3 in trio and num1 in trio and num2 in trio:
                s3 += veces * 25
                razones.append(f"trío histórico {veces}x")
        cad1 = cadenas.get(num1, Counter()).get(num3, 0)
        cad2 = cadenas.get(num2, Counter()).get(num3, 0)
        if cad1 > 0 or cad2 > 0:
            s3 += (cad1 + cad2) * 5
            razones.append(f"cadenas {cad1+cad2}")
        if 3 <= detalles[num3]["atraso"] <= 40:
            s3 += 15
            razones.append(f"atraso {detalles[num3]['atraso']}")
        s3 += detalles[num3]["jales_in"] * 6
        if serie_de(num3) != serie_de(num1) and serie_de(num3) != serie_de(num2):
            s3 += 8
            razones.append("otra serie")
        if num3 in penal_ayer: s3 *= 0.80
        if num3 in cargados_nums: s3 *= 0.50
        if s3 > 0:
            candidatos_3.append({"num": num3, "score": s3, "razon": ", ".join(razones) if razones else "complementario"})
    candidatos_3.sort(key=lambda x: x["score"], reverse=True)
    if not candidatos_3: return None, []
    num3 = candidatos_3[0]["num"]
    exp.append(f"🧩 **{fmt_num(num3)} {ANIMALITOS_DICT[num3]}**: {candidatos_3[0]['razon']}")
    return [num1, num2, num3], exp


def motor_principal(df):
    if df.empty or len(df) < 30:
        return {}

    df_ventana = df.tail(VENTANA_SORTEOS).copy()
    freq_ventana = Counter(df_ventana["numero"].tolist())
    freq_rec20 = Counter(df.tail(20)["numero"].tolist())
    freq_rec30 = Counter(df.tail(30)["numero"].tolist())
    atrasos = {}
    total = len(df)
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        atrasos[num] = total - 1 - idxs[-1] if idxs else total

    fecha_hoy = df["fecha"].iloc[-1]
    df_hoy = df[df["fecha"] == fecha_hoy]
    total_hoy = len(df_hoy)
    salieron_hoy = set(df_hoy["numero"].tolist())
    atraso_hoy = {}
    for num in ANIMALITOS_DICT.keys():
        idxs_hoy = df_hoy[df_hoy["numero"] == num].index.tolist()
        if idxs_hoy:
            atraso_hoy[num] = total_hoy - 1 - df_hoy.index.get_loc(idxs_hoy[-1])
        else:
            atraso_hoy[num] = 999

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
    ultima_fecha_str = fechas_unicas[-1]
    ultima_fecha_dt = pd.to_datetime(ultima_fecha_str, format="%d/%m/%Y", errors="coerce")
    hoy_real_dt = pd.Timestamp.now().normalize()
    fecha_dia_anterior = None
    if pd.notna(ultima_fecha_dt):
        if ultima_fecha_dt.normalize() == hoy_real_dt:
            if len(fechas_unicas) >= 2:
                fecha_dia_anterior = fechas_unicas[-2]
        else:
            fecha_dia_anterior = ultima_fecha_str

    ritmos = calcular_ritmo_historico(df)
    congelados = calcular_congelados(df, ritmos)
    penal_ayer = calcular_penal_ayer(df)
    eco_top = calcular_ecosistema_top(df)
    prob_dia = calcular_prob_dia_semana(df, ultima_fecha_dt)

    scores = {}
    detalles = {}
    for num in ANIMALITOS_DICT.keys():
        fv = freq_ventana.get(num, 0); f20 = freq_rec20.get(num, 0); f30 = freq_rec30.get(num, 0)
        atr = atrasos.get(num, 0); atr_hoy = atraso_hoy.get(num, 999); jal = jales_entrantes.get(num, 0)
        n_fv = fv / max_fv if max_fv else 0
        n_f20 = f20 / max_f20 if max_f20 else 0
        n_atr = atr / max_atr if max_atr else 0
        n_jal = jal / max_jal if max_jal else 0
        bonus_caliente = 0.08 if f30 >= 3 else (0.04 if f30 == 2 else 0)
        penal_frio = 0
        if atr > 60: penal_frio = -0.35
        elif atr > 45: penal_frio = -0.20
        elif atr > 30: penal_frio = -0.10
        penal_reciente = 0
        if atr_hoy == 0: penal_reciente = -0.60
        elif atr_hoy == 1: penal_reciente = -0.45
        elif atr_hoy == 2: penal_reciente = -0.30
        elif atr_hoy == 3: penal_reciente = -0.20
        elif atr_hoy == 4: penal_reciente = -0.10
        score = n_fv*0.20 + n_f20*0.20 + n_atr*0.20 + n_jal*0.25 + bonus_caliente + penal_frio + penal_reciente
        if eco_top and ecosistema_de(num) == eco_top: score += 0.10
        if prob_dia.get(num, 0) >= 3: score += 0.05
        if fv == 0: score *= 0.4
        if atr >= DESCARTE_ATRASO: score = 0
        if num in congelados: score *= 0.10
        if num in penal_ayer: score *= 0.80
        scores[num] = round(max(score, 0) * 100, 2)
        detalles[num] = {
            "freq_ventana": fv, "freq_20": f20, "atraso": atr, "atraso_hoy": atr_hoy,
            "jales_in": jal, "caliente": bonus_caliente > 0,
            "penal": penal_frio < 0, "enjaulado": atr >= DESCARTE_ATRASO,
            "congelado": num in congelados, "penal_ayer": num in penal_ayer,
            "eco_top": eco_top and ecosistema_de(num) == eco_top,
            "cargado_banca": False
        }

    carga_banca = calcular_carga_banca(df, scores, detalles, salieron_hoy)
    scores_ajustados, detalles_ajustados, cargados_nums = aplicar_anti_bloqueo(scores, detalles, carga_banca)

    return {
        "df": df, "scores": scores_ajustados, "scores_original": scores,
        "detalles": detalles_ajustados, "ritmos": ritmos,
        "jales_aprendidos": jales_aprendidos, "salieron_hoy": salieron_hoy,
        "congelados": congelados, "penal_ayer": penal_ayer, "carga_banca": carga_banca,
        "cargados_nums": cargados_nums, "eco_top": eco_top,
        "fecha_dia_anterior": fecha_dia_anterior, "atrasos": atrasos
    }


def main():
    st.title("👑 Ruleta Royal Pro V2")
    st.caption("Patrones · Cortafuegos · Ecosistemas · Anti-Bloqueo · Espejos · Repetidores")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja..."):
        df = cargar_historial_google_sheets()

    if df.empty:
        st.error("No se pudieron cargar datos.")
        return

    motor = motor_principal(df)
    if not motor:
        st.warning("Datos insuficientes.")
        return

    scores = motor["scores"]
    detalles = motor["detalles"]
    ritmos = motor["ritmos"]
    jales_aprendidos = motor["jales_aprendidos"]
    salieron_hoy = motor["salieron_hoy"]
    congelados = motor["congelados"]
    penal_ayer = motor["penal_ayer"]
    carga_banca = motor["carga_banca"]
    cargados_nums = motor["cargados_nums"]
    eco_top = motor["eco_top"]
    fecha_dia_anterior = motor["fecha_dia_anterior"]

    ultimo = df.iloc[-1]
    st.caption(f"📅 Día: {ultimo['fecha']} · Hoy: {len(salieron_hoy)} · Congelados: {len(congelados)} · Ayer: {len(penal_ayer)} · Cargados: {len(carga_banca)}")

    # ═══════════════════════════════════════════════════
    # CANDIDATOS A REPETIR MAÑANA (ESPECIAL RULETA ROYAL)
    # ═══════════════════════════════════════════════════
    candidatos_rep = calcular_candidatos_repetir_manana(df, dias_analisis=30)
    if candidatos_rep:
        st.markdown("## 🔁 CANDIDATOS A REPETIR MAÑANA")
        st.caption("Ruleta Royal suele repetir 4-6 del día anterior. Top con mayor tasa:")
        for i, c in enumerate(candidatos_rep[:8], 1):
            emoji = "🔥" if c["tasa"] >= 50 else ("🟡" if c["tasa"] >= 35 else "🟢")
            st.write(f"{emoji} **#{i} - {fmt_num(c['num'])} {ANIMALITOS_DICT[c['num']]}** — Repite {c['tasa']}% ({c['veces_repitio']}/{c['apariciones']} veces)")
        st.markdown("---")

    # ECOSISTEMA
    if eco_top:
        st.markdown(f"## 🌍 Ecosistema caliente hoy: **{eco_top}**")
        st.markdown("---")

    # ANTI-BLOQUEO
    if carga_banca:
        st.markdown("## 🚫 MÓDULO ANTI-BLOQUEO DE BANCA")
        for c in carga_banca:
            st.warning(f"**{fmt_num(c['num'])} {ANIMALITOS_DICT[c['num']]}** — Cargado · Score original {c['score_original']}% · Atraso hoy {c['atraso_hoy']}")
        st.markdown("---")

    # ESPEJOS
    if congelados:
        espejos = predecir_proximo_espejo(df, congelados)
        if espejos:
            st.markdown("## 🪞 ANIMAL ESPEJO (rompe-sequías)")
            for e in espejos:
                st.info(f"**{fmt_num(e['liberador'])} {ANIMALITOS_DICT[e['liberador']]}** — Ha roto sequías {e['veces']} veces (de {fmt_num(e['congelado'])} {ANIMALITOS_DICT[e['congelado']]})")
            st.markdown("---")

    # PATRONES
    dias_dict, repetidores, alternadores, cada_2, cada_3, cada_4_5 = analizar_patrones(df, dias_analisis=30)
    st.markdown("## 📊 PATRONES (últimos 30 días)")

    if repetidores:
        st.markdown("### 🔁 Repetidores (salieron hoy)")
        for i, r in enumerate(repetidores[:8], 1):
            if r["num"] in congelados or r["num"] in cargados_nums: continue
            emoji = "🔥" if r["tasa"] >= 50 else ("🟡" if r["tasa"] >= 35 else "🟢")
            st.write(f"{emoji} **{fmt_num(r['num'])} {ANIMALITOS_DICT[r['num']]}** — Repite {r['tasa']}%")

    if alternadores:
        st.markdown("### 🔄 Alternadores (día sí, día no)")
        for i, a in enumerate(alternadores[:6], 1):
            if a["num"] in congelados or a["num"] in cargados_nums: continue
            st.write(f"**{fmt_num(a['num'])} {ANIMALITOS_DICT[a['num']]}** — Alterna {a['tasa']}% (gap {a['gap_actual']})")

    if cada_2:
        st.markdown("### 📅 Cada 2 días")
        for c in cada_2[:6]:
            if c["num"] in congelados or c["num"] in cargados_nums: continue
            st.write(f"**{fmt_num(c['num'])} {ANIMALITOS_DICT[c['num']]}** — prom {c['promedio']}d · gap {c['gap_actual']}d")

    if cada_3:
        st.markdown("### 📅 Cada 3 días")
        for c in cada_3[:6]:
            if c["num"] in congelados or c["num"] in cargados_nums: continue
            st.write(f"**{fmt_num(c['num'])} {ANIMALITOS_DICT[c['num']]}** — prom {c['promedio']}d · gap {c['gap_actual']}d")

    if cada_4_5:
        st.markdown("### 📅 Cada 4-5 días")
        for c in cada_4_5[:6]:
            if c["num"] in congelados or c["num"] in cargados_nums: continue
            st.write(f"**{fmt_num(c['num'])} {ANIMALITOS_DICT[c['num']]}** — prom {c['promedio']}d · gap {c['gap_actual']}d")
    st.markdown("---")

    # TRIPLETA PENSANTE
    cadenas = aprender_cadenas(df, max_salto=3)
    trios_hist = buscar_trios_historicos(df, dias_analisis=60, min_rep=2, ventana=11)

    st.markdown("## 🧠 TRIPLETA PENSANTE (con filtros)")
    r_a = calcular_tripleta_pensante(df, detalles, scores, ritmos, cadenas, trios_hist, salieron_hoy, congelados, penal_ayer, cargados_nums, excluir=None)
    if r_a[0]:
        nums_a, exp_a = r_a
        st.markdown("### 🎯 TRIPLETA PENSANTE A")
        st.success(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in nums_a]))
        for e in exp_a: st.markdown(f"- {e}")
    else:
        st.warning("No se pudo armar la Tripleta A.")

    st.markdown("")
    excluir_b = set(r_a[0]) if r_a[0] else set()
    r_b = calcular_tripleta_pensante(df, detalles, scores, ritmos, cadenas, trios_hist, salieron_hoy, congelados, penal_ayer, cargados_nums, excluir=excluir_b)
    if r_b[0]:
        nums_b, exp_b = r_b
        st.markdown("### ⚡ TRIPLETA PENSANTE B (alternativa)")
        st.info(" - ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in nums_b]))
        for e in exp_b: st.markdown(f"- {e}")
    st.markdown("---")

    # ALINEACIONES
    alineaciones = detectar_alineaciones(df, salieron_hoy, min_repeticiones=2)
    if alineaciones:
        st.markdown("### 🔗 Alineación Caliente")
        for al in alineaciones[:3]:
            a, b = al["par"]
            if a in congelados or b in congelados: continue
            if a in cargados_nums or b in cargados_nums: continue
            st.markdown(f"**{fmt_num(a)} {ANIMALITOS_DICT[a]} + {fmt_num(b)} {ANIMALITOS_DICT[b]}**")
            st.caption(f"{al['veces']} veces · Promedio cada {al['promedio']} · Atraso: {al['atraso']}")
        st.markdown("---")

    # ÚLTIMO RESULTADO
    st.markdown("### 🎯 Último resultado")
    st.markdown(f"## {fmt_num(int(ultimo['numero']))} - {ultimo['nombre']}")
    st.caption(f"Fecha: {ultimo['fecha']}")
    st.markdown("---")

    # ANIMALES DE HOY
    df_hoy = df[df["fecha"] == ultimo['fecha']].reset_index(drop=True)
    if not df_hoy.empty:
        st.markdown(f"### 📅 Animales de HOY ({ultimo['fecha']}) — Ya salieron {len(df_hoy)}")
        for i, row in df_hoy.iterrows():
            num = int(row["numero"])
            d = detalles.get(num, {})
            st.write(f"{i+1}. **{fmt_num(num)} - {row['nombre']}** (atraso: {d.get('atraso', '?')})")
        st.markdown("---")

    # ANIMALES DE AYER
    if fecha_dia_anterior:
        st.markdown(f"### 🔁 Animales del {fecha_dia_anterior}")
        df_dia = df[df["fecha"] == fecha_dia_anterior].reset_index(drop=True)
        for i, row in df_dia.iterrows():
            num = int(row["numero"])
            d = detalles.get(num, {})
            marca = " ⚠️ (4+ ayer)" if num in penal_ayer else ""
            st.write(f"{i+1}. **{fmt_num(num)} - {row['nombre']}** (atraso: {d.get('atraso', '?')}){marca}")
        st.markdown("---")

    # TOP 10
    st.markdown("### 🏆 Top 10 Animales")
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
    for i, (num, sc) in enumerate(top, 1):
        d = detalles[num]
        marcas = []
        if d["caliente"]: marcas.append("🔥")
        if d["eco_top"]: marcas.append("🌍")
        if d["penal_ayer"]: marcas.append("⚠️")
        if d["congelado"]: marcas.append("❄️")
        if d.get("cargado_banca"): marcas.append("🚫")
        st.write(f"**#{i} - {fmt_num(num)} {ANIMALITOS_DICT[num]}** — {sc}% {' '.join(marcas)}")
    st.markdown("---")

    # JALES
    st.markdown("### 🔗 Jales Aprendidos")
    ultimo_num = int(ultimo["numero"])
    jales_ult = jales_aprendidos.get(ultimo_num, Counter())
    if jales_ult:
        for jale, c in jales_ult.most_common(3):
            st.write(f"- Después de **{fmt_num(ultimo_num)} {ultimo['nombre']}** → **{fmt_num(jale)} {ANIMALITOS_DICT[jale]}** ({c} veces)")

    with st.expander("❄️ Ver congelados"):
        for num in sorted(congelados):
            st.write(f"- {fmt_num(num)} {ANIMALITOS_DICT[num]}")

    with st.expander("⚠️ Ver penalizados por ayer"):
        for num in sorted(penal_ayer):
            st.write(f"- {fmt_num(num)} {ANIMALITOS_DICT[num]}")

    with st.expander("📋 Ver últimos 30 sorteos"):
        st.dataframe(df.tail(30)[["fecha", "numero", "nombre"]], use_container_width=True)


if __name__ == "__main__":
    main()
