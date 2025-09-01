# save as app.py
from flask import Flask, request, render_template_string, send_file
import json
import io
import re

app = Flask(__name__)

# HTML template
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>JSONL Processor</title>
</head>
<body>
    <h2>Upload JSONL File</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file" accept=".jsonl" required>
        <button type="submit">Upload & Process</button>
    </form>
    {% if preview %}
        <h3>Preview (first 3 lines):</h3>
        <pre>{{ preview }}</pre>
        <a href="/download">⬇️ Download Processed JSONL</a>
    {% endif %}
</body>
</html>
"""

processed_data = None  # store processed content in memory


def convert_options(text: str) -> str:
    """Convert options (1-4) and (a-d) into (A-D)."""
    replacements = {
        "(1)": "(A)", "(2)": "(B)", "(3)": "(C)", "(4)": "(D)",
        "(a)": "(A)", "(b)": "(B)", "(c)": "(C)", "(d)": "(D)",
        "(A)": "(A)", "(B)": "(B)", "(C)": "(C)", "(D)": "(D)",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


@app.route("/", methods=["GET", "POST"])
def index():
    global processed_data
    if request.method == "POST":
        file = request.files["file"]
        if not file:
            return "No file uploaded", 400

        # Read and process JSONL
        lines = file.read().decode("utf-8").splitlines()
        processed_lines = []
        for line in lines:
            obj = json.loads(line)

            body = obj.get("body", {})
            messages = body.get("messages", [])
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")

                    # ---- Process QUESTION ----
                    if "QUESTION (HTML one-line):" in content:
                        q_match = re.search(r"QUESTION \(HTML one-line\):(.*?)(SOLUTION \(HTML one-line\):|$)", content, flags=re.DOTALL)
                        if q_match:
                            q_text = q_match.group(1)
                            q_text = convert_options(q_text)  # always convert in QUESTION
                            content = content.replace(q_match.group(1), q_text)

                    # ---- Process SOLUTION ----
                    if "SOLUTION (HTML one-line):" in content:
                        sol_match = re.search(r"SOLUTION \(HTML one-line\):(.*)", content, flags=re.DOTALL)
                        if sol_match:
                            sol_text = sol_match.group(1).strip()

                            # Only convert if options exist in SOLUTION
                            if any(opt in sol_text for opt in ["(1)", "(2)", "(3)", "(4)", "(a)", "(b)", "(c)", "(d)"]):
                                new_sol_text = convert_options(sol_text)
                                content = content.replace(sol_text, new_sol_text)
                            # else → leave solution as it is (even if empty)

                    msg["content"] = content.strip()

            processed_lines.append(json.dumps(obj, ensure_ascii=False))

        # Save in memory
        processed_data = "\n".join(processed_lines)

        # Show preview (first 3 lines)
        preview = "\n".join(processed_lines[:3])
        return render_template_string(HTML_PAGE, preview=preview)

    return render_template_string(HTML_PAGE, preview=None)


@app.route("/download")
def download():
    global processed_data
    if not processed_data:
        return "No file processed yet", 400

    buf = io.BytesIO(processed_data.encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="tagging_batch.jsonl",
        mimetype="application/jsonl"
    )


if __name__ == "__main__":
    app.run(debug=True)
