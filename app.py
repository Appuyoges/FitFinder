from flask import Flask, request, jsonify
import os, tempfile
import pdfplumber
from docx import Document
from nltk.stem import PorterStemmer

app = Flask(__name__)

REQUIRED_KEYWORDS = {
    "python": ["python", "py"],
    "sql": ["sql", "mysql", "postgresql", "sqlite"],
    "communication": ["communication", "interpersonal", "presentation"],
    "problem solving": ["problem solving", "critical thinking", "troubleshooting"],
}

BONUS_KEYWORDS = {
    "machine learning": ["machine learning", "ml", "ai"],
    "leadership": ["leadership", "team lead", "mentorship"],
}

THRESHOLD = 60
stemmer = PorterStemmer()

def extract_text(file_storage):
    filename = file_storage.filename.lower()
    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            file_storage.save(temp_path)

        if filename.endswith(".pdf"):
            with pdfplumber.open(temp_path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif filename.endswith(".docx"):
            doc = Document(temp_path)
            return "\n".join(para.text for para in doc.paragraphs)
        elif filename.endswith(".txt"):
            with open(temp_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except PermissionError:
                pass

# ✅ Simple tokenizer (no nltk.download needed)
def preprocess(text):
    tokens = text.lower().replace('\n', ' ').split()
    return [stemmer.stem(token.strip(".,!?;:()[]{}\"'")) for token in tokens]

def match_keywords(processed_text, keyword_dict):
    matched = []
    for canonical, variants in keyword_dict.items():
        for variant in variants:
            variant_stemmed = [stemmer.stem(word) for word in variant.lower().split()]
            if all(stem in processed_text for stem in variant_stemmed):
                matched.append(canonical)
                break
    return list(set(matched))

@app.route("/", methods=["GET"])
def index():
    return "✅ Welcome to FitFinder Resume Checker API! Use POST /check_resume to evaluate resumes."

@app.route("/check_resume", methods=["POST"])
def check_resume():
    print("Request content-type:", request.content_type)
    text = ""

    if "resume_file" in request.files:
        print("🔍 File received")
        file = request.files["resume_file"]
        text = extract_text(file)
    elif request.is_json:
        print("📝 JSON received")
        text = request.json.get("resume_text", "")
    else:
        print("⚠️ No valid input found")
        return jsonify({"error": "No resume content provided"}), 400

    if not text.strip():
        return jsonify({"error": "Empty or invalid resume content"}), 400

    processed = preprocess(text)

    required_matched = match_keywords(processed, REQUIRED_KEYWORDS)
    bonus_matched = match_keywords(processed, BONUS_KEYWORDS)

    req_score = (len(required_matched) / len(REQUIRED_KEYWORDS)) * 80
    bonus_score = (len(bonus_matched) / len(BONUS_KEYWORDS)) * 20 if BONUS_KEYWORDS else 0
    total_score = round(req_score + bonus_score)

    status = "qualified" if total_score >= THRESHOLD else "rejected"

    return jsonify({
        "status": status,
        "total_score": total_score,
        "required_matched": required_matched,
        "bonus_matched": bonus_matched,
        "missing_required": list(set(REQUIRED_KEYWORDS) - set(required_matched))
    }), 200

if __name__ == "__main__":
    app.run(debug=True)
