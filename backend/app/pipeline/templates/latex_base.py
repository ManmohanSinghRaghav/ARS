"""
LaTeX base templates for professional academic papers.
"""

LATEX_TEMPLATE = r"""
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\geometry{a4paper, margin=1in}
\usepackage{amsmath, amssymb, amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{microtype}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{caption}
\usepackage{subcaption}

\title{[[TITLE]]}
\author{Autonomous Research Scientist (ARS)}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
[[ABSTRACT]]
\end{abstract}

[[CONTENT]]

\bibliographystyle{plain}
\begin{thebibliography}{99}
[[REFERENCES]]
\end{thebibliography}

\end{document}
"""

NEURIPS_LATEX_STYLE = {
    "sections": [
        "Abstract",
        "1 Introduction",
        "2 Related Work",
        "3 Methodology",
        "4 Experiments",
        "5 Discussion",
        "6 Conclusion",
        "References"
    ],
    "formatting_rules": [
        "Use strictly professional LaTeX syntax.",
        "Include math environments ($...$) for all symbols.",
        "Use \section{}, \subsection{}, and \subsubsection{} for hierarchy.",
    ],
    "prompts": {
        "introduction": "Write a deep, multi-paragraph Introduction (Section 1.0) for: {{topic}}. Define the problem, current landscape, and our contribution clearly. Aim for ~800 words.",
        "related_work": "Synthesize the provided literature review into a deep 'Related Work' section (Section 2.0). Compare and contrast at least 5 major themes. Aim for ~1000 words.",
        "methodology": "Provide a rigorous formalization of the Methodology (Section 3.0). Include at least one algorithm environment using algorithm2e style and multiple LaTeX equations. Aim for ~1200 words.",
        "results": "Describe the experimental results (Section 4.0) based on the Result Card. Include a detailed analysis of metrics and use the provided LaTeX tables. Aim for ~800 words.",
        "conclusion": "Write a forward-looking Conclusion and Discussion (Section 5.0 and 6.0). Analyze limitations and future research directions. Aim for ~600 words."
    }
}
