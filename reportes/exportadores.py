"""
RF-14: exportación de reportes a Excel (openpyxl) y PDF (ReportLab). Ambos formatos reciben el MISMO
objeto Reporte que se muestra en pantalla, por eso el archivo coincide con lo que ve el usuario.
"""
from decimal import Decimal
from io import BytesIO

from django.utils import timezone

from inventario.excepciones import formatear_cantidad


def _texto(valor):
    if isinstance(valor, Decimal):
        return formatear_cantidad(valor)
    return "" if valor is None else str(valor)


def a_excel(reporte):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    libro = Workbook()
    hoja = libro.active
    hoja.title = reporte.titulo[:31]
    hoja.append([reporte.titulo])
    hoja["A1"].font = Font(bold=True, size=14, color="1F4E79")
    hoja.append([reporte.filtros])
    hoja.append([f"Generado: {timezone.localtime(reporte.generado_en):%d/%m/%Y %H:%M}"])
    hoja.append([])
    hoja.append(reporte.columnas)
    for celda in hoja[hoja.max_row]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E79")
    for fila in reporte.filas:
        hoja.append([valor for valor in fila])  # Decimal se guarda como número
    for i, columna in enumerate(reporte.columnas, start=1):
        ancho = max([len(columna)] + [len(_texto(f[i - 1])) for f in reporte.filas])
        hoja.column_dimensions[hoja.cell(row=5, column=i).column_letter].width = min(ancho + 2, 45)
    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def a_pdf(reporte):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida, pagesize=landscape(letter), title=reporte.titulo, author="InventarioWeb El Jardín",
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36,
    )
    estilos = getSampleStyleSheet()
    datos = [reporte.columnas] + [[_texto(v) for v in fila] for fila in reporte.filas]
    if not reporte.filas:
        datos.append(["Sin datos para los filtros seleccionados"] + [""] * (len(reporte.columnas) - 1))
    tabla = Table(datos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8B95A1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F4F8")]),
    ]))
    documento.build([
        Paragraph(reporte.titulo, estilos["Title"]),
        Paragraph(reporte.filtros, estilos["Normal"]),
        Paragraph(f"Generado: {timezone.localtime(reporte.generado_en):%d/%m/%Y %H:%M}", estilos["Normal"]),
        Spacer(1, 12),
        tabla,
    ])
    return salida.getvalue()
