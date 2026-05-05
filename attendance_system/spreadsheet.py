from __future__ import annotations

from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


XML_NS = 'http://www.w3.org/XML/1998/namespace'
MAIN_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
CONTENT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'

NS = {
    'main': MAIN_NS,
    'rel': REL_NS,
    'pkgrel': PKG_REL_NS,
    'content': CONTENT_NS,
}


def build_xlsx(headers: list[str], example_rows: list[list[str]], sheet_name: str = 'Sheet1') -> bytes:
    rows = [headers, *example_rows]
    workbook = BytesIO()
    with ZipFile(workbook, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', _content_types_xml())
        archive.writestr('_rels/.rels', _root_rels_xml())
        archive.writestr('xl/workbook.xml', _workbook_xml(sheet_name))
        archive.writestr('xl/_rels/workbook.xml.rels', _workbook_rels_xml())
        archive.writestr('xl/styles.xml', _styles_xml())
        archive.writestr('xl/worksheets/sheet1.xml', _worksheet_xml(rows))
    return workbook.getvalue()


def read_xlsx(uploaded_file) -> list[dict[str, str]]:
    with ZipFile(uploaded_file) as archive:
        shared_strings = _read_shared_strings(archive)
        sheet_path = _get_first_sheet_path(archive)
        xml_bytes = archive.read(sheet_path)

    root = ET.fromstring(xml_bytes)
    rows_by_index: dict[int, dict[int, str]] = {}

    for row in root.findall('.//main:sheetData/main:row', NS):
        row_index = int(row.attrib.get('r', '0'))
        values: dict[int, str] = {}
        for cell in row.findall('main:c', NS):
            ref = cell.attrib.get('r', '')
            column_index = _column_index_from_ref(ref)
            values[column_index] = _cell_value(cell, shared_strings).strip()
        rows_by_index[row_index] = values

    if 1 not in rows_by_index:
        raise ValueError('Excel faylda sarlavha qatori topilmadi.')

    headers_map = rows_by_index[1]
    max_column = max(headers_map.keys(), default=-1)
    headers = [headers_map.get(index, '').strip() for index in range(max_column + 1)]
    if not any(headers):
        raise ValueError('Excel sarlavhalari bo`sh.')

    parsed_rows: list[dict[str, str]] = []
    for row_index in sorted(index for index in rows_by_index.keys() if index > 1):
        row_values = rows_by_index[row_index]
        values = [row_values.get(index, '').strip() for index in range(max_column + 1)]
        if not any(values):
            continue
        parsed_rows.append({
            headers[index]: values[index]
            for index in range(len(headers))
            if headers[index]
        })
    return parsed_rows


def parse_active_value(raw_value: str, default: bool = True) -> bool:
    value = (raw_value or '').strip().lower()
    if not value:
        return default
    if value in {'faol', 'active', '1', 'ha', 'yes', 'true'}:
        return True
    if value in {'nofaol', 'inactive', '0', 'yoq', "yo'q", 'no', 'false'}:
        return False
    raise ValueError("Holat ustuni 'Faol' yoki 'Nofaol' bo'lishi kerak.")


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Types xmlns="{CONTENT_NS}">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def _workbook_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<workbook xmlns="{MAIN_NS}" xmlns:r="{REL_NS}">'
        '<sheets>'
        f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>'
        '</sheets>'
        '</workbook>'
    )


def _workbook_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<Relationships xmlns="{PKG_REL_NS}">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        '</Relationships>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<styleSheet xmlns="{MAIN_NS}">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def _worksheet_xml(rows: list[list[str]]) -> str:
    rendered_rows = []
    for row_number, row_values in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row_values):
            cell_ref = f'{_column_letters(column_index)}{row_number}'
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{escape(str(value))}</t></is></c>'
            )
        rendered_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{MAIN_NS}" xmlns:r="{REL_NS}" xmlns:xml="{XML_NS}">'
        f'<sheetData>{"".join(rendered_rows)}</sheetData>'
        '</worksheet>'
    )


def _read_shared_strings(archive: ZipFile) -> list[str]:
    if 'xl/sharedStrings.xml' not in archive.namelist():
        return []
    root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
    values = []
    for item in root.findall('main:si', NS):
        text_parts = [node.text or '' for node in item.findall('.//main:t', NS)]
        values.append(''.join(text_parts))
    return values


def _get_first_sheet_path(archive: ZipFile) -> str:
    workbook_root = ET.fromstring(archive.read('xl/workbook.xml'))
    sheet = workbook_root.find('main:sheets/main:sheet', NS)
    if sheet is None:
        raise ValueError('Excel workbook ichida sheet topilmadi.')
    rel_id = sheet.attrib.get(f'{{{REL_NS}}}id')
    rel_root = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
    target = None
    for rel in rel_root.findall('pkgrel:Relationship', NS):
        if rel.attrib.get('Id') == rel_id:
            target = rel.attrib.get('Target')
            break
    if not target:
        raise ValueError('Sheet manzili topilmadi.')
    return str(PurePosixPath('xl') / PurePosixPath(target))


def _column_letters(index: int) -> str:
    letters = ''
    current = index + 1
    while current:
        current, remainder = divmod(current - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _column_index_from_ref(cell_ref: str) -> int:
    letters = ''.join(char for char in cell_ref if char.isalpha()).upper()
    if not letters:
        return 0
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _cell_value(cell, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get('t')
    if cell_type == 'inlineStr':
        return ''.join(node.text or '' for node in cell.findall('.//main:t', NS))
    value_node = cell.find('main:v', NS)
    if value_node is None or value_node.text is None:
        return ''
    if cell_type == 's':
        shared_index = int(value_node.text)
        return shared_strings[shared_index] if shared_index < len(shared_strings) else ''
    return value_node.text
