import os
import pptx
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

def create_presentation():
    prs = pptx.Presentation()
    # 16:9 widescreen: 13.333 x 7.5 inches
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Paleta oficial (Kit de Elementos)
    C_CREMA = RGBColor(251, 241, 232)        # #FBF1E8
    C_NEGRO = RGBColor(20, 20, 20)           # #141414
    C_AZUL = RGBColor(26, 66, 184)           # #1A42B8
    C_AZUL_OSCURO = RGBColor(18, 48, 127)    # #12307F
    C_AZUL_CLARO = RGBColor(230, 241, 251)   # #E6F1FB
    C_GRIS = RGBColor(107, 114, 128)         # #6B7280
    C_BLANCO = RGBColor(255, 255, 255)       # #FFFFFF
    C_BORDE = RGBColor(226, 217, 204)        # #E2D9CC
    C_VERDE = RGBColor(30, 138, 95)          # #1E8A5F
    C_VERDE_CLARO = RGBColor(227, 243, 234)  # #E3F3EA
    C_ROJO = RGBColor(184, 58, 58)           # #B83A3A
    C_ROJO_CLARO = RGBColor(249, 225, 225)   # #F9E1E1
    C_AMBAR = RGBColor(183, 121, 31)         # #B7791F
    C_AMBAR_CLARO = RGBColor(251, 239, 213)  # #FBEFD5

    def set_bg(slide, color=C_CREMA):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, eyebrow, title, dark_mode=False):
        # Eyebrow
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7), Inches(0.35))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = eyebrow.upper()
        p.font.name = "Calibri"
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_AZUL if not dark_mode else C_AZUL_CLARO

        # Title
        tx_box2 = slide.shapes.add_textbox(Inches(0.8), Inches(0.85), Inches(11.7), Inches(0.65))
        tf2 = tx_box2.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = title
        p2.font.name = "Arial"
        p2.font.size = Pt(28)
        p2.font.bold = True
        p2.font.color.rgb = C_NEGRO if not dark_mode else C_BLANCO

    def add_footer(slide, text="GOMERÍA EL PUENTE · SISTEMA DE GESTIÓN", dark_mode=False):
        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.3))
        tf = tx_box.text_frame
        p = tf.paragraphs[0]
        p.text = text.upper()
        p.font.name = "Calibri"
        p.font.size = Pt(9)
        p.font.bold = True
        p.font.color.rgb = C_GRIS if not dark_mode else C_AZUL_CLARO

    def add_card(slide, left, top, width, height, bg_color=C_BLANCO, border_color=C_BORDE):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1.2)
        else:
            card.line.fill.background()
        return card

    # =========================================================================
    # SLIDE 1: PORTADA (Kit Pág. 4)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1, C_CREMA)
    # Right blue banner (35% width)
    r_banner = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(8.8), 0, Inches(4.533), prs.slide_height)
    r_banner.fill.solid()
    r_banner.fill.fore_color.rgb = C_AZUL
    r_banner.line.fill.background()

    # Right white card
    r_card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.3), Inches(2.3), Inches(3.5), Inches(2.9))
    r_card.fill.solid()
    r_card.fill.fore_color.rgb = C_BLANCO
    r_card.line.fill.background()
    tf_rc = r_card.text_frame
    tf_rc.vertical_anchor = pptx.enum.text.MSO_ANCHOR.MIDDLE
    p = tf_rc.paragraphs[0]
    p.text = "LOGO O IMAGEN\nDEL SISTEMA"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Arial"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_AZUL

    # Left content
    tx_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.2), Inches(7.5), Inches(5.2))
    tf = tx_box.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "P R E S E N T A C I Ó N   F I N A L"
    p0.font.name = "Calibri"
    p0.font.size = Pt(12)
    p0.font.bold = True
    p0.font.color.rgb = C_AZUL

    p1 = tf.add_paragraph()
    p1.space_before = Pt(14)
    p1.text = "SISTEMA DE GESTIÓN\nGOMERÍA EL PUENTE"
    p1.font.name = "Arial"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = C_NEGRO

    p2 = tf.add_paragraph()
    p2.space_before = Pt(10)
    p2.text = "ADMINISTRACIÓN INTEGRAL DE FLOTAS Y CUENTAS CORRIENTES"
    p2.font.name = "Calibri"
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = C_GRIS

    p3 = tf.add_paragraph()
    p3.space_before = Pt(40)
    p3.text = "Alumno: [ COMPLETAR: Nombre y Apellido ]\nMateria: Programación IV & Gestión de Desarrollo de Software (UTN FRGP)\nProfesor: [ COMPLETAR: Nombre del Docente / Tribunal ]\nFecha: Noviembre de 2026"
    p3.font.name = "Calibri"
    p3.font.size = Pt(13)
    p3.font.color.rgb = C_NEGRO

    # =========================================================================
    # SLIDE 2: ENTREVISTA Y RELEVAMIENTO (Kit Pág. 10)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "F A S E   0   ·   R E L E V A M I E N T O   ( 2 2 / 0 8 / 2 0 2 6 )", "La Entrevista Inicial y Detección de Fricciones")
    add_footer(s2)

    # Left text
    tx_l = s2.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(4.8), Inches(4.6))
    tf_l = tx_l.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "Relevamiento presencial en Gomería 'El Puente' junto a la encargada de mostrador. Se analizaron los flujos diarios de atención a choferes y flotas corporativas, identificando cuellos de botella críticos en la confección de remitos y conciliación de cuentas."
    p.font.name = "Calibri"
    p.font.size = Pt(15)
    p.font.color.rgb = C_NEGRO

    p2 = tf_l.add_paragraph()
    p2.space_before = Pt(16)
    p2.text = "Requisito central del cliente: Desarrollar una herramienta local, ágil y visualmente clara, capaz de registrar un remito en menos de un minuto y erradicar los errores en alícuotas impositivas."
    p2.font.name = "Calibri"
    p2.font.size = Pt(13.5)
    p2.font.color.rgb = C_GRIS

    # Right list (3 items with circle !)
    items_s2 = [
        ("Pérdida y deterioro de comprobantes", "Uso exclusivo de talonarios de papel carbónico. Si el chofer se llevaba el remito o se dañaba la copia, se perdía el seguimiento y cobro del trabajo."),
        ("Error en liquidación de IVA y tarifas", "Cálculo manual en calculadora para 3 listas de precios (L1, L2, L3) generando constantes discrepancias del 21% según condición fiscal."),
        ("Descontrol de cheques diferidos y personal", "E-checks asentados en cuadernos con fechas de cobro vencidas y ausencias de operarios descontadas a mano sin trazabilidad.")
    ]
    top_pos = Inches(1.8)
    for title_it, desc_it in items_s2:
        # circle !
        circle = s2.shapes.add_shape(MSO_SHAPE.OVAL, Inches(6.0), top_pos + Inches(0.05), Inches(0.55), Inches(0.55))
        circle.fill.solid()
        circle.fill.fore_color.rgb = C_AZUL_CLARO
        circle.line.fill.background()
        tf_c = circle.text_frame
        tf_c.vertical_anchor = pptx.enum.text.MSO_ANCHOR.MIDDLE
        p_c = tf_c.paragraphs[0]
        p_c.text = "!"
        p_c.alignment = PP_ALIGN.CENTER
        p_c.font.name = "Arial"
        p_c.font.size = Pt(16)
        p_c.font.bold = True
        p_c.font.color.rgb = C_AZUL

        # Text item
        tx_item = s2.shapes.add_textbox(Inches(6.75), top_pos, Inches(5.7), Inches(1.2))
        tf_it = tx_item.text_frame
        tf_it.word_wrap = True
        p_it1 = tf_it.paragraphs[0]
        p_it1.text = title_it
        p_it1.font.name = "Arial"
        p_it1.font.size = Pt(15)
        p_it1.font.bold = True
        p_it1.font.color.rgb = C_NEGRO

        p_it2 = tf_it.add_paragraph()
        p_it2.space_before = Pt(4)
        p_it2.text = desc_it
        p_it2.font.name = "Calibri"
        p_it2.font.size = Pt(13)
        p_it2.font.color.rgb = C_GRIS

        top_pos += Inches(1.5)

    # =========================================================================
    # SLIDE 3: ANTES Y DESPUÉS (Kit Pág. 17)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "D I A G N Ó S T I C O   O P E R A T I V O", "Transformación del Taller: Antes y Después")
    add_footer(s3)

    # Left card: ANTES
    c_left = add_card(s3, Inches(0.8), Inches(1.8), Inches(5.3), Inches(4.7))
    # Pill ANTES
    pill_a = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(2.1), Inches(1.6), Inches(0.45))
    pill_a.fill.solid()
    pill_a.fill.fore_color.rgb = C_ROJO_CLARO
    pill_a.line.fill.background()
    p = pill_a.text_frame.paragraphs[0]
    p.text = "ANTES"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Calibri"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_ROJO

    tx_antes = s3.shapes.add_textbox(Inches(1.2), Inches(2.75), Inches(4.5), Inches(3.5))
    tf_a = tx_antes.text_frame
    tf_a.word_wrap = True
    antes_lines = [
        "• Talonarios de papel físicos y carbónicos lentos de transcribir.",
        "• Cálculos a mano de IVA (21%) según cliente y tipo de remito.",
        "• Hasta 2 horas semanales para conciliar la cuenta de cada empresa.",
        "• Sin respaldo digital ante rotura, robo o extravío físico.",
        "• Descuentos de sueldos por faltas anotados en libretas."
    ]
    for idx, l in enumerate(antes_lines):
        p = tf_a.paragraphs[0] if idx == 0 else tf_a.add_paragraph()
        if idx > 0: p.space_before = Pt(10)
        p.text = l
        p.font.name = "Calibri"
        p.font.size = Pt(14)
        p.font.color.rgb = C_GRIS

    # Arrow circle in middle
    arrow_circle = s3.shapes.add_shape(MSO_SHAPE.OVAL, Inches(6.35), Inches(3.75), Inches(0.65), Inches(0.65))
    arrow_circle.fill.solid()
    arrow_circle.fill.fore_color.rgb = C_AZUL
    arrow_circle.line.fill.background()
    p_ar = arrow_circle.text_frame.paragraphs[0]
    p_ar.text = "→"
    p_ar.alignment = PP_ALIGN.CENTER
    p_ar.font.name = "Arial"
    p_ar.font.size = Pt(18)
    p_ar.font.bold = True
    p_ar.font.color.rgb = C_BLANCO

    # Right card: DESPUÉS
    c_right = add_card(s3, Inches(7.2), Inches(1.8), Inches(5.3), Inches(4.7))
    # Pill DESPUÉS
    pill_d = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.6), Inches(2.1), Inches(1.6), Inches(0.45))
    pill_d.fill.solid()
    pill_d.fill.fore_color.rgb = C_VERDE_CLARO
    pill_d.line.fill.background()
    p = pill_d.text_frame.paragraphs[0]
    p.text = "DESPUÉS"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Calibri"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = C_VERDE

    tx_desp = s3.shapes.add_textbox(Inches(7.6), Inches(2.75), Inches(4.5), Inches(3.5))
    tf_d = tx_desp.text_frame
    tf_d.word_wrap = True
    desp_lines = [
        "• Carga digital en menos de 45 seg con foto del papel adjunta.",
        "• Discriminación automática de condición fiscal y lista L1-L3.",
        "• Exportación a Excel mensualizado en 1 clic y saldos en vivo.",
        "• Respaldo atómico ZIP restaurable (Base SQLite + Fotos).",
        "• Registro diario de ausencias con descuento proporcional automático."
    ]
    for idx, l in enumerate(desp_lines):
        p = tf_d.paragraphs[0] if idx == 0 else tf_d.add_paragraph()
        if idx > 0: p.space_before = Pt(10)
        p.text = l
        p.font.name = "Calibri"
        p.font.size = Pt(14)
        p.font.color.rgb = C_NEGRO

    # =========================================================================
    # SLIDE 4: OBJETIVOS Y ALCANCES (Kit Pág. 12)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "D E L I M I T A C I Ó N   D E L   P R O Y E C T O", "Objetivos y Definición de Alcance")
    add_footer(s4)

    # Panel In-Scope (Blanco)
    c_in = add_card(s4, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.7))
    tx_in = s4.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.3))
    tf_in = tx_in.text_frame
    tf_in.word_wrap = True
    p = tf_in.paragraphs[0]
    p.text = "DENTRO DEL ALCANCE (IN-SCOPE)"
    p.font.name = "Arial"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_NEGRO

    in_items = [
        "• Módulo Mataburros: emisión ágil de remitos OI y OIB.",
        "• Validación algorítmica de CUIT por módulo 11 de AFIP y duplicados.",
        "• 3 listas de precios simultáneas (L1 Mostrador, L2 Flota, L3 Cta Cte).",
        "• Cartera de cheques diferidos con buscador interactivo Choices.js.",
        "• Control semanal de operarios, registro de ausencias y adelantos.",
        "• Vista imprimible formal adaptada a PDF y exportaciones a Excel."
    ]
    for idx, it in enumerate(in_items):
        p = tf_in.add_paragraph()
        p.space_before = Pt(8)
        p.text = it
        p.font.name = "Calibri"
        p.font.size = Pt(13)
        p.font.color.rgb = C_GRIS

    # Panel Out-of-Scope (Azul)
    c_out = add_card(s4, Inches(6.9), Inches(1.8), Inches(5.6), Inches(4.7), bg_color=C_AZUL, border_color=None)
    tx_out = s4.shapes.add_textbox(Inches(7.2), Inches(2.0), Inches(5.0), Inches(4.3))
    tf_out = tx_out.text_frame
    tf_out.word_wrap = True
    p = tf_out.paragraphs[0]
    p.text = "FUERA DEL ALCANCE (OUT-OF-SCOPE)"
    p.font.name = "Arial"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_BLANCO

    out_items = [
        "• Facturación electrónica directa con WebService AFIP (el taller opera con remito interno formal de control).",
        "• Infraestructura en la nube / Hosting web (descartado: se ejecuta 100% en local con iniciar.bat en la PC del taller).",
        "• Aplicación móvil para choferes (la atención es presencial en mostrador).",
        "• Pasarelas de cobro online (MercadoPago/tarjetas descartadas por política comercial de cheques y transferencias).",
        "• Inventario físico de neumáticos nuevos (reservado para fase posterior)."
    ]
    for idx, it in enumerate(out_items):
        p = tf_out.add_paragraph()
        p.space_before = Pt(8)
        p.text = it
        p.font.name = "Calibri"
        p.font.size = Pt(13)
        p.font.color.rgb = C_AZUL_CLARO

    # =========================================================================
    # SLIDE 5: ROLES Y RESPONSABILIDADES (Kit Pág. 8)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "O R G A N I Z A C I Ó N   Y   P E R M I S O S", "Matriz de Roles y Responsabilidades")
    add_footer(s5)

    roles_data = [
        ("A", "Administrador", "Dueño del Taller", "Rol admin en sistema. Control de usuarios, administración del tarifario L1-L3, liquidación semanal de sueldos y descarga de backups atómicos."),
        ("O", "Operaria", "Mostrador y Facturación", "Rol usuario en sistema. Confección de remitos en Mataburros, consulta de clientes, registro de pagos y seguimiento de cartera de cheques."),
        ("T", "Operarios", "Personal de Fosa", "Personal operativo de taller. Sujetos de control de gestión: registro diario de ausencias, vales de adelantos y cálculo proporcional de haberes."),
        ("D", "Desarrollador", "Líder de Proyecto & QA", "[ COMPLETAR: Tu Nombre ]. Relevamiento funcional, diseño de arquitectura Flask/SQLite, 90 tests automatizados y puesta en marcha.")
    ]

    card_w = Inches(2.7)
    left_start = Inches(0.8)
    gap = Inches(0.3)

    for idx, (letter, title_r, sub_r, desc_r) in enumerate(roles_data):
        cur_left = left_start + idx * (card_w + gap)
        add_card(s5, cur_left, Inches(1.8), card_w, Inches(4.7))

        # Circle icon
        circ = s5.shapes.add_shape(MSO_SHAPE.OVAL, cur_left + Inches(0.95), Inches(2.1), Inches(0.8), Inches(0.8))
        circ.fill.solid()
        circ.fill.fore_color.rgb = C_AZUL
        circ.line.fill.background()
        p_c = circ.text_frame.paragraphs[0]
        p_c.text = letter
        p_c.alignment = PP_ALIGN.CENTER
        p_c.font.name = "Arial"
        p_c.font.size = Pt(20)
        p_c.font.bold = True
        p_c.font.color.rgb = C_BLANCO

        # Card text
        tx_r = s5.shapes.add_textbox(cur_left + Inches(0.2), Inches(3.1), cur_left + card_w - Inches(0.4), Inches(3.2))
        tf_r = tx_r.text_frame
        tf_r.word_wrap = True

        p1 = tf_r.paragraphs[0]
        p1.text = title_r
        p1.font.name = "Arial"
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = C_NEGRO

        p2 = tf_r.add_paragraph()
        p2.space_before = Pt(4)
        p2.text = sub_r
        p2.font.name = "Calibri"
        p2.font.size = Pt(12)
        p2.font.bold = True
        p2.font.color.rgb = C_AZUL

        p3 = tf_r.add_paragraph()
        p3.space_before = Pt(12)
        p3.text = desc_r
        p3.font.name = "Calibri"
        p3.font.size = Pt(12)
        p3.font.color.rgb = C_GRIS

    # =========================================================================
    # SLIDE 6: METODOLOGÍA ÁGIL (Kit Pág. 19 - Tablero Kanban)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "M E T O D O L O G Í A   Á G I L", "Marco Scrumban y Adaptación al Cambio")
    add_footer(s6)

    kanban_cols = [
        ("Por hacer", C_AMBAR, C_AMBAR_CLARO, Inches(0.8), [
            "Product Backlog priorizado por valor comercial para el taller.",
            "Criterio DoD estricto: pruebas unitarias aprobadas y linters flake8.",
            "Historias de usuario enfocadas en rapidez operativa en mostrador."
        ]),
        ("En curso", C_AZUL, C_AZUL_CLARO, Inches(4.8), [
            "Sprints cortos de 1 a 2 semanas con feedback directo en el taller.",
            "Requerimiento emergente: Tareas temporales sin alterar catálogo.",
            "Personalización visual adaptada a la operaria: Modo Milagritos."
        ]),
        ("Listo", C_VERDE, C_VERDE_CLARO, Inches(8.8), [
            "Más de 85 commits documentados en repositorio Git.",
            "Lanzador iniciar.bat de 1 solo clic para entorno Windows.",
            "Manual de usuario en PDF y plan de capacitación interactivo 1 a 1."
        ])
    ]

    col_w = Inches(3.733)
    for col_title, text_c, bg_c, c_left, tasks_k in kanban_cols:
        # Column background
        col_bg = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_left, Inches(1.8), col_w, Inches(4.7))
        col_bg.fill.solid()
        col_bg.fill.fore_color.rgb = bg_c
        col_bg.line.fill.background()

        # Header text
        tx_h = s6.shapes.add_textbox(c_left + Inches(0.3), Inches(2.0), col_w - Inches(0.6), Inches(0.5))
        p = tx_h.text_frame.paragraphs[0]
        p.text = col_title
        p.font.name = "Arial"
        p.font.size = Pt(17)
        p.font.bold = True
        p.font.color.rgb = text_c

        # Mini cards
        card_top = Inches(2.6)
        for t_text in tasks_k:
            mini_card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_left + Inches(0.25), card_top, col_w - Inches(0.5), Inches(1.15))
            mini_card.fill.solid()
            mini_card.fill.fore_color.rgb = C_BLANCO
            mini_card.line.color.rgb = C_BORDE
            mini_card.line.width = Pt(1)

            tf_m = mini_card.text_frame
            tf_m.word_wrap = True
            p_m = tf_m.paragraphs[0]
            p_m.text = t_text
            p_m.font.name = "Calibri"
            p_m.font.size = Pt(12)
            p_m.font.color.rgb = C_NEGRO

            card_top += Inches(1.25)

    # =========================================================================
    # SLIDE 7: CRONOGRAMA Y CAMINO CRÍTICO (Kit Pág. 5)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_header(s7, "P L A N I F I C A C I Ó N   T E M P O R A L", "Cronograma de Gantt y Camino Crítico")
    add_footer(s7)

    # Left text card
    c_gantt_txt = add_card(s7, Inches(0.8), Inches(1.8), Inches(5.4), Inches(4.7))
    tx_gt = s7.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(4.8), Inches(4.3))
    tf_gt = tx_gt.text_frame
    tf_gt.word_wrap = True

    p = tf_gt.paragraphs[0]
    p.text = "CADENA CRÍTICA (CPM)"
    p.font.name = "Arial"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = C_NEGRO

    p_flow = tf_gt.add_paragraph()
    p_flow.space_before = Pt(8)
    p_flow.text = "Relevamiento (5d) → Modelo SQLite (3d) → Mataburros L1-L3 (10d) → Historial/Excel (8d) → QA y Seguridad (6d)"
    p_flow.font.name = "Calibri"
    p_flow.font.size = Pt(12.5)
    p_flow.font.bold = True
    p_flow.font.color.rgb = C_AZUL

    gt_points = [
        "• Tareas sin holgura: Cualquier desvío en el núcleo de remitos retrasaba directamente la entrega final.",
        "• Eficiencia de ejecución: 14 de las 20 tareas de desarrollo concluyeron antes de la fecha estimada.",
        "• Control de desvíos: Se absorbió la complejidad del cálculo inteligente de IVA sin posponer entregas.",
        "• Hito de Cierre: Sábado 21 de Noviembre de 2026 (Versión 1.0 oficial lista para producción)."
    ]
    for idx, pt in enumerate(gt_points):
        p = tf_gt.add_paragraph()
        p.space_before = Pt(10)
        p.text = pt
        p.font.name = "Calibri"
        p.font.size = Pt(12)
        p.font.color.rgb = C_GRIS

    # Right area for Gantt screenshot
    c_gantt_img = add_card(s7, Inches(6.5), Inches(1.8), Inches(6.0), Inches(4.7))
    tf_gi = c_gantt_img.text_frame
    tf_gi.vertical_anchor = pptx.enum.text.MSO_ANCHOR.MIDDLE
    p = tf_gi.paragraphs[0]
    p.text = "[ INSERTAR CAPTURA DE GANTT ]\n\ndocs/Extras/Gantt - SG Gomez Miño.xlsx\n(Pegar acá la captura del cronograma y barras)"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Calibri"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_AZUL

    # =========================================================================
    # SLIDE 8: ARQUITECTURA TÉCNICA (Kit Pág. 9 - Grilla 3 + 2)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_header(s8, "A R Q U I T E C T U R A   D E   S O F T W A R E", "Diseño Arquitectónico y Modelo Relacional")
    add_footer(s8)

    # Top 3 cards
    top_cards = [
        ("1", "Backend Modular", "Python 3 + Flask 3.1 modularizado en Blueprints (routes/) y servicios desacoplados (services/). Lógica de negocio 100% aislada."),
        ("2", "Base de Datos", "SQLite 3 relacional transaccional (ACID) con claves foráneas activadas (PRAGMA foreign_keys = ON) y reglas RESTRICT / CASCADE."),
        ("3", "Frontend Jinja2", "HTML5 + Jinja2 con plantilla base.html unificada, inyección de contexto global, Bootstrap 5.3 responsivo y hojas CSS propias.")
    ]
    w_top = Inches(3.733)
    for idx, (num, tit, desc) in enumerate(top_cards):
        c_left = Inches(0.8) + idx * (w_top + Inches(0.25))
        card = add_card(s8, c_left, Inches(1.8), w_top, Inches(2.2))

        tx = s8.shapes.add_textbox(c_left + Inches(0.2), Inches(1.9), w_top - Inches(0.4), Inches(2.0))
        tf = tx.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = f"{num}. {tit}"
        p1.font.name = "Arial"
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = C_NEGRO

        p2 = tf.add_paragraph()
        p2.space_before = Pt(6)
        p2.text = desc
        p2.font.name = "Calibri"
        p2.font.size = Pt(12)
        p2.font.color.rgb = C_GRIS

    # Bottom 2 cards
    bot_cards = [
        ("4", "Interactividad Asíncrona (JS ES6)", "JavaScript nativo con fetch para conmutación de estados de pago sin recargar la página. Choices.js para selección predictiva de clientes en remitos y cheques."),
        ("5", "Seguridad, Auditoría y Resguardo", "Hash criptográfico con sal en contraseñas (werkzeug.security), decoradores de rol (@login_requerido, @solo_admin), auditoría en log y backup atómico ZIP.")
    ]
    w_bot = Inches(5.72)
    for idx, (num, tit, desc) in enumerate(bot_cards):
        c_left = Inches(0.8) + idx * (w_bot + Inches(0.28))
        card = add_card(s8, c_left, Inches(4.3), w_bot, Inches(2.2))

        tx = s8.shapes.add_textbox(c_left + Inches(0.3), Inches(4.45), w_bot - Inches(0.6), Inches(1.9))
        tf = tx.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = f"{num}. {tit}"
        p1.font.name = "Arial"
        p1.font.size = Pt(15)
        p1.font.bold = True
        p1.font.color.rgb = C_NEGRO

        p2 = tf.add_paragraph()
        p2.space_before = Pt(6)
        p2.text = desc
        p2.font.name = "Calibri"
        p2.font.size = Pt(12)
        p2.font.color.rgb = C_GRIS

    # =========================================================================
    # SLIDE 9: CRITERIOS DE ACEPTACIÓN Y CALIDAD (Kit Pág. 13 - Filas de lista)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_bg(s9)
    add_header(s9, "A S E G U R A M I E N T O   D E   C A L I D A D   ( Q A )", "Criterios de Aceptación y Validación Automatizada")
    add_footer(s9)

    qa_rows = [
        ("Validación de CUIT en tiempo real", "Algoritmo módulo 11 de AFIP y verificación asíncrona de duplicados vía API separada antes del guardado."),
        ("Estandarización de talonario", "Formato estricto: 5 dígitos numéricos para OI (oficial) y prefijo 00 + 4 dígitos para OIB (secundario)."),
        ("Regla de jerarquía tarifaria", "Control automático en el catálogo de tareas garantizando la coherencia comercial: L1 (base) ≤ L2 (flota) ≤ L3 (cta cte)."),
        ("Aislamiento de entorno de pruebas", "Infraestructura de test con base SQLite temporal en memoria que previene bloqueos de concurrencia y no ensucia la base real."),
        ("Suite de 90 tests automatizados", "100% de pruebas unitarias e integrales aprobadas con 91% de cobertura de código verificada en unittest y pytest.")
    ]

    top_pos = Inches(1.8)
    for title_r, desc_r in qa_rows:
        row_card = add_card(s9, Inches(0.8), top_pos, Inches(11.7), Inches(0.82))
        tx = s9.shapes.add_textbox(Inches(1.1), top_pos + Inches(0.08), Inches(11.1), Inches(0.65))
        tf = tx.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title_r.upper() + "   —   "
        p.font.name = "Arial"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_AZUL

        run = p.add_run()
        run.text = desc_r
        run.font.name = "Calibri"
        run.font.size = Pt(13)
        run.font.bold = False
        run.font.color.rgb = C_NEGRO

        top_pos += Inches(0.95)

    # =========================================================================
    # SLIDE 10: COSTOS Y PRESUPUESTO (Kit Pág. 11 - Tabla editable)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_bg(s10)
    add_header(s10, "E S T U D I O   D E   C O S T O S   Y   E S F U E R Z O", "Matriz de Costos del Proyecto (Régimen: 2 hs/día)")
    add_footer(s10)

    # Table
    rows = 7
    cols = 5
    table_shape = s10.shapes.add_table(rows, cols, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.3))
    t = table_shape.table
    t.columns[0].width = Inches(3.6)
    t.columns[1].width = Inches(1.8)
    t.columns[2].width = Inches(2.1)
    t.columns[3].width = Inches(1.8)
    t.columns[4].width = Inches(2.4)

    headers = ["Actividad / Rubro", "Días Reales", "Valor x Hora", "Horas x Día", "Total Actividad"]
    for col_idx, h_text in enumerate(headers):
        cell = t.cell(0, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = C_AZUL
        p = cell.text_frame.paragraphs[0]
        p.text = h_text
        p.font.name = "Arial"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_BLANCO
        p.alignment = PP_ALIGN.CENTER if col_idx > 0 else PP_ALIGN.LEFT

    table_data = [
        ("Días de Análisis de Requerimientos", "5 días", "$7.000", "2 hs", "$70.000"),
        ("Días de Diseño de Interfaces (UI/UX)", "3 días", "$6.500", "2 hs", "$39.000"),
        ("Días de Programación y Construcción", "70 días", "$10.000", "2 hs", "$1.400.000"),
        ("Días de Pruebas y Aseguramiento (QA)", "10 días", "$6.000", "2 hs", "$120.000"),
        ("Días de Documentación y Manuales", "14 días", "$5.000", "2 hs", "$140.000"),
        ("TOTAL GENERAL DEL PROYECTO", "—", "—", "—", "$1.769.000 ARS")
    ]

    for row_idx, r_data in enumerate(table_data, start=1):
        is_total = (row_idx == 6)
        for col_idx, val in enumerate(r_data):
            cell = t.cell(row_idx, col_idx)
            cell.fill.solid()
            if is_total:
                cell.fill.fore_color.rgb = C_AZUL_CLARO
            else:
                cell.fill.fore_color.rgb = C_BLANCO if row_idx % 2 == 1 else C_CREMA

            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = "Arial" if is_total else "Calibri"
            p.font.size = Pt(13) if is_total else Pt(12.5)
            p.font.bold = is_total or (col_idx == 4)
            p.font.color.rgb = C_AZUL if is_total else C_NEGRO
            p.alignment = PP_ALIGN.CENTER if col_idx > 0 else PP_ALIGN.LEFT

    # Note below table
    tx_note = s10.shapes.add_textbox(Inches(0.8), Inches(6.25), Inches(11.7), Inches(0.4))
    p = tx_note.text_frame.paragraphs[0]
    p.text = "* Stack 100% Open Source y hardware local ($0 en licencias e infraestructura). Retorno de inversión (ROI) estimado en 4 a 6 meses."
    p.font.name = "Calibri"
    p.font.size = Pt(11)
    p.font.color.rgb = C_GRIS

    # =========================================================================
    # SLIDE 11: MÉTRICAS Y KPIS (Kit Pág. 16 - Datos destacados)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_bg(s11)
    add_header(s11, "R E S U L T A D O S   Y   M É T R I C A S", "Indicadores Clave de Rendimiento (KPI)")
    add_footer(s11)

    kpi_cards = [
        ("< 45 seg", "Tiempo en Mostrador", "Reducción drástica frente a los 5 a 7 minutos que demandaba la confección y cálculo en papel carbónico."),
        ("0%", "Discrepancia Impositiva", "Eliminación total de errores de cálculo en alícuotas de IVA (21%) y aplicación automática según cliente."),
        ("90 / 90", "Tests Automatizados", "100% de la suite de pruebas unitarias e integrales aprobada con 91% de cobertura de código verificada.")
    ]

    card_w = Inches(3.733)
    for idx, (num_k, tit_k, desc_k) in enumerate(kpi_cards):
        c_left = Inches(0.8) + idx * (card_w + Inches(0.25))
        add_card(s11, c_left, Inches(1.8), card_w, Inches(4.7))

        tx = s11.shapes.add_textbox(c_left + Inches(0.3), Inches(2.2), card_w - Inches(0.6), Inches(4.0))
        tf = tx.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = num_k
        p1.font.name = "Arial"
        p1.font.size = Pt(40)
        p1.font.bold = True
        p1.font.color.rgb = C_AZUL

        p2 = tf.add_paragraph()
        p2.space_before = Pt(14)
        p2.text = tit_k
        p2.font.name = "Arial"
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = C_NEGRO

        p3 = tf.add_paragraph()
        p3.space_before = Pt(10)
        p3.text = desc_k
        p3.font.name = "Calibri"
        p3.font.size = Pt(13)
        p3.font.color.rgb = C_GRIS

    # =========================================================================
    # SLIDE 12: CIERRE Y PREGUNTAS (Kit Pág. 24)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_bg(s12)

    tx_close = s12.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.333), Inches(3.0))
    tf_c = tx_close.text_frame
    tf_c.word_wrap = True

    p0 = tf_c.paragraphs[0]
    p0.text = "¡GRACIAS!"
    p0.alignment = PP_ALIGN.CENTER
    p0.font.name = "Arial"
    p0.font.size = Pt(48)
    p0.font.bold = True
    p0.font.color.rgb = C_NEGRO

    p1 = tf_c.add_paragraph()
    p1.space_before = Pt(14)
    p1.text = "Preguntas y comentarios son bienvenidos"
    p1.alignment = PP_ALIGN.CENTER
    p1.font.name = "Calibri"
    p1.font.size = Pt(18)
    p1.font.color.rgb = C_GRIS

    p2 = tf_c.add_paragraph()
    p2.space_before = Pt(30)
    p2.text = "E L   P U E N T E   G O M E R Í A"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.name = "Calibri"
    p2.font.size = Pt(13)
    p2.font.bold = True
    p2.font.color.rgb = C_AZUL

    p3 = tf_c.add_paragraph()
    p3.space_before = Pt(20)
    p3.text = "[ Espacio disponible para demostración en vivo del sistema con iniciar.bat ]"
    p3.alignment = PP_ALIGN.CENTER
    p3.font.name = "Calibri"
    p3.font.size = Pt(12)
    p3.font.color.rgb = C_GRIS

    output_path = r"C:\dev\gomeria\sg-gomeria\docs\Presentacion_Gomeria_El_Puente.pptx"
    prs.save(output_path)
    print("SUCCESS: Presentation PPTX created at:", output_path)

if __name__ == "__main__":
    create_presentation()
