import re
import tkinter as tk
from tkinter import filedialog, messagebox

def format_mcq(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f if line.strip()]

    formatted_content = ""
    current_question_lines = []

    # Pattern to detect options (A-D or a-d)
    option_pattern = re.compile(r'\(([A-Da-d])\)\s*(.*?)(?=(\([A-Da-d]\))|$)')

    def process_question(lines):
        """Process lines for a single question"""
        if not lines:
            return None, False

        text = " ".join(lines)
        options = {}
        for match in option_pattern.finditer(text):
            letter = match.group(1)
            content = match.group(2).strip()
            options[letter] = f"({letter}) {content}"

        # Remove options to get question text
        q_text = option_pattern.sub("", text).strip()

        # Only valid if exactly 4 options
        if len(options) == 4 and q_text:
            return q_text, options, True
        return q_text, options, False

    for line in lines:
        # Start a new question when a blank line is found or a numbered line appears
        if current_question_lines and re.match(r'^\d+\.\s*', line):
            q_text, opts, valid = process_question(current_question_lines)
            if valid:
                formatted_content += f"{q_text}\n"
                for key in sorted(opts.keys(), key=lambda x: x.upper()):
                    formatted_content += opts[key] + "\n"
                formatted_content += "\n"
            current_question_lines = [line]
        else:
            current_question_lines.append(line)

    # Process last question
    if current_question_lines:
        q_text, opts, valid = process_question(current_question_lines)
        if valid:
            formatted_content += f"{q_text}\n"
            for key in sorted(opts.keys(), key=lambda x: x.upper()):
                formatted_content += opts[key] + "\n"

    return formatted_content

def select_file():
    file_path = filedialog.askopenfilename(
        title="Select MCQ Text File",
        filetypes=[("Text Files", "*.txt")]
    )
    if file_path:
        formatted = format_mcq(file_path)
        output_text.delete("1.0", tk.END)
        if not formatted.strip():
            messagebox.showwarning("No Output", "No complete questions with 4 options found!")
            return

        output_text.insert(tk.END, formatted)

        save = messagebox.askyesno("Save File", "Do you want to save the formatted questions to a file?")
        if save:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                title="Save Formatted MCQs"
            )
            if save_path:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(formatted)
                messagebox.showinfo("Success", f"Formatted MCQs saved to:\n{save_path}")

# GUI
root = tk.Tk()
root.title("MCQ Formatter")
root.geometry("700x500")

btn_select = tk.Button(root, text="Select MCQ File", command=select_file, font=("Arial", 14))
btn_select.pack(pady=10)

output_text = tk.Text(root, wrap=tk.WORD, font=("Arial", 12))
output_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

root.mainloop()
