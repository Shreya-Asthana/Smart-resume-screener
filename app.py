# app.py
import os
import csv
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from parser import parse_resume
from llm_client import rate_candidate

from dotenv import load_dotenv
load_dotenv()

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

CSV_PATH = "resumes.csv"
ALLOWED_EXT = {"pdf", "docx", "txt"}

def allowed_file(fn):
    return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXT

def write_csv_record(rec: dict):
    """Append record dict to resumes.csv (create header if not exists)."""
    fieldnames = ["id","filename","name","email","phone","skills","education","experience","text"]
    write_header = not os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(rec)

def read_all_records():
    """Read all from resumes.csv into list of dicts."""
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def get_record_by_id(rec_id: str):
    recs = read_all_records()
    for rec in recs:
        if rec["id"] == rec_id:
            return rec
    return None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        if "resume" not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
        file = request.files["resume"]
        if file.filename == "":
            flash("No selected file", "danger")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(path)
            ext = filename.rsplit(".",1)[1].lower()
            parsed = parse_resume(path, ext)
            recs = read_all_records()
            new_id = str(len(recs) + 1)
            rec = {
                "id": new_id,
                "filename": filename,
                "name": parsed.get("name") or "",
                "email": parsed.get("email") or "",
                "phone": parsed.get("phone") or "",
                "skills": ";".join(parsed.get("skills", [])),
                "education": parsed.get("education") or "",
                "experience": parsed.get("experience") or "",
                "text": parsed.get("text") or ""
            }
            write_csv_record(rec)
            flash("Uploaded & parsed.", "success")
            return redirect(url_for("candidates"))
    return render_template("upload.html")

@app.route("/candidates")
def candidates():
    recs = read_all_records()
    return render_template("candidates.html", records=recs)

@app.route("/candidate/<rec_id>")
def candidate(rec_id):
    rec = get_record_by_id(rec_id)
    if rec is None:
        flash("Candidate not found", "danger")
        return redirect(url_for("candidates"))
    skills = rec["skills"].split(";") if rec.get("skills") else []
    return render_template("candidate.html", rec=rec, skills=skills)

@app.route("/match", methods=["GET","POST"])
def match():
    if request.method == "POST":
        job_desc = request.form.get("job_description","").strip()
        if not job_desc:
            flash("Provide job description.", "warning")
            return redirect(request.url)
        recs = read_all_records()
        results = []
        for rec in recs:
            skills_section_text = rec.get("skills_section", "") or rec.get("text", "")[:2000]  # fallback to text
            try:
                resp = rate_candidate(skills_section_text, job_desc)
                score = float(resp.get("score", 0.0))
                justification = resp.get("justification", resp.get("raw", ""))
                matches = resp.get("matches", [])
                recommendation = resp.get("recommendation", "")
            except Exception as e:
                score = 0.0
                justification = f"LLM error: {str(e)}"
                matches = []
                recommendation = ""
            results.append({
                "rec": rec,
                "score": score,
                "justification": justification,
                "matches": matches,
                "recommendation": recommendation
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return render_template("match_results.html", job_desc=job_desc, results=results)
    return render_template("match_form.html")

if __name__ == "__main__":
    app.run(debug=True)