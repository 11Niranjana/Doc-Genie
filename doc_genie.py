import ast
import gradio as gr
from datetime import datetime
from pathlib import Path
import urllib.parse

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet


# -----------------------------
# CORE ANALYZER CLASS
# -----------------------------

class DocGenieAnalyzer:

    @staticmethod
    def extract_function_signature(code):
        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):

                    params = []

                    for arg in node.args.args:
                        name = arg.arg
                        type_ = "Any"

                        if arg.annotation:
                            type_ = ast.unparse(arg.annotation)

                        params.append({
                            "name": name,
                            "type": type_,
                            "default": None
                        })

                    return_type = "Any"

                    if node.returns:
                        return_type = ast.unparse(node.returns)

                    signature = {
                        "name": node.name,
                        "params": params,
                        "return_type": return_type
                    }

                    return signature, node

            return None, None

        except Exception:
            return None, None

    # -------------------------

    @staticmethod
    def analyze_function_logic(func_def, code):

        analysis = {
            "has_loops": False,
            "has_conditions": False,
            "operations": [],
            "function_calls": [],
            "description": ""
        }

        for node in ast.walk(func_def):

            if isinstance(node, (ast.For, ast.While)):
                analysis["has_loops"] = True

            if isinstance(node, ast.If):
                analysis["has_conditions"] = True

            if isinstance(node, ast.BinOp):

                if isinstance(node.op, ast.Add):
                    analysis["operations"].append("addition")

                if isinstance(node.op, ast.Sub):
                    analysis["operations"].append("subtraction")

                if isinstance(node.op, ast.Mult):
                    analysis["operations"].append("multiplication")

                if isinstance(node.op, ast.Div):
                    analysis["operations"].append("division")

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    analysis["function_calls"].append(node.func.id)

        desc = f"Executes {func_def.name} function"

        if analysis["has_conditions"]:
            desc += " with conditional logic"

        if analysis["has_loops"]:
            desc += " and iteration"

        desc += " and returns computed result."

        analysis["description"] = desc

        return analysis

    # -------------------------

    @staticmethod
    def generate_google_docstring(signature, analysis):

        text = f'    """{analysis["description"]}\n\n'

        if signature["params"]:
            text += "    Args:\n"
            for p in signature["params"]:
                text += f'        {p["name"]} ({p["type"]}): Input parameter.\n'

        text += "\n"
        text += "    Returns:\n"
        text += f'        {signature["return_type"]}: Result value.\n'
        text += '    """\n'

        return text

    # -------------------------

    @staticmethod
    def generate_numpy_docstring(signature, analysis):

        text = f'    """{analysis["description"]}\n\n'

        text += "    Parameters\n"
        text += "    ----------\n"

        for p in signature["params"]:
            text += f'    {p["name"]} : {p["type"]}\n'
            text += "        Input parameter.\n"

        text += "\n    Returns\n"
        text += "    -------\n"
        text += f'    {signature["return_type"]}\n'
        text += "        Result value.\n"

        text += '    """\n'

        return text


# -----------------------------
# GLOBALS
# -----------------------------

analyzer = DocGenieAnalyzer()
generation_history = []


# -----------------------------
# DOCSTRING GENERATION
# -----------------------------

def generate_docstring(code, style):

    signature, func = analyzer.extract_function_signature(code)

    if not signature:
        return "", "❌ No valid function detected"

    analysis = analyzer.analyze_function_logic(func, code)

    if style == "google":
        docstring = analyzer.generate_google_docstring(signature, analysis)
    else:
        docstring = analyzer.generate_numpy_docstring(signature, analysis)

    lines = code.split("\n")
    new_code = lines[0] + "\n" + docstring

    for line in lines[1:]:
        new_code += line + "\n"

    generation_history.append({
        "code": code,
        "docstring": docstring,
        "time": str(datetime.now())
    })

    return new_code, "✅ Docstring Generated"


# -----------------------------
# FILE UPLOAD
# -----------------------------

def load_file(file):

    if file is None:
        return ""

    with open(file.name, "r") as f:
        return f.read()


# -----------------------------
# TXT EXPORT
# -----------------------------

def export_txt():

    if not generation_history:
        return None

    text = ""

    for item in generation_history:
        text += item["code"]
        text += "\n"
        text += item["docstring"]
        text += "\n\n"

    path = "docgenie_output.txt"

    Path(path).write_text(text)

    return path


# -----------------------------
# PDF EXPORT
# -----------------------------

def export_pdf():

    if not generation_history:
        return None

    path = "docgenie_output.pdf"

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("Doc-Genie Documentation Report", styles["Title"]))
    story.append(Spacer(1,20))

    for item in generation_history:

        story.append(Paragraph("Function Documentation", styles["Heading2"]))
        story.append(Spacer(1,10))

        story.append(Preformatted(item["code"], styles["Code"]))
        story.append(Spacer(1,10))

        story.append(Preformatted(item["docstring"], styles["Code"]))
        story.append(Spacer(1,20))

    doc = SimpleDocTemplate(path, pagesize=A4)
    doc.build(story)

    return path


# -----------------------------
# SOCIAL SHARE
# -----------------------------

def share_links(text):

    encoded = urllib.parse.quote(text)

    whatsapp = f"https://wa.me/?text={encoded}"
    facebook = f"https://www.facebook.com/sharer/sharer.php?u={encoded}"

    return whatsapp, facebook


# -----------------------------
# GRADIO UI
# -----------------------------

with gr.Blocks(title="Doc-Genie") as demo:

    gr.Markdown("# 📚 Doc-Genie Python Docstring Generator")

    file_input = gr.File(label="Upload Python File (.py)")

    code_input = gr.Code(language="python")

    file_input.change(load_file, file_input, code_input)

    style = gr.Radio(
        ["google","numpy"],
        label="Docstring Style",
        value="google"
    )

    generate_btn = gr.Button("Generate Docstring")

    output = gr.Code(language="python")

    status = gr.Textbox()

    generate_btn.click(
        generate_docstring,
        inputs=[code_input,style],
        outputs=[output,status]
    )

    gr.Markdown("## Export")

    txt_btn = gr.Button("Download TXT")
    pdf_btn = gr.Button("Download PDF")

    txt_file = gr.File()
    pdf_file = gr.File()

    txt_btn.click(export_txt, outputs=txt_file)
    pdf_btn.click(export_pdf, outputs=pdf_file)

    gr.Markdown("## Share")

    share_text = gr.Textbox(label="Text to Share")

    share_btn = gr.Button("Generate Share Links")

    whatsapp = gr.Textbox(label="WhatsApp Link")
    facebook = gr.Textbox(label="Facebook Link")

    share_btn.click(
        share_links,
        inputs=share_text,
        outputs=[whatsapp,facebook]
    )


demo.launch(share=True)