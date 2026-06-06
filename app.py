import os
import json
import time
from datetime import datetime

from flask import Flask, render_template, request, send_from_directory, abort, jsonify
from pdf_utils import get_fields_with_meta, fill_pdf

app = Flask(__name__)
app.secret_key = os.urandom(24)

TEMPLATES_DIR  = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'Templates'))
ASSETS_DIR     = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
PATIENTS_FILE  = os.path.join(os.path.dirname(__file__), 'patients.json')
RSST_DIR = os.path.join(TEMPLATES_DIR, 'RSST')
REQ_DIR  = os.path.join(TEMPLATES_DIR, 'Req')
DESKTOP  = os.path.expanduser('~/Desktop')

# ── PDF field name mappings ────────────────────────────────────────────────
RSST_MAP = {
    'collection_date':  'Date_To-be-collected_af_date',
    'collection_time':  'Time-To-be-collected',
    'study_subject_id': 'Study-Subject-ID',
    'subject_initials': 'Subject-Initials',
    'mrn':              'MRN',
}

REQ_MAP = {
    'collection_date':     'Collection Window',
    'study_subject_id':    'Study Subject ID',
    'patient_identifier':  'Patient Indentifiers',
}


def load_patients():
    if not os.path.exists(PATIENTS_FILE):
        return []
    with open(PATIENTS_FILE) as f:
        return json.load(f)


def save_patients(patients):
    with open(PATIENTS_FILE, 'w') as f:
        json.dump(patients, f, indent=2)


def list_pdfs(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder)
                  if f.lower().endswith('.pdf') and not f.startswith('.'))


def load_prefills(folder, pdf_field_names):
    out = {}
    for fname in list_pdfs(folder):
        meta = get_fields_with_meta(os.path.join(folder, fname))
        out[fname] = {k: meta.get(k, {}).get('value', '') for k in pdf_field_names}
    return out


rsst_prefills = load_prefills(RSST_DIR, list(RSST_MAP.values()))
req_prefills  = load_prefills(REQ_DIR,  list(REQ_MAP.values()))


@app.route('/assets/<path:filename>')
def serve_asset(filename):
    return send_from_directory(ASSETS_DIR, filename)


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
    rsst_fields   = data.get('rsst_fields', {})
    req_forms     = data.get('req_forms', [])
    folder_name   = (data.get('folder_name') or rsst_name).strip()

    # Create output folder on Desktop
    out_dir = os.path.join(DESKTOP, folder_name)
    os.makedirs(out_dir, exist_ok=True)
    seen = set()

    # ── RSST PDF ──────────────────────────────────────────────────────────
    if rsst_template:
        rsst_path = os.path.join(RSST_DIR, rsst_template)
        if os.path.exists(rsst_path):
            vals = {pdf_f: rsst_fields[fid]
                    for fid, pdf_f in RSST_MAP.items()
                    if rsst_fields.get(fid)}
            vals['Date_Form-Submitted_af_date'] = today
            pdf_bytes = fill_pdf(rsst_path, vals)
            fname = _unique(f'{rsst_name}.pdf', seen)
            with open(os.path.join(out_dir, fname), 'wb') as f:
                f.write(pdf_bytes)

    # ── Req PDFs ──────────────────────────────────────────────────────────
    for req in req_forms:
        template = req.get('template', '')
        name     = (req.get('name') or 'Req').strip()
        if not template:
            continue
        req_path = os.path.join(REQ_DIR, template)
        if not os.path.exists(req_path):
            continue

        vals = {}
        for fid in ('collection_date', 'study_subject_id'):
            if rsst_fields.get(fid):
                vals[REQ_MAP[fid]] = rsst_fields[fid]
        pid = req.get('patient_identifier', '')
        if pid:
            vals[REQ_MAP['patient_identifier']] = pid.replace('\n', '\r')

        pdf_bytes = fill_pdf(req_path, vals)
        fname = _unique(f'{name}.pdf', seen)
        with open(os.path.join(out_dir, fname), 'wb') as f:
            f.write(pdf_bytes)

    return jsonify({'folder': out_dir, 'folder_name': folder_name})


@app.route('/patients', methods=['GET'])
def get_patients():
    return jsonify(load_patients())


@app.route('/patients', methods=['POST'])
def add_patient():
    data = request.get_json(force=True)
    identifier = (data.get('identifier') or '').strip()
    if not identifier:
        abort(400)
    patients = load_patients()
    patient = {
        'id':         str(int(time.time() * 1000)),
        'identifier': identifier,
        'initials':   (data.get('initials')   or '').strip(),
        'subject_id': (data.get('subject_id') or '').strip(),
    }
    patients.append(patient)
    save_patients(patients)
    return jsonify(patient), 201


@app.route('/patients/<patient_id>', methods=['PUT'])
def update_patient(patient_id):
    data = request.get_json(force=True)
    patients = load_patients()
    for p in patients:
        if p['id'] == patient_id:
            p['identifier'] = (data.get('identifier') or '').strip()
            p['initials']   = (data.get('initials')   or '').strip()
            p['subject_id'] = (data.get('subject_id') or '').strip()
            save_patients(patients)
            return jsonify(p)
    abort(404)


@app.route('/patients/<patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    patients = [p for p in load_patients() if p['id'] != patient_id]
    save_patients(patients)
    return '', 204


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
    app.run(debug=True, port=8080)
