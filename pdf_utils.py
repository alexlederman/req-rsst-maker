import io
import zipfile
import pypdf

# Values that look like placeholders and should NOT be treated as pre-filled
_PLACEHOLDER_STARTS = (
    'Select ', 'select ',
    'e.g.,', 'e.g. ',
    'Enter ', 'enter ',
    'Use format',
)
_PLACEHOLDER_EXACT = {
    'HH:MM', 'n/a', 'N/A', '/', '/Off', '/No', '\r', '\n', '',
}


def is_prefilled(value: str, field_type: str) -> bool:
    """True if a field has a meaningful pre-filled value (should show as disabled)."""
    if field_type == 'checkbox':
        return value in ('/Yes', '/')
    v = str(value).strip()
    if not v or v in _PLACEHOLDER_EXACT:
        return False
    if any(v.startswith(p) for p in _PLACEHOLDER_STARTS):
        return False
    return True


def get_fields_with_meta(pdf_path: str) -> dict:
    """
    Returns an ordered dict:
      { field_name: {'type': 'text'|'checkbox', 'label': str, 'value': str} }

    'label' uses /TU tooltip when available, otherwise the field name.
    'value' is the current /V value (empty string if none/placeholder).
    """
    reader = pypdf.PdfReader(pdf_path)
    raw = reader.get_fields()
    if not raw:
        return {}

    result = {}
    for name, f in raw.items():
        ft = f.get('/FT')

        tu = f.get('/TU', '') or ''
        tu = str(tu).strip()

        v = f.get('/V')
        v = '' if v is None else str(v)

        result[name] = {
            'type': 'checkbox' if ft == '/Btn' else 'text',
            'label': tu if tu else name,
            'value': v,
        }
    return result


def get_fields(pdf_path: str) -> dict:
    """Returns {field_name: 'text'|'checkbox'}."""
    return {n: m['type'] for n, m in get_fields_with_meta(pdf_path).items()}


def fill_pdf(pdf_path: str, field_values: dict) -> bytes:
    """Fill a PDF and return the result as bytes."""
    reader = pypdf.PdfReader(pdf_path)
    writer = pypdf.PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values, auto_regenerate=False)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
