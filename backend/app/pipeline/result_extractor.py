import json
import re

def extract_results_from_output(stdout: str) -> dict:
    """
    Parses the evaluation output from the sandbox executor.
    Looks for JSON blocks or keyword patterns (accuracy, loss, etc.).
    """
    results = {
        "metrics": {},
        "raw_summary": "",
        "latex_table": ""
    }
    
    # Try to find a JSON block in the output
    json_match = re.search(r'(\{.*\})', stdout, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            results["metrics"] = data
        except:
            pass
            
    # Basic keyword extraction if no JSON found
    patterns = {
        "accuracy": r"accuracy[:\s]+(\d+\.\d+)",
        "loss": r"loss[:\s]+(\d+\.\d+)",
        "precision": r"precision[:\s]+(\d+\.\d+)",
        "recall": r"recall[:\s]+(\d+\.\d+)",
    }
    
    for key, pattern in patterns.items():
        if key not in results["metrics"]:
            match = re.search(pattern, stdout, re.IGNORECASE)
            if match:
                results["metrics"][key] = float(match.group(1))

    # Generate a simple LaTeX table
    if results["metrics"]:
        table = "\\begin{tabular}{lc}\n\\hline\nMetric & Value \\\\ \n\\hline\n"
        for k, v in results["metrics"].items():
            table += f"{k.capitalize()} & {v} \\\\ \n"
        table += "\\hline\n\\end{tabular}"
        results["latex_table"] = table
    
    results["raw_summary"] = stdout[-1000:] if len(stdout) > 1000 else stdout
    return results
