import os
import subprocess
import shutil
import tempfile
from pathlib import Path

def compile_latex_to_pdf(tex_content: str, output_path: str) -> bool:
    """
    Compiles LaTeX content into a PDF using pdflatex.
    Returns True if successful, False otherwise.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tex_file = tmp_path / "paper.tex"
        
        # Write content
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(tex_content)
        
        # Run pdflatex (twice for references)
        try:
            # -interaction=nonstopmode prevents hanging on errors
            # -output-directory ensures files stay in tmp
            for _ in range(2):
                result = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(tmp_path), "paper.tex"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            pdf_file = tmp_path / "paper.pdf"
            if pdf_file.exists():
                shutil.copy(pdf_file, output_path)
                return True
            else:
                print(f"[Compiler] Error: PDF was not generated. Log:\n{result.stdout}")
                return False
        except subprocess.TimeoutExpired:
            print("[Compiler] Error: Compilation timed out.")
            return False
        except Exception as e:
            print(f"[Compiler] Error during compilation: {e}")
            return False
