from flask import Flask, request, jsonify
import re, os, tempfile
import pdfplumber
from docx import Document
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
import nltk
nltk.download('punkt')

app = Flask(__name__)

# Define required and bonus keywords
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

THRESHOLD = 60  # Minimum percentage to qualify

stemmer = PorterStemmer()

# Function to extract text from various file types
def extract_text(file_storage):
    filename = file_storage.filename.lower()
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        file_storage.save(temp_file.name)
        if filename.endswith(".pdf"):
            with pdfplumber.open(temp_file.name) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif filename.endswith(".docx"):
            doc = Document(temp_file.name)
            return "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith(".txt"):
            return temp_file.read().decode("utf-8")
        else:
            return ""
    os.unlink(temp_file.name)

# Preprocess text by tokenizing and stemming
def preprocess(text):
    tokens = word_tokenize(text.lower())
    return [stemmer.stem(token) for token in tokens]

# Match keywords in preprocessed text
def match_keywords(processed_text, keyword_dict):
    matched = []
    for canonical, variants in keyword_dict.items():
        for variant in variants:
            variant_stemmed = [stemmer.stem(word) for word in word_tokenize(variant.lower())]
            if all(stem in processed_text for stem in variant_stemmed):
                matched.append(canonical)
                break
    return list(set(matched))

# Root route (fix for 404 on base URL)
@app.route("/", methods=["GET"])
def index():
    return "Welcome to FitFinder Resume Checker API! Use POST /check_resume to evaluate a resume."

# Resume evaluation route
@app.route("/check_resume", methods=["POST"])
def check_resume():
    text = ""
    if "resume_file" in request.files:
        file = request.files["resume_file"]
        text = extract_text(file)
    elif request.json:
        text = request.json.get("resume_text", "")
    
    if not text.strip():
        return jsonify({"error": "No resume content provided"}), 400

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
    })

if __name__ == "__main__":
    app.run()
