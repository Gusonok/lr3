import os
import sys
import docx
from docx.shared import Inches, Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Установка внутренних отступов ячейки таблицы в dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex):
    """Установка фонового цвета ячейки."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)

def set_table_borders(table, color="B0B0B0", sz="4", val="single"):
    """Установка аккуратных границ таблицы."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>\n'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'  <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>\n'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def make_row_cant_split(row):
    """Запрет разрыва строки таблицы при переходе на новую страницу."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:cantSplit'))

def set_repeat_header(row):
    """Повторение шапки таблицы на каждой странице при разрыве."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement('w:tblHeader'))

def add_heading_clean(doc, text, level=1, page_break_before=False):
    """Добавляет заголовок в стандартном строгом академическом стиле (без маркеров!)."""
    p = doc.add_paragraph(style=f'Heading {level}')
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6 if level == 1 else 4)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.page_break_before = page_break_before
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_body_p(doc, text, bold_prefix=None):
    """Основной абзац по ГОСТ (14pt Times New Roman, 1.5 интервал, 1.25 см отступ, по ширине)."""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.first_line_indent = Mm(12.5)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.font.name = 'Times New Roman'
        r_bold.font.size = Pt(14)
        r_bold.font.bold = True
        r_bold.font.color.rgb = RGBColor(0, 0, 0)
        
    r_text = p.add_run(text)
    r_text.font.name = 'Times New Roman'
    r_text.font.size = Pt(14)
    r_text.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_bullet_p(doc, text, bold_prefix=None):
    """Маркированный пункт списка с абзацным отступом."""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.first_line_indent = Mm(12.5)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.space_before = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    r_bullet = p.add_run("– ")
    r_bullet.font.name = 'Times New Roman'
    r_bullet.font.size = Pt(14)
    
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.font.name = 'Times New Roman'
        r_bold.font.size = Pt(14)
        r_bold.font.bold = True
        r_bold.font.color.rgb = RGBColor(0, 0, 0)
        
    r_text = p.add_run(text)
    r_text.font.name = 'Times New Roman'
    r_text.font.size = Pt(14)
    r_text.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_code_snippet(doc, code_str):
    """Компактный аккуратный блок исходного кода."""
    lines = code_str.strip().split('\n')
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.first_line_indent = Mm(0)
        p.paragraph_format.left_indent = Mm(12.5)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        stripped_l = line.lstrip(' ')
        leading_spaces_count = len(line) - len(stripped_l)
        display_line = ('\u00A0' * leading_spaces_count) + stripped_l if leading_spaces_count > 0 else (line if line else ' ')
        
        run = p.add_run(display_line)
        run.font.name = 'Courier New'
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(30, 30, 30)
        
        t_nodes = run._r.xpath('./w:t')
        if t_nodes:
            t_nodes[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

def add_figure_with_caption(doc, img_path, caption_text, width_mm=150):
    """Вставка рисунка с центрированием и подписью по ГОСТ."""
    if os.path.exists(img_path):
        p_img = doc.add_paragraph()
        p_img.paragraph_format.line_spacing = 1.0
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(4)
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_img = p_img.add_run()
        run_img.add_picture(img_path, width=Mm(width_mm))
        
        p_cap = doc.add_paragraph()
        p_cap.paragraph_format.line_spacing = 1.15
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(8)
        p_cap.paragraph_format.keep_with_next = False
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = 'Times New Roman'
        r_cap.font.size = Pt(12)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGBColor(40, 40, 40)

def main():
    doc = docx.Document()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Поля страницы по ГОСТ 7.32-2017: Левое - 30 мм, Правое - 15 мм, Верхнее - 20 мм, Нижнее - 20 мм
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(20)
    section.bottom_margin = Mm(20)
    section.left_margin = Mm(30)
    section.right_margin = Mm(15)
    
    # 2. Особый колонтитул первой страницы (без номера страницы, только город и год)
    section.different_first_page_header_footer = True
    
    first_footer = section.first_page_footer
    p_first_foot = first_footer.paragraphs[0]
    p_first_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ff = p_first_foot.add_run("Таганрог 2026")
    r_ff.font.name = "Times New Roman"
    r_ff.font.size = Pt(14)
    r_ff.font.color.rgb = RGBColor(0, 0, 0)
    
    # Последующие страницы — номер страницы по центру внизу
    normal_footer = section.footer
    p_norm_foot = normal_footer.paragraphs[0]
    p_norm_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_nf = p_norm_foot.add_run()
    r_nf.font.name = "Times New Roman"
    r_nf.font.size = Pt(14)
    r_nf.font.color.rgb = RGBColor(0, 0, 0)
    fldSimple = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls('w'))
    r_nf._r.append(fldSimple)

    # 3. Настройка базовых стилей шрифтов
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(14)
    style_normal.font.color.rgb = RGBColor(0, 0, 0)
    
    for lvl in [1, 2, 3]:
        st = doc.styles[f'Heading {lvl}']
        st.font.name = 'Times New Roman'
        st.font.size = Pt(14)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)

    # ==========================================
    # СТРАНИЦА 1: ТИТУЛЬНЫЙ ЛИСТ (БЕЗ ЗНАКОВ И КАРТИНОК)
    # ==========================================
    p_top = doc.add_paragraph()
    p_top.paragraph_format.line_spacing = 1.0
    p_top.paragraph_format.space_before = Pt(0)
    p_top.paragraph_format.space_after = Pt(2)
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_top.add_run("Министерство науки и высшего образования Российской Федерации\n"
                      "Федеральное государственное автономное образовательное учреждение высшего образования\n"
                      "«ЮЖНЫЙ ФЕДЕРАЛЬНЫЙ УНИВЕРСИТЕТ»\n"
                      "(ФГАОУ ВО «ЮФУ»)\n"
                      "Институт компьютерных технологий и информационной безопасности\n"
                      "Информационная безопасность телекоммуникационных систем")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(14)

    # Отступ перед заголовком отчета (заменяет графический знак)
    p_space = doc.add_paragraph()
    p_space.paragraph_format.line_spacing = 1.0
    p_space.paragraph_format.space_before = Pt(36)
    p_space.paragraph_format.space_after = Pt(0)

    p_title = doc.add_paragraph()
    p_title.paragraph_format.line_spacing = 1.15
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(4)
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_title.add_run("ОТЧЕТ ПО ЛАБОРАТОРНОЙ РАБОТЕ № 3")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(16)
    r.font.bold = True

    p_disc = doc.add_paragraph()
    p_disc.paragraph_format.line_spacing = 1.15
    p_disc.paragraph_format.space_before = Pt(2)
    p_disc.paragraph_format.space_after = Pt(4)
    p_disc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_disc.add_run("по дисциплине:\n«Машинное обучение и аналитика больших данных»")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(14)

    p_topic = doc.add_paragraph()
    p_topic.paragraph_format.line_spacing = 1.15
    p_topic.paragraph_format.space_before = Pt(4)
    p_topic.paragraph_format.space_after = Pt(40)
    p_topic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_topic.add_run("на тему:\n«Высокопроизводительная геопространственная интерполяция метеорологических данных»")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(14)
    r.font.bold = True

    # Таблица исполнителей
    table_exec = doc.add_table(rows=3, cols=2)
    table_exec.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table_exec, val="none")

    exec_data = [
        ("Выполнил: студент группы КТбо3-3", "__________ Иршко\u00A0О.\u00A0А."),
        ("Выполнил: студент группы КТбо3-3", "__________ Грицынин\u00A0Н.\u00A0С."),
        ("Проверил: Ассистент ИКТИБ ЮФУ", "__________ Мельник\u00A0Я.\u00A0Э.")
    ]

    for i, (col1, col2) in enumerate(exec_data):
        row = table_exec.rows[i]
        make_row_cant_split(row)
        c1, c2 = row.cells[0], row.cells[1]
        c1.width = Mm(78)
        c2.width = Mm(87)
        set_cell_margins(c1, top=40, bottom=40, left=0, right=20)
        set_cell_margins(c2, top=40, bottom=40, left=20, right=0)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.line_spacing = 1.15
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p1.add_run(col1)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(14)
        
        p2 = c2.paragraphs[0]
        p2.paragraph_format.line_spacing = 1.15
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r2 = p2.add_run(col2)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(14)

    # ==========================================
    # СТРАНИЦА 2: АВТОСОБИРАЕМОЕ ОГЛАВЛЕНИЕ (WORD TOC FIELD)
    # ==========================================
    doc.add_page_break()
    p_toc_head = doc.add_paragraph()
    p_toc_head.paragraph_format.line_spacing = 1.5
    p_toc_head.paragraph_format.space_before = Pt(0)
    p_toc_head.paragraph_format.space_after = Pt(12)
    p_toc_head.paragraph_format.first_line_indent = Mm(0)
    p_toc_head.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_toc_h = p_toc_head.add_run("Оглавление")
    r_toc_h.font.name = 'Times New Roman'
    r_toc_h.font.size = Pt(14)
    r_toc_h.font.bold = True

    # Настоящее нативное поле оглавления Word (TOC)
    p_toc = doc.add_paragraph()
    p_toc.paragraph_format.line_spacing = 1.15
    p_toc.paragraph_format.first_line_indent = Mm(0)
    run_toc = p_toc.add_run()

    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> TOC \o "1-3" \h \z \u </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))

    run_toc._r.append(fldChar1)
    run_toc._r.append(instrText)
    run_toc._r.append(fldChar2)
    run_toc._r.append(fldChar3)

    # ==========================================
    # СТРАНИЦА 3: ЦЕЛЬ И ТЕОРИЯ
    # ==========================================
    doc.add_page_break()
    add_heading_clean(doc, "Цель работы", level=1)

    add_body_p(doc, "1. Освоить фундаментальные принципы и практические методы высокопроизводительной геопространственной интерполяции больших объемов данных на языке Python.")
    add_body_p(doc, "2. Научиться использовать специализированные геоинформационные библиотеки: расчет геодезических расстояний на сфере и эллипсоиде (pyproj), сохранение геопривязанных многомерных растров с компрессией (rasterio), организацию CLI-интерфейса (argparse).")
    add_body_p(doc, "3. Реализовать векторизованный алгоритм интерполяции методом обратно взвешенных расстояний (IDW) с пакетной обработкой строк (батчингом) для жесткого контроля оперативной памяти и потоковым вычислением временной статистики ячеек матрицы.")
    add_body_p(doc, "4. Разработать клиент-серверное расширение для распределенных вычислений на базе FastAPI в локальной сети, провести сравнительный анализ производительности и исследовать масштабируемость системы.")

    add_heading_clean(doc, "Краткие теоретические сведения", level=1)

    add_body_p(doc, "Метод обратно взвешенных расстояний (Inverse Distance Weighting, IDW) является классическим алгоритмом пространственной интерполяции, основанным на предположении, что влияние известных точек уменьшается с увеличением расстояния до оцениваемой ячейки. Значение параметра Z в точке с координатами (x, y) вычисляется как средневзвешенное по формуле:", bold_prefix="1. Метод IDW: ")
    add_body_p(doc, "Z(x, y) = [ ∑(w_i · z_i) ] / [ ∑ w_i ], где веса w_i = 1 / (d_i^p + ε). Параметр p задает степень затухания расстояния (обычно p = 2.0), d_i — физическое расстояние от целевой точки до i-й опорной станции, а ε — малая константа (например, 10⁻¹²), исключающая деление на ноль.")

    add_body_p(doc, "При работе в географической системе координат WGS84 (EPSG:4326) координаты задаются в градусах долготы и широты. Применение евклидова расстояния на градусной сетке порождает грубые искажения, поскольку длина градуса долготы зависит от широты. Модуль pyproj.Geod(ellps='WGS84') решает обратную геодезическую задачу по алгоритму Винсенти, обеспечивая точный расчет физических расстояний в метрах по поверхности земного эллипсоида.", bold_prefix="2. Геодезические расчеты на эллипсоиде WGS84: ")

    add_body_p(doc, "Для обработки сотен тысяч пикселей за 365 временных срезов циклы Python неприменимы из-за критических накладных расходов. Векторизация средствами NumPy переносит расчеты в скомпилированные библиотеки BLAS/LAPACK. В частности, интерполяция показаний станций на 365 дней сводится к единой операции матричного перемножения нормализованных весов на матрицу дневных температур станций (оператор @).", bold_prefix="3. Векторизация в NumPy: ")

    add_body_p(doc, "Хранение полного массива размером 400 × 800 × 365 элементов в формате float32 требует порядка 467 МБ RAM. При высоком разрешении сетки потребление памяти может превысить доступный объем ОЗУ. Пакетная обработка (батчинг) делит растр на горизонтальные полосы строк. Для каждого батча рассчитываются значения сразу за весь год, сворачиваются в статистику (Min, Max, Mean) и удаляются из памяти, что снижает пиковое потребление RAM более чем в 10 раз.", bold_prefix="4. Пакетная обработка (батчинг) и контроль RAM: ")

    add_body_p(doc, "Библиотека rasterio обеспечивает запись растровых данных в формат GeoTIFF с указанием системы координат (EPSG:4326), аффинного преобразования (связь индексов матрицы с географическими координатами) и сжатия LZW без потерь, уменьшающего объем файлов в 2–3 раза.", bold_prefix="5. Формат GeoTIFF и компрессия LZW: ")

    add_body_p(doc, "Для агрегации временных рядов при наличии возможных пропусков данных методичка предписывает обязательное использование nan-безопасных функций NumPy (np.nanmin, np.nanmax, np.nanmean), предотвращающих каскадную порчу статистики.", bold_prefix="6. Обработка пропущенных значений (NaN): ")

    # ==========================================
    # РАЗДЕЛ: ХОД РАБОТЫ
    # ==========================================
    add_heading_clean(doc, "Ход работы", level=1, page_break_before=True)

    add_heading_clean(doc, "1. Постановка задачи", level=2)
    add_body_p(doc, "В соответствии с Вариантом 1 («Температура воздуха») зафиксированы следующие условия:")
    add_bullet_p(doc, "Полуостров Крым (WGS84: долгота 32.4°E – 36.6°E, широта 44.3°N – 46.2°N).", bold_prefix="Регион исследования: ")
    add_bullet_p(doc, "50 станций, случайно расположенных в границах региона.", bold_prefix="Опорная сеть: ")
    add_bullet_p(doc, "температура воздуха в диапазоне от -50.0 °C до +50.0 °C на 365 дней.", bold_prefix="Параметр и диапазон: ")
    add_bullet_p(doc, "матрица 400 строк на 800 столбцов (320 000 ячеек растра).", bold_prefix="Сетка расчета: ")
    add_bullet_p(doc, "минимум, максимум, среднегодовое значение за 365 дней.", bold_prefix="Результирующие слои: ")

    add_heading_clean(doc, "2. Модульная структура программного комплекса", level=2)
    add_body_p(doc, "Проект разделен на отдельные модули в соответствии с рекомендациями методички:")
    add_bullet_p(doc, "генерация синтетической базы станций и ежедневных наблюдений в CSV-файл.", bold_prefix="data_generator.py – ")
    add_bullet_p(doc, "векторизованный расчет геодезических расстояний через pyproj, матричные веса IDW и свертка временного ряда.", bold_prefix="interpolation_core.py – ")
    add_bullet_p(doc, "потоковый расчет предварительной статистики по CSV и агрегация батчей через nan-безопасные функции NumPy.", bold_prefix="stats_calculator.py – ")
    add_bullet_p(doc, "интерфейс командной строки (argparse), диспетчер ProcessPoolExecutor, механизм батчинга и сохранение в GeoTIFF (rasterio).", bold_prefix="main.py – ")
    add_bullet_p(doc, "клиент-серверный вычислительный комплекс на базе FastAPI для параллельного расчета на двух ПК.", bold_prefix="main_distributed.py – ")
    add_bullet_p(doc, "автоматизированное тестирование производительности от 1 до 12 процессов.", bold_prefix="benchmark.py – ")

    add_heading_clean(doc, "3. Генерация входных данных (data_generator.py)", level=2)
    add_body_p(doc, "Функция generate_data создает 50 станций со случайными координатами в границах Крыма и для каждой генерирует 365 суточных значений температуры:")
    code_gen = (
        "def generate_data(filename=\"stations.csv\", num_stations=50, bounds=None):\n"
        "    if bounds is None:\n"
        "        bounds = {\"west\": 32.4, \"east\": 36.6, \"south\": 44.3, \"north\": 46.2}\n"
        "    stations = {}\n"
        "    for i in range(num_stations):\n"
        "        lat = random.uniform(bounds[\"south\"], bounds[\"north\"])\n"
        "        lon = random.uniform(bounds[\"west\"], bounds[\"east\"])\n"
        "        stations[f\"station_{i}\"] = {\"latitude\": lat, \"longitude\": lon}\n"
        "\n"
        "    with open(filename, \"w\", newline=\"\", encoding=\"utf-8\") as csvfile:\n"
        "        writer = csv.DictWriter(csvfile, fieldnames=[\"station\", \"latitude\", \"longitude\", \"day\", \"temperature\"])\n"
        "        writer.writeheader()\n"
        "        for station, coords in stations.items():\n"
        "            for day in range(1, 366):\n"
        "                writer.writerow({\"station\": station, \"latitude\": coords[\"latitude\"],\n"
        "                                 \"longitude\": coords[\"longitude\"], \"day\": day,\n"
        "                                 \"temperature\": random.uniform(-50, 50)})"
    )
    add_code_snippet(doc, code_gen)

    add_heading_clean(doc, "4. Векторизованное ядро интерполяции (interpolation_core.py)", level=2)
    add_body_p(doc, "Вычислительное ядро обрабатывает горизонтальную полосу строк. Расстояния на эллипсоиде WGS84 рассчитываются векторизованно через geod.inv(), а интерполяция на все 365 дней выполняется одним матричным умножением norm_weights @ station_temps:")
    code_core = (
        "geod = pyproj.Geod(ellps=\"WGS84\")\n"
        "\n"
        "def interpolate_batch(row_start, row_end, width, height, bounds, station_lons, station_lats, station_temps, power=2):\n"
        "    d_lon = (bounds[\"east\"] - bounds[\"west\"]) / width\n"
        "    d_lat = (bounds[\"north\"] - bounds[\"south\"]) / height\n"
        "    cols = np.arange(width)\n"
        "    rows = np.arange(row_start, row_end)\n"
        "    grid_lons, grid_lats = np.meshgrid(bounds[\"west\"] + (cols + 0.5) * d_lon,\n"
        "                                       bounds[\"north\"] - (rows + 0.5) * d_lat)\n"
        "    target_lons, target_lats = grid_lons.ravel(), grid_lats.ravel()\n"
        "    num_targets, num_stations = len(target_lons), len(station_lons)\n"
        "\n"
        "    # Векторный расчет расстояний на WGS84\n"
        "    _, _, distances = geod.inv(np.repeat(target_lons, num_stations), np.repeat(target_lats, num_stations),\n"
        "                               np.tile(station_lons, num_targets), np.tile(station_lats, num_targets))\n"
        "    dist_matrix = distances.reshape(num_targets, num_stations)\n"
        "\n"
        "    # Нормализация весов IDW\n"
        "    weights = 1.0 / (dist_matrix**power + 1e-12)\n"
        "    norm_weights = weights / np.sum(weights, axis=1, keepdims=True)\n"
        "\n"
        "    # Матричное умножение: (num_targets x 50) @ (50 x 365) -> (num_targets x 365)\n"
        "    batch_temps = norm_weights @ station_temps\n"
        "    b_min, b_max, b_mean = compute_batch_stats(batch_temps, len(rows), width)\n"
        "    return row_start, row_end, b_min, b_max, b_mean"
    )
    add_code_snippet(doc, code_core)

    add_heading_clean(doc, "5. Статистический анализ (stats_calculator.py)", level=2)
    add_body_p(doc, "Модуль реализует потоковый анализ сырого CSV-файла (без расхода оперативной памяти) и агрегацию батча температур по временной шкале через nan-безопасные функции:")
    code_stat = (
        "def compute_batch_stats(batch_temps, batch_height, width):\n"
        "    b_min = np.nanmin(batch_temps, axis=1).reshape(batch_height, width)\n"
        "    b_max = np.nanmax(batch_temps, axis=1).reshape(batch_height, width)\n"
        "    b_mean = np.nanmean(batch_temps, axis=1).reshape(batch_height, width)\n"
        "    return b_min.astype(np.float32), b_max.astype(np.float32), b_mean.astype(np.float32)"
    )
    add_code_snippet(doc, code_stat)

    add_heading_clean(doc, "6. Координация вычислений и сохранение в GeoTIFF (main.py)", level=2)
    add_body_p(doc, "В main.py высота растра (400 строк) нарезается на 8 батчей по 50 строк. Задачи передаются пулу рабочих процессов ProcessPoolExecutor, а готовые полосы монтируются в результирующие матрицы и сохраняются в GeoTIFF со сжатием LZW:")
    code_save = (
        "def save_as_geotiff(filename, raster_data, bounds, width, height):\n"
        "    transform = from_origin(bounds[\"west\"], bounds[\"north\"],\n"
        "                            (bounds[\"east\"] - bounds[\"west\"]) / width,\n"
        "                            (bounds[\"north\"] - bounds[\"south\"]) / height)\n"
        "    profile = {\"driver\": \"GTiff\", \"height\": height, \"width\": width, \"count\": 1,\n"
        "               \"dtype\": raster_data.dtype, \"crs\": \"EPSG:4326\",\n"
        "               \"transform\": transform, \"compress\": \"lzw\"}\n"
        "    with rasterio.open(filename, \"w\", **profile) as dst:\n"
        "        dst.write(raster_data, 1)"
    )
    add_code_snippet(doc, code_save)

    add_heading_clean(doc, "7. Распределенные клиент-серверные вычисления (main_distributed.py)", level=2)
    add_body_p(doc, "В рамках усложненного задания разработана распределенная архитектура на базе FastAPI. Вычислительный узел (воркер) запускается на удаленном ПК в локальной сети, принимая задачи через HTTP POST эндпоинт /compute_half. Координатор делит растр пополам (строки 0..200 и 200..400): первая половина рассчитывается локально на всех ядрах CPU, а вторая половина одновременно отправляется по сети на воркер через ThreadPoolExecutor. По завершении половины объединяются в единый растр.")

    # ==========================================
    # РАЗДЕЛ: ЭКСПЕРИМЕНТАЛЬНОЕ ИССЛЕДОВАНИЕ
    # ==========================================
    add_heading_clean(doc, "Экспериментальное исследование и сравнительный анализ", level=1, page_break_before=True)

    add_body_p(doc, "Тестирование производительности проводилось на стенде со следующими характеристиками:")
    add_bullet_p(doc, "Intel Core (8 физических ядер, 12 логических потоков).", bold_prefix="Процессор: ")
    add_bullet_p(doc, "16 ГБ DDR4/DDR5.", bold_prefix="ОЗУ: ")
    add_bullet_p(doc, "Windows 11 Pro 64-bit, Python 3.14, NumPy 2.x, pyproj 3.7, rasterio 1.4.", bold_prefix="Окружение: ")
    add_bullet_p(doc, "сетка 400 × 800 пикселей (320 000 точек), 50 станций, 365 дней, батч 50 строк.", bold_prefix="Параметры интерполяции: ")

    add_heading_clean(doc, "1. Исследование зависимости времени интерполяции от числа процессов", level=2)
    add_body_p(doc, "Скрипт benchmark.py выполнил серии контрольных прогонов на рабочей сетке 400 × 800 для конфигураций от 1 до 12 рабочих процессов. Результаты измерений представлены в таблице 1.")

    # Таблица 1
    p_t1_cap = doc.add_paragraph()
    p_t1_cap.paragraph_format.line_spacing = 1.15
    p_t1_cap.paragraph_format.space_before = Pt(8)
    p_t1_cap.paragraph_format.space_after = Pt(4)
    p_t1_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p_t1_cap.add_run("Таблица 1 – Зависимость времени выполнения интерполяции от количества процессов")
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
    r.font.bold = True

    table1 = doc.add_table(rows=6, cols=4)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table1)

    t1_headers = ["Число процессов", "Время выполнения (с)", "Ускорение (Speedup)", "Эффективность (E = S / N)"]
    row_hdr = table1.rows[0]
    make_row_cant_split(row_hdr)
    set_repeat_header(row_hdr)
    for c_idx, title in enumerate(t1_headers):
        cell = row_hdr.cells[c_idx]
        set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
        set_cell_shading(cell, "EAEAEA")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(title)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        r.font.bold = True

    t1_data = [
        ("1", "12.288", "1.00x (база)", "100.0 %"),
        ("2", "5.937", "2.07x", "103.5 %"),
        ("4", "3.429", "3.58x", "89.5 %"),
        ("8", "3.180", "3.86x", "48.3 %"),
        ("12", "3.120", "3.94x", "32.8 %")
    ]

    for r_idx, row_vals in enumerate(t1_data):
        row = table1.rows[r_idx + 1]
        make_row_cant_split(row)
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            if r_idx % 2 == 1:
                set_cell_shading(cell, "F7F7F7")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(12)
            if c_idx == 2:
                r.font.bold = True

    # Рисунок 1: lab3_benchmark_graph.png
    add_figure_with_caption(
        doc,
        os.path.join(script_dir, "lab3_benchmark_graph.png"),
        "Рисунок 1 – Зависимость времени интерполяции от количества рабочих процессов",
        width_mm=130
    )

    add_heading_clean(doc, "2. Визуализация результатов интерполяции", level=2)
    add_body_p(doc, "На основе рассчитанных слоев GeoTIFF построены пространственные картограммы температуры воздуха в Крыму за 365 дней:")

    # Рисунок 2: crimea_all_stats.png
    add_figure_with_caption(
        doc,
        os.path.join(script_dir, "crimea_all_stats.png"),
        "Рисунок 2 – Пространственные поля температур для региона Крым (Min, Mean, Max)",
        width_mm=150
    )

    add_heading_clean(doc, "3. Апробация распределенных вычислений и верификация точности", level=2)
    add_body_p(doc, "В рамках апробации клиент-серверного режима на базе FastAPI выполнен расчет растра в двухузловом режиме (Ноутбук-координатор и ПК-воркер). Для подтверждения корректности распределенной декомпозиции и склейки матриц проведено попиксельное сравнение файлов crimea_cluster_mean.tif и crimea_single_mean.tif:")
    add_body_p(doc, "Максимальная абсолютная разность значений по всем 320 000 ячейкам составила строго 0.0 (°C). Это доказывает полную числовую эквивалентность распределенного алгоритма локальному вычислению без потерь точности и искажений на стыке половин растра.")

    # ==========================================
    # РАЗДЕЛ: АНАЛИЗ И ВЫВОДЫ
    # ==========================================
    add_heading_clean(doc, "Анализ результатов экспериментов", level=1, page_break_before=False)

    add_body_p(doc, "При увеличении количества процессов с 1 до 4 время интерполяции сокращается с 12.29 с до 3.43 с, что соответствует ускорению в 3.58 раза и эффективности 89.5%. Это подтверждает высокую параллельность задачи IDW-интерполяции, где каждый батч рассчитывается независимо от других.", bold_prefix="1. Эффективность распараллеливания: ")

    add_body_p(doc, "При дальнейшем росте числа процессов (8 и 12) ускорение стабилизируется на уровне ~3.9x (3.12 с), а эффективность падает до 32.8%. Это объясняется архитектурой тестового процессора: наличие 8 физических ядер и 4 виртуальных потоков Hyper-Threading означает, что виртуальные ядра разделяют аппаратные вычислительные блоки SIMD/FPU физических ядер. Кроме того, согласно закону Амдала, ускорение ограничивается последовательными этапами (чтение CSV, формирование задач и запись GeoTIFF).", bold_prefix="2. Факторы насыщения ускорения: ")

    add_body_p(doc, "Дробление матрицы на полосы по 50 строк позволило избежать выделения монолитного трехмерного массива на 365 дней (~467 МБ). Свертка во временную статистику непосредственно в воркере снижает объем передаваемых через IPC данных до 160 КБ на батч, что исключает накладные расходы сериализации и предотвращает дефицит памяти.", bold_prefix="3. Контроль оперативной памяти (батчинг): ")

    add_body_p(doc, "Клиент-серверное решение на FastAPI успешно решило задачу распределения нагрузки: передача крупных фрагментов сетки минимизирует сетевой оверхед по сравнению с побатчевой отправкой, а нулевая разность итоговых матриц (0.0) подтверждает строгую корректность вычислений.", bold_prefix="4. Распределенная модель вычислений: ")

    add_heading_clean(doc, "ВЫВОД", level=1)

    add_body_p(doc, "В ходе выполнения лабораторной работы № 3 был разработан и всесторонне исследован высокопроизводительный программный комплекс геопространственной IDW-интерполяции метеоданных на языке Python.")
    add_body_p(doc, "1. Реализована полная векторизация математических расчетов: геодезические расстояния на эллипсоиде WGS84 рассчитываются через pyproj.Geod, а годовая интерполяция 365 дней выполняется одной операцией матричного умножения NumPy, что устранило медленные интерпретируемые циклы.")
    add_body_p(doc, "2. Механизм батчинга строк и сворачивания временного ряда с использованием nan-безопасных функций (np.nanmin, np.nanmax, np.nanmean) обеспечил жесткий контроль потребления оперативной памяти и устойчивость к пропущенным измерениям.")
    add_body_p(doc, "3. Экспорт данных выполнен в формате GeoTIFF с аффинной привязкой EPSG:4326 и компрессией LZW через rasterio, обеспечивая компактность файлов (~1.45 МБ) и совместимость с геоинформационными системами.")
    add_body_p(doc, "4. Экспериментально подтверждено 4-кратное ускорение на локальном пуле процессов concurrent.futures.ProcessPoolExecutor (сокращение времени с 12.29 с до 3.12 с).")
    add_body_p(doc, "5. Разработан распределенный комплекс на базе FastAPI, подтвердивший стабильную работу в локальной сети и 100% числовую точность результатов при межмашинной декомпозиции расчетной сетки.")

    # Сохранение документа DOCX
    output_docx = os.path.join(script_dir, "Отчет_ЛР3_Иршко_Грицынин.docx")
    doc.save(output_docx)
    print(f"Отчет DOCX сохранен: {output_docx}")

    # Автоматическое обновление автособираемого оглавления и конвертация в PDF через Word COM
    output_pdf = os.path.join(script_dir, "Отчет_ЛР3_Иршко_Грицынин.pdf")
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc_com = word.Documents.Open(output_docx)
        
        # Обновляем автособираемое оглавление средствами Word
        if doc_com.TablesOfContents.Count > 0:
            doc_com.TablesOfContents(1).Update()
        doc_com.Fields.Update()
        
        # Сохраняем обновленный docx и экспортируем в pdf
        doc_com.Save()
        doc_com.SaveAs(output_pdf, FileFormat=17) # 17 = wdFormatPDF
        doc_com.Close()
        word.Quit()
        print(f"Оглавление Word автоматически обновлено, PDF сгенерирован: {output_pdf}")
    except Exception as e:
        print(f"Предупреждение при работе с Word COM: {e}")

if __name__ == "__main__":
    main()
