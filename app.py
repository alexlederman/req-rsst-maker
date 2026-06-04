import os
import io
import json
import zipfile
from datetime import datetime

from flask import Flask, render_template, request, send_file, abort
from pdf_utils import get_fields_with_meta, fill_pdf

app = Flask(__name__)
app.secret_key = os.urandom(24)

TEMPLATES_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Templates'))
RSST_DIR = os.path.join(TEMPLATES_DIR, 'RSST')
REQ_DIR  = os.path.join(TEMPLATES_DIR, 'Req')

# ── PDF field name mappings ────────────────────────────────────────────────
# RSST fields filled from user input
RSST_MAP = {
    'collection_date':  'Date_To-be-collected_af_date',
    'collection_time':  'Time-To-be-collected',
    'study_subject_id': 'Study-Subject-ID',
    'subject_initials': 'Subject-Initials',
    'mrn':              'MRN',
    # date_submitted handled separately (auto)
}

# Req fields — shared values come from rsst_fields
REQ_MAP = {
    'collection_date':     'Collection Window',
    'study_subject_id':    'Study Subject ID',
    'patient_identifier':  'Patient Indentifiers',
}


def list_pdfs(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if f.lower().endswith('.pdf') and not f.startswith('.'))


def load_prefills(folder, pdf_field_names):
    """Return {filename: {pdf_field: value}} for each PDF in folder."""
    out = {}
    for fname in list_pdfs(folder):
        meta = get_fields_with_meta(os.path.join(folder, fname))
        out[fname] = {k: meta.get(k, {}).get('value', '') for k in pdf_field_names}
    return out


# Pre-load template data for JS (values to pre-populate editable cells)
rsst_prefills = load_prefills(RSST_DIR, list(RSST_MAP.values()))
req_prefills  = load_prefills(REQ_DIR,  list(REQ_MAP.values()))


@app.route('/')
def sheet():
    return render_template(
        'sheet.html',
        rsst_files=list_pdfs(RSST_DIR),
        req_files=list_pdfs(REQ_DIR),
        rsst_files_json=json.dumps(list_pdfs(RSST_DIR)),
        req_files_json=json.dumps(list_pdfs(REQ_DIR)),
        rsst_prefills_json=json.dumps(rsst_prefills),
        req_prefills_json=json.dumps(req_prefills),
    )


@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json(force=True)
    if not data:
        abort(400)

    _now          = datetime.now()
    today         = f"{_now.month}/{_now.day}/{_now.strftime('%y')}"
    rsst_template = data.get('rsst_template', '')
    rsst_name     = (data.get('rsst_name') or 'RSST').strip()
    rsst_fields   = data.get('rsst_fields', {})   # {logical_id: value}
    req_forms     = data.get('req_forms', [])

    zip_buf = io.BytesIO()
    seen = set()

    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:

        # ── RSST PDF ──────────────────────────────────────────────────────
        if rsst_template:
            rsst_path = os.path.join(RSST_DIR, rsst_template)
            if os.path.exists(rsst_path):
                vals = {pdf_f: rsst_fields[fid]
                        for fid, pdf_f in RSST_MAP.items()
                        if rsst_fields.get(fid)}
                vals['Date_Form-Submitted_af_date'] = today
                zf.writestr(_unique(f'{rsst_name}.pdf', seen),
                            fill_pdf(rsst_path, vals))

        # ── Req PDFs ──────────────────────────────────────────────────────
        for req in req_forms:
            template = req.get('template', '')
            name     = (req.get('name') or 'Req').strip()
            if not template:
                continue
            req_path = os.path.join(REQ_DIR, template)
            if not os.path.exists(req_path):
                continue

            vals = {}
            # Shared values from RSST column
            for fid in ('collection_date', 'study_subject_id'):
                if rsst_fields.get(fid):
                    vals[REQ_MAP[fid]] = rsst_fields[fid]
            # Req-only: patient identifier (convert newlines to carriage returns)
            pid = req.get('patient_identifier', '')
            if pid:
                vals[REQ_MAP['patient_identifier']] = pid.replace('\n', '\r')

            zf.writestr(_unique(f'{name}.pdf', seen), fill_pdf(req_path, vals))

    zip_buf.seek(0)
    return send_file(zip_buf, mimetype='application/zip',
                     as_attachment=True, download_name='generated.zip')


def _unique(name, seen):
    if name not in seen:
        seen.add(name)
        return name
    base = name[:-4] if name.lower().endswith('.pdf') else name
    i = 2
    while f'{base}_{i}.pdf' in seen:
        i += 1
    result = f'{base}_{i}.pdf'
    seen.add(result)
    return result


if __name__ == '__main__':
    app.run(debug=True, port=5000)
