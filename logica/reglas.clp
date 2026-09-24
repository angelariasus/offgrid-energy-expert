; =============================================================================
; Sistema Experto de Energias Renovables Off-Grid
; UNMSM - Curso Sistemas Inteligentes
;
; Motor: forward chaining, algoritmo Rete, resolucion de conflictos Depth (LIFO)
; 30 reglas organizadas en 3 capas mediante salience:
;   Capa 1 (salience 20): R01-R16  - Abstraccion tecnica (mediciones -> viabilidad/demanda)
;   Capa 2 (salience 10): R17-R30  - Decision tecnologica (viabilidad+contexto -> tecnologia)
;   Capa 3 (salience 0) : reportar-recomendacion - Explicabilidad
;
; Puntos de corte verificados como mutuamente excluyentes y sin huecos:
;   Solar (radiacion, kWh/m2/dia):      alta >5.5 | media [4.5,5.5] | baja <4.5
;   Eolica (velocidad-viento, m/s):     alta >6.0 | media [4.0,6.0] | inviable <4.0
;   Hidraulica (caudal Q l/s, salto H m, con curso de agua):
;       alta: Q>100 y H>20
;       baja: Q<20 o H<5
;       media: complemento exacto de {alta} U {baja} dentro del dominio Q>=0,H>=0
;              (equivalente a Q>=20 y H>=5 y no(Q>100 y H>20))
;       inviable: hay-curso-agua = no
;   Biomasa (masa-estiercol, kg/dia):   alta >20 | media [5,20] | inviable <5
;   Demanda MTF (consumo-diario, Wh/dia): bajo_basico <=1000 | medio_transicion (1000,3300] | alto_productivo >3300
; =============================================================================


; =============================================================================
; DEFTEMPLATES
; =============================================================================

(deftemplate mediciones-zona
    "Hecho de entrada: mediciones brutas tomadas en campo para una zona/comunidad."
    (slot radiacion (type FLOAT))
    (slot velocidad-viento (type FLOAT))
    (slot hay-curso-agua (type SYMBOL) (allowed-symbols si no))
    (slot caudal (type FLOAT))
    (slot salto-neto (type FLOAT))
    (slot masa-estiercol (type FLOAT))
    (slot consumo-diario (type FLOAT))
    (slot presupuesto (type SYMBOL) (allowed-symbols bajo medio alto)))

(deftemplate viabilidad-recurso
    "Hecho derivado (Capa 1): nivel de viabilidad tecnica de un recurso energetico."
    (slot recurso (type SYMBOL) (allowed-symbols solar eolica hidraulica biomasa))
    (slot nivel (type SYMBOL) (allowed-symbols alta media baja inviable)))

(deftemplate clasificacion-demanda
    "Hecho derivado (Capa 1): clasificacion de la demanda segun el Multi-Tier Framework (MTF)."
    (slot nivel (type SYMBOL) (allowed-symbols bajo_basico medio_transicion alto_productivo)))

(deftemplate recomendacion-energetica
    "Hecho de salida (Capa 2): tecnologia prescrita, con justificacion y trazabilidad de la regla origen."
    (slot tecnologia (type STRING))
    (slot justificacion (type STRING))
    (slot regla-origen (type STRING)))


; =============================================================================
; CAPA 1 - ABSTRACCION TECNICA (salience 20) - R01 a R16
; Convierten mediciones brutas en niveles de viabilidad y clasifican la demanda.
; =============================================================================

; --- Solar fotovoltaica (R01-R03) ---------------------------------------------

(defrule R01-solar-alta
    (declare (salience 20))
    (mediciones-zona (radiacion ?r&:(> ?r 5.5)))
    =>
    (assert (viabilidad-recurso (recurso solar) (nivel alta))))

(defrule R02-solar-media
    (declare (salience 20))
    (mediciones-zona (radiacion ?r&:(and (>= ?r 4.5) (<= ?r 5.5))))
    =>
    (assert (viabilidad-recurso (recurso solar) (nivel media))))

(defrule R03-solar-baja
    (declare (salience 20))
    (mediciones-zona (radiacion ?r&:(< ?r 4.5)))
    =>
    (assert (viabilidad-recurso (recurso solar) (nivel baja))))

; --- Eolica de pequena escala (R04-R06) ---------------------------------------

(defrule R04-eolica-alta
    (declare (salience 20))
    (mediciones-zona (velocidad-viento ?v&:(> ?v 6.0)))
    =>
    (assert (viabilidad-recurso (recurso eolica) (nivel alta))))

(defrule R05-eolica-media
    (declare (salience 20))
    (mediciones-zona (velocidad-viento ?v&:(and (>= ?v 4.0) (<= ?v 6.0))))
    =>
    (assert (viabilidad-recurso (recurso eolica) (nivel media))))

(defrule R06-eolica-inviable
    (declare (salience 20))
    (mediciones-zona (velocidad-viento ?v&:(< ?v 4.0)))
    =>
    (assert (viabilidad-recurso (recurso eolica) (nivel inviable))))

; --- Micro/mini hidraulica run-of-river (R07-R10) -----------------------------

(defrule R07-hidraulica-alta
    (declare (salience 20))
    (mediciones-zona (hay-curso-agua si)
                      (caudal ?q&:(> ?q 100))
                      (salto-neto ?h&:(> ?h 20)))
    =>
    (assert (viabilidad-recurso (recurso hidraulica) (nivel alta))))

(defrule R08-hidraulica-media
    (declare (salience 20))
    (mediciones-zona (hay-curso-agua si)
                      (caudal ?q&:(>= ?q 20))
                      (salto-neto ?h&:(and (>= ?h 5)
                                            (or (<= ?q 100) (<= ?h 20)))))
    =>
    (assert (viabilidad-recurso (recurso hidraulica) (nivel media))))

(defrule R09-hidraulica-baja
    (declare (salience 20))
    (mediciones-zona (hay-curso-agua si)
                      (caudal ?q)
                      (salto-neto ?h&:(or (< ?q 20) (< ?h 5))))
    =>
    (assert (viabilidad-recurso (recurso hidraulica) (nivel baja))))

(defrule R10-hidraulica-inviable
    (declare (salience 20))
    (mediciones-zona (hay-curso-agua no))
    =>
    (assert (viabilidad-recurso (recurso hidraulica) (nivel inviable))))

; --- Biodigestion anaerobica / biomasa (R11-R13) ------------------------------

(defrule R11-biomasa-alta
    (declare (salience 20))
    (mediciones-zona (masa-estiercol ?m&:(> ?m 20)))
    =>
    (assert (viabilidad-recurso (recurso biomasa) (nivel alta))))

(defrule R12-biomasa-media
    (declare (salience 20))
    (mediciones-zona (masa-estiercol ?m&:(and (>= ?m 5) (<= ?m 20))))
    =>
    (assert (viabilidad-recurso (recurso biomasa) (nivel media))))

(defrule R13-biomasa-inviable
    (declare (salience 20))
    (mediciones-zona (masa-estiercol ?m&:(< ?m 5)))
    =>
    (assert (viabilidad-recurso (recurso biomasa) (nivel inviable))))

; --- Clasificacion de demanda (Multi-Tier Framework) (R14-R16) ---------------

(defrule R14-demanda-bajo-basico
    (declare (salience 20))
    (mediciones-zona (consumo-diario ?c&:(<= ?c 1000)))
    =>
    (assert (clasificacion-demanda (nivel bajo_basico))))

(defrule R15-demanda-medio-transicion
    (declare (salience 20))
    (mediciones-zona (consumo-diario ?c&:(and (> ?c 1000) (<= ?c 3300))))
    =>
    (assert (clasificacion-demanda (nivel medio_transicion))))

(defrule R16-demanda-alto-productivo
    (declare (salience 20))
    (mediciones-zona (consumo-diario ?c&:(> ?c 3300)))
    =>
    (assert (clasificacion-demanda (nivel alto_productivo))))


; =============================================================================
; CAPA 2 - DECISION TECNOLOGICA (salience 10) - R17 a R30
; Cruzan viabilidades con presupuesto/demanda para prescribir tecnologia.
; Varias reglas pueden dispararse simultaneamente (monofuente + hibrida a la vez).
; =============================================================================

(defrule R17-panel-solar-basico
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel alta))
    (mediciones-zona (presupuesto bajo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Panel Solar Basico (SHS)")
                (justificacion "Radiacion solar con viabilidad ALTA y presupuesto BAJO: se prioriza un sistema solar domiciliario individual de bajo costo de adquisicion y mantenimiento.")
                (regla-origen "R17"))))

(defrule R18-sistema-solar-domiciliario
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel alta))
    (clasificacion-demanda (nivel bajo_basico))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Solar Domiciliario (SHS)")
                (justificacion "Radiacion solar con viabilidad ALTA y demanda clasificada como BAJO_BASICO (MTF): un sistema solar domiciliario cubre las necesidades esenciales de iluminacion y carga de dispositivos.")
                (regla-origen "R18"))))

(defrule R19-sistema-solar-centralizado
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel alta))
    (clasificacion-demanda (nivel alto_productivo))
    (mediciones-zona (presupuesto ?p&medio|alto))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Solar Centralizado (Bombeo/Productivo)")
                (justificacion "Radiacion solar ALTA, demanda ALTO_PRODUCTIVO y presupuesto suficiente: se justifica una instalacion centralizada orientada a usos productivos (bombeo, agroindustria, etc.).")
                (regla-origen "R19"))))

(defrule R20-sistema-eolico-independiente
    (declare (salience 10))
    (viabilidad-recurso (recurso eolica) (nivel alta))
    (viabilidad-recurso (recurso solar) (nivel baja))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Eolico Independiente")
                (justificacion "Viento con viabilidad ALTA mientras que el recurso solar es BAJO: la eolica se convierte en la fuente principal viable de la zona.")
                (regla-origen "R20"))))

(defrule R21-sistema-eolico-comunitario
    (declare (salience 10))
    (viabilidad-recurso (recurso eolica) (nivel alta))
    (clasificacion-demanda (nivel alto_productivo))
    (mediciones-zona (presupuesto ?p&medio|alto))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Eolico Comunitario con Baterias")
                (justificacion "Viento ALTO, demanda ALTO_PRODUCTIVO y presupuesto suficiente: se justifica un sistema comunitario con banco de baterias para sostener cargas productivas.")
                (regla-origen "R21"))))

(defrule R22-central-microhidraulica-ror
    (declare (salience 10))
    (viabilidad-recurso (recurso hidraulica) (nivel alta))
    (mediciones-zona (presupuesto ?p&medio|alto))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Central Microhidraulica Run-of-River")
                (justificacion "Caudal y salto neto con viabilidad ALTA y presupuesto suficiente: una central run-of-river ofrece generacion constante de alta capacidad.")
                (regla-origen "R22"))))

(defrule R23-micro-central-banki-michell
    (declare (salience 10))
    (viabilidad-recurso (recurso hidraulica) (nivel media))
    (clasificacion-demanda (nivel alto_productivo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Micro Central Hidraulica Banki-Michell")
                (justificacion "Recurso hidraulico con viabilidad MEDIA y demanda ALTO_PRODUCTIVO: una turbina Banki-Michell es adecuada para caudales y saltos moderados con generacion suficiente para usos productivos.")
                (regla-origen "R23"))))

(defrule R24-biodigestor-tubular-invernadero
    (declare (salience 10))
    (viabilidad-recurso (recurso biomasa) (nivel ?n&alta|media))
    (mediciones-zona (presupuesto ?p&medio|bajo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Biodigestor Tubular con Invernadero")
                (justificacion "Disponibilidad de estiercol con viabilidad ALTA o MEDIA y presupuesto BAJO o MEDIO: el biodigestor tubular es una solucion de bajo costo apta para climas frios (invernadero).")
                (regla-origen "R24"))))

(defrule R25-biodigestor-comunitario-motogenerador
    (declare (salience 10))
    (viabilidad-recurso (recurso biomasa) (nivel alta))
    (clasificacion-demanda (nivel alto_productivo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Biodigestor Comunitario con Motogenerador")
                (justificacion "Disponibilidad de estiercol con viabilidad ALTA y demanda ALTO_PRODUCTIVO: un biodigestor comunitario con motogenerador entrega la potencia necesaria para usos productivos.")
                (regla-origen "R25"))))

(defrule R26-solucion-solar-basica-prioritaria
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel media))
    (viabilidad-recurso (recurso eolica) (nivel media))
    (mediciones-zona (presupuesto bajo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Solucion Solar Basica Prioritaria")
                (justificacion "Solar y eolica ambos con viabilidad MEDIA y presupuesto BAJO: se prioriza la solucion solar basica por su menor costo de mantenimiento frente a la eolica.")
                (regla-origen "R26"))))

(defrule R27-sistema-hibrido-solar-eolico
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel alta))
    (viabilidad-recurso (recurso eolica) (nivel alta))
    (mediciones-zona (presupuesto ?p&medio|alto))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Hibrido Solar-Eolico")
                (justificacion "Solar y eolica con viabilidad ALTA simultaneamente y presupuesto suficiente: un sistema hibrido aprovecha la complementariedad de ambos recursos.")
                (regla-origen "R27"))))

(defrule R28-sistema-hibrido-solar-hidraulico
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel ?ns&alta|media))
    (viabilidad-recurso (recurso hidraulica) (nivel ?nh&alta|media))
    (clasificacion-demanda (nivel alto_productivo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Hibrido Solar-Hidraulico")
                (justificacion "Solar e hidraulica con viabilidad ALTA o MEDIA y demanda ALTO_PRODUCTIVO: la complementariedad estacional entre ambos recursos sostiene cargas productivas todo el ano.")
                (regla-origen "R28"))))

(defrule R29-sistema-hibrido-eolico-hidraulico
    (declare (salience 10))
    (viabilidad-recurso (recurso eolica) (nivel alta))
    (viabilidad-recurso (recurso hidraulica) (nivel alta))
    (mediciones-zona (presupuesto ?p&medio|alto))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Sistema Hibrido Eolico-Hidraulico")
                (justificacion "Eolica e hidraulica con viabilidad ALTA simultaneamente y presupuesto suficiente: sistema hibrido de alta capacidad combinada.")
                (regla-origen "R29"))))

(defrule R30-microrred-hibrida-solar-eolica-lfp
    (declare (salience 10))
    (viabilidad-recurso (recurso solar) (nivel alta))
    (viabilidad-recurso (recurso eolica) (nivel alta))
    (clasificacion-demanda (nivel alto_productivo))
    =>
    (assert (recomendacion-energetica
                (tecnologia "Microrred Hibrida Solar-Eolica con Banco LFP")
                (justificacion "Solar y eolica con viabilidad ALTA y demanda ALTO_PRODUCTIVO: una microrred con banco de baterias de Litio-Ferrofosfato (LFP) garantiza estabilidad y autonomia para cargas productivas.")
                (regla-origen "R30"))))


; =============================================================================
; CAPA 3 - EXPLICABILIDAD (salience 0)
; =============================================================================

(defrule reportar-recomendacion
    (declare (salience 0))
    (recomendacion-energetica (tecnologia ?t) (regla-origen ?r))
    =>
    (printout t "Recomendacion [" ?r "]: " ?t crlf))
