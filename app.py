from flask import Flask, request, render_template, jsonify
import os
import docx2txt
import requests
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF for better PDF extraction

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure upload folder exists
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"pdf", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path):
    try:
        if file_path.endswith(".pdf"):
            with fitz.open(file_path) as doc:
                return "\n".join([page.get_text() for page in doc])
        elif file_path.endswith(".docx"):
            return docx2txt.process(file_path)
        else:
            return "Unsupported file format. Please upload a PDF or DOCX."
    except Exception as e:
        return f"Error extracting text: {e}"

def get_llm_analysis(text, user_type):
    if user_type == "student":
        prompt = f"""
        You are an AI career coach assisting students with interview preparation.

        ### Candidate Resume Text:
        {text}

        ### Instructions:
        *1. Expected Interview Questions:*  
        - Identify technical and behavioral questions based on the resume content.  

        *2. Skill Gaps & Areas for Improvement:*  
        - Highlight missing or weak areas in technical and soft skills.  

        *3. Preparation Guide:*  
        - Recommend topics to study based on gaps and expected questions.  
        - Suggest online resources or courses (if applicable).  
        """
    else:
        prompt = f"""
        You are an AI assistant that helps interviewers evaluate candidates.

        ### Candidate Resume Text:
        {text}

        ### Instructions:
        *1. Candidate Summary:*  
        - Provide a brief professional overview of the candidate.  

        *2. Key Skills & Areas of Concern:*  
        - Highlight technical and soft skills.  
        - Identify any gaps or weak areas.  

        *3. Benchmark Interview Questions:*  
        - Suggest a mix of technical, problem-solving, and soft skills questions.  
        """

    messages = [
        {"role": "system", "content": "You are an AI assistant analyzing resumes for job suitability."},
        {"role": "user", "content": prompt}
    ]

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"error": "Missing API Key for LLM Service"}

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={"model": "mistral-saba-24b", "messages": messages},
            verify=False
        )

        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            questions = [line.strip("- ") for line in content.split("\n") if line.startswith("- ")]
            return {
                "LLM Analysis": content,   # ✅ Fix key name here
                "questions": questions
            }
        else:
            return {"error": f"Error getting analysis: {response.text}"}
    except Exception as e:
        return {"error": f"Error connecting to LLM service: {str(e)}"}

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_resume():
    file = request.files.get("resume")
    user_type = request.form.get("user_type")

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload a PDF or DOCX file."})

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)

    extracted_text = extract_text_from_file(file_path)
    os.remove(file_path)  # Cleanup

    if "Error" in extracted_text:
        return jsonify({"error": extracted_text})

    # Get AI analysis based on user type
    llm_analysis = get_llm_analysis(extracted_text, user_type)

    return jsonify(llm_analysis)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)











