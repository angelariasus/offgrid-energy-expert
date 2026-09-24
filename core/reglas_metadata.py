"""Metadata estática de las 30 reglas del sistema experto (R01-R30).

Vive como una constante Python (no hardcodeada en el router) para que
`routers/api.py` la sirva tal cual en `GET /api/reglas`, permitiendo que el
frontend construya una vista de explicabilidad/auditoría sin duplicar texto,
y sirviendo como evidencia de trazabilidad para la sustentación académica.

Nota: la regla de Capa 3 (`reportar-recomendacion`) no forma parte de estas
30 reglas numeradas; es una regla adicional de reporte/explicabilidad.
"""

from __future__ import annotations

REGLAS_METADATA: list[dict[str, object]] = [
    # ---------------------------------------------------------------- Capa 1
    {
        "codigo": "R01",
        "capa": 1,
        "descripcion": "Viabilidad solar ALTA",
        "condicion": "radiacion > 5.5 kWh/m2/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R02",
        "capa": 1,
        "descripcion": "Viabilidad solar MEDIA",
        "condicion": "4.5 <= radiacion <= 5.5 kWh/m2/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R03",
        "capa": 1,
        "descripcion": "Viabilidad solar BAJA",
        "condicion": "radiacion < 4.5 kWh/m2/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R04",
        "capa": 1,
        "descripcion": "Viabilidad eólica ALTA",
        "condicion": "velocidad-viento > 6.0 m/s",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R05",
        "capa": 1,
        "descripcion": "Viabilidad eólica MEDIA",
        "condicion": "4.0 <= velocidad-viento <= 6.0 m/s",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R06",
        "capa": 1,
        "descripcion": "Viabilidad eólica INVIABLE",
        "condicion": "velocidad-viento < 4.0 m/s",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R07",
        "capa": 1,
        "descripcion": "Viabilidad hidráulica ALTA",
        "condicion": "hay-curso-agua=si ∧ caudal(Q) > 100 l/s ∧ salto-neto(H) > 20 m",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R08",
        "capa": 1,
        "descripcion": "Viabilidad hidráulica MEDIA",
        "condicion": "hay-curso-agua=si ∧ Q >= 20 ∧ H >= 5 ∧ no(Q>100 ∧ H>20)",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R09",
        "capa": 1,
        "descripcion": "Viabilidad hidráulica BAJA",
        "condicion": "hay-curso-agua=si ∧ (Q < 20 l/s ∨ H < 5 m)",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R10",
        "capa": 1,
        "descripcion": "Viabilidad hidráulica INVIABLE",
        "condicion": "hay-curso-agua = no",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R11",
        "capa": 1,
        "descripcion": "Viabilidad de biomasa ALTA",
        "condicion": "masa-estiercol > 20 kg/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R12",
        "capa": 1,
        "descripcion": "Viabilidad de biomasa MEDIA",
        "condicion": "5 <= masa-estiercol <= 20 kg/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R13",
        "capa": 1,
        "descripcion": "Viabilidad de biomasa INVIABLE",
        "condicion": "masa-estiercol < 5 kg/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R14",
        "capa": 1,
        "descripcion": "Demanda MTF: bajo_basico",
        "condicion": "consumo-diario <= 1000 Wh/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R15",
        "capa": 1,
        "descripcion": "Demanda MTF: medio_transicion",
        "condicion": "1000 < consumo-diario <= 3300 Wh/día",
        "tecnologia_asociada": None,
    },
    {
        "codigo": "R16",
        "capa": 1,
        "descripcion": "Demanda MTF: alto_productivo",
        "condicion": "consumo-diario > 3300 Wh/día",
        "tecnologia_asociada": None,
    },
    # ---------------------------------------------------------------- Capa 2
    {
        "codigo": "R17",
        "capa": 2,
        "descripcion": "Solar alta con presupuesto bajo",
        "condicion": "solar=alta ∧ presupuesto=bajo",
        "tecnologia_asociada": "Panel Solar Básico (SHS)",
    },
    {
        "codigo": "R18",
        "capa": 2,
        "descripcion": "Solar alta con demanda básica",
        "condicion": "solar=alta ∧ demanda=bajo_basico",
        "tecnologia_asociada": "Sistema Solar Domiciliario (SHS)",
    },
    {
        "codigo": "R19",
        "capa": 2,
        "descripcion": "Solar alta con demanda productiva y presupuesto suficiente",
        "condicion": "solar=alta ∧ demanda=alto_productivo ∧ presupuesto∈{medio,alto}",
        "tecnologia_asociada": "Sistema Solar Centralizado (Bombeo/Productivo)",
    },
    {
        "codigo": "R20",
        "capa": 2,
        "descripcion": "Eólica alta con solar baja",
        "condicion": "eólica=alta ∧ solar=baja",
        "tecnologia_asociada": "Sistema Eólico Independiente",
    },
    {
        "codigo": "R21",
        "capa": 2,
        "descripcion": "Eólica alta con demanda productiva y presupuesto suficiente",
        "condicion": "eólica=alta ∧ demanda=alto_productivo ∧ presupuesto∈{medio,alto}",
        "tecnologia_asociada": "Sistema Eólico Comunitario con Baterías",
    },
    {
        "codigo": "R22",
        "capa": 2,
        "descripcion": "Hidráulica alta con presupuesto suficiente",
        "condicion": "hidráulica=alta ∧ presupuesto∈{medio,alto}",
        "tecnologia_asociada": "Central Microhidráulica Run-of-River",
    },
    {
        "codigo": "R23",
        "capa": 2,
        "descripcion": "Hidráulica media con demanda productiva",
        "condicion": "hidráulica=media ∧ demanda=alto_productivo",
        "tecnologia_asociada": "Micro Central Hidráulica Banki-Michell",
    },
    {
        "codigo": "R24",
        "capa": 2,
        "descripcion": "Biomasa alta/media con presupuesto medio o bajo",
        "condicion": "biomasa∈{alta,media} ∧ presupuesto∈{medio,bajo}",
        "tecnologia_asociada": "Biodigestor Tubular con Invernadero",
    },
    {
        "codigo": "R25",
        "capa": 2,
        "descripcion": "Biomasa alta con demanda productiva",
        "condicion": "biomasa=alta ∧ demanda=alto_productivo",
        "tecnologia_asociada": "Biodigestor Comunitario con Motogenerador",
    },
    {
        "codigo": "R26",
        "capa": 2,
        "descripcion": "Solar y eólica media con presupuesto bajo",
        "condicion": "solar=media ∧ eólica=media ∧ presupuesto=bajo",
        "tecnologia_asociada": "Solución Solar Básica Prioritaria",
    },
    {
        "codigo": "R27",
        "capa": 2,
        "descripcion": "Híbrido solar-eólico con presupuesto suficiente",
        "condicion": "solar=alta ∧ eólica=alta ∧ presupuesto∈{medio,alto}",
        "tecnologia_asociada": "Sistema Híbrido Solar-Eólico",
    },
    {
        "codigo": "R28",
        "capa": 2,
        "descripcion": "Híbrido solar-hidráulico con demanda productiva",
        "condicion": "solar∈{alta,media} ∧ hidráulica∈{alta,media} ∧ demanda=alto_productivo",
        "tecnologia_asociada": "Sistema Híbrido Solar-Hidráulico",
    },
    {
        "codigo": "R29",
        "capa": 2,
        "descripcion": "Híbrido eólico-hidráulico con presupuesto suficiente",
        "condicion": "eólica=alta ∧ hidráulica=alta ∧ presupuesto∈{medio,alto}",
        "tecnologia_asociada": "Sistema Híbrido Eólico-Hidráulico",
    },
    {
        "codigo": "R30",
        "capa": 2,
        "descripcion": "Microrred híbrida solar-eólica con demanda productiva",
        "condicion": "solar=alta ∧ eólica=alta ∧ demanda=alto_productivo",
        "tecnologia_asociada": "Microrred Híbrida Solar-Eólica con Banco LFP",
    },
]
