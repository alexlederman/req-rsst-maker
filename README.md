# Form Creator

A local web app for filling and generating PDF forms for clinical research. Built for Fred Hutchinson Cancer Center.

## What it does

- Select a patient from a saved list (or create a new one)
- Fill in collection date, time, subject ID, and other RSST fields once
- Generate filled RSST and Requisition PDFs in one click
- Files are saved to a timestamped folder on your Desktop

---

## Setup

### Requirements

- Python 3.9 or later
- The `forms/` folder with your PDF templates (not included in this repo)

### Install dependencies

**Mac:**
```bash
pip3 install -r requirements.txt
```

**Windows:**
```bash
pip install -r requirements.txt
```

---

## Folder structure

The `forms/` folder must be placed inside `pdf_filler/` and structured as follows:

```
pdf_filler/
  forms/
    RSST/
      your-rsst-template.pdf
    Req/
      your-req-template.pdf
      SubfolderName/       ← optional subfolders for grouped templates
        another-template.pdf
```

---

## Running the app

**Mac:**
```bash
python3 app.py
```

**Windows:**
```bash
python app.py
```

Then open [http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser.

Keep the terminal open while using the app — closing it stops the server. Press `Ctrl+C` to stop it.

---

## Notes

- Patient data is stored locally in `patients.json` and is not synced to GitHub
- PDF templates in `forms/` are stored locally and are not synced to GitHub
