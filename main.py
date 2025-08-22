import re
import json
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Regex pattern for options (A-D or a-d)
option_pattern = re.compile(r'\(([A-Da-d])\)\s*(.*?)(?=(\([A-Da-d]\))|$)')

def process_question(lines):
    if not lines:
        return "", {}, False

    text = " ".join(lines)
    text = re.sub(r'^\s*\d+[\.\)\-]\s*', '', text)

    options = {}
    for match in option_pattern.finditer(text):
        letter = match.group(1).upper()
        content = match.group(2).strip()
        options[letter] = content

    q_text = option_pattern.sub("", text).strip()
    valid_keys = ["A", "B", "C", "D"]
    sorted_options = {k: options[k] for k in valid_keys if k in options}

    if len(sorted_options) == 4 and q_text:
        return q_text, sorted_options, True

    if len(sorted_options) == 2 and q_text:
        values = [v.lower() for v in sorted_options.values()]
        if set(values) in ({"yes", "no"}, {"true", "false"}):
            forced = {}
            if set(values) == {"yes", "no"}:
                for k, v in options.items():
                    if v.lower() == "yes":
                        forced["A"] = v
                    elif v.lower() == "no":
                        forced["B"] = v
            elif set(values) == {"true", "false"}:
                for k, v in options.items():
                    if v.lower() == "true":
                        forced["A"] = v
                    elif v.lower() == "false":
                        forced["B"] = v
            return q_text, forced, True

    return q_text, sorted_options, False


def parse_mcqs_from_text(content: str):
    lines = [line.rstrip() for line in content.splitlines() if line.strip()]
    questions = []
    current_question_lines = []

    for line in lines:
        if current_question_lines and re.match(r'^\d+\.\s*', line):
            q_text, opts, valid = process_question(current_question_lines)
            if valid:
                questions.append({"question": q_text, "options": opts})
            current_question_lines = [line]
        else:
            current_question_lines.append(line)

    if current_question_lines:
        q_text, opts, valid = process_question(current_question_lines)
        if valid:
            questions.append({"question": q_text, "options": opts})

    return questions


def format_as_text(questions: list) -> str:
    output = ""
    for q in questions:
        output += f"{q['question']}\n"
        for k in q["options"]:
            output += f"({k}) {q['options'][k]}\n"
        output += "\n"
    return output.strip()


def format_as_html(questions: list) -> str:
    html = ""
    for q in questions:
        html += f"<div class='question'><p><b>{q['question']}</b></p><ul class='options'>"
        for k in q["options"]:
            html += f"<li><span class='option'>({k}) {q['options'][k]}</span></li>"
        html += "</ul></div>"
    return html


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head><title>Upload MCQ File</title></head>
        <body>
            <h2>Upload MCQ File</h2>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input type="file" name="file"><br><br>
                <label for="output">Output format:</label>
                <select name="output">
                    <option value="json">JSON</option>
                    <option value="txt">Text</option>
                    <option value="html">HTML</option>
                </select><br><br>
                <input type="submit" value="Upload">
            </form>
            <div id="preview"></div>
        </body>
    </html>
    """


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(file: UploadFile, output: str = Form("json")):
    content = await file.read()
    text = content.decode("utf-8")
    questions = parse_mcqs_from_text(text)

    if output == "json":
        data = json.dumps(questions, indent=2)
        preview = f"<pre>{data}</pre>"
        mime = "application/json"
        ext = "json"

    elif output == "txt":
        data = format_as_text(questions)
        preview = f"<pre>{data}</pre>"
        mime = "text/plain"
        ext = "txt"

    elif output == "html":
        data = format_as_html(questions)
        preview = f"""
        <div style="font-family:Arial;">
            {data}
        </div>
        """
        mime = "text/html"
        ext = "html"

    else:
        return HTMLResponse("<p>Invalid output format</p>", status_code=400)

    return f"""
    <html>
    <head>
        <title>Upload MCQ File</title>
        <style>
            details {{
                margin-top: 20px;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background: #f9f9f9;
            }}
            summary {{
                font-weight: bold;
                cursor: pointer;
            }}
            #download-btn {{
                margin-top: 15px;
                padding: 8px 16px;
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            #download-btn:hover {{
                background: #2980b9;
            }}
        </style>
    </head>
    <body>
        <h2>Upload MCQ File</h2>
        <form action="/upload" enctype="multipart/form-data" method="post">
            <input type="file" name="file"><br><br>
            <label for="output">Output format:</label>
            <select name="output">
                <option value="json">JSON</option>
                <option value="txt">Text</option>
                <option value="html">HTML</option>
            </select><br><br>
            <input type="submit" value="Upload">
        </form>

        <details open>
            <summary>Preview ({output.upper()})</summary>
            <div style="margin-top:10px;">{preview}</div>
        </details>

        <button id="download-btn" onclick="downloadFile()">⬇ Download File</button>

        <script>
        function downloadFile() {{
            var blob = new Blob([{json.dumps(data)}], {{ type: '{mime}' }});
            var link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = "questions.{ext}";
            link.click();
        }}
        </script>
    </body>
    </html>
    """
