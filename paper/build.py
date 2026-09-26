from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent
for cmd in [['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['bibtex','main'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex']]:
    result=subprocess.run(cmd,cwd=root)
    if result.returncode:raise SystemExit(result.returncode)
