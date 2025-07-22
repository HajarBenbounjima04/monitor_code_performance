import os
import sys
import json
import argparse
import logging
import webbrowser
from datetime import datetime
import shutil
import matplotlib.pyplot as plt
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger('ReportGenerator')

class ReportGenerator:
    def __init__(self, results_file, output_dir=None, format="html", verbose=False, show_charts=True):
        self.results_file = results_file
        self.results = None
        self.format = format
        self.show_charts = show_charts
        self.verbose = verbose
        
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.dirname(results_file)
        
        if verbose:
            logger.setLevel(logging.DEBUG)
        
        self.load_results()
    
    def load_results(self):
        """Charge les résultats depuis le fichier JSON"""
        try:
            if not os.path.exists(self.results_file):
                alternate_path = os.path.join(self.output_dir, "analysis_results.json")
                if os.path.exists(alternate_path):
                    self.results_file = alternate_path
                else:
                    logger.error(f"Fichier de résultats introuvable: {self.results_file}")
                    sys.exit(1)
            
            with open(self.results_file, 'r', encoding='utf-8') as f:
                self.results = json.load(f)
            
            logger.debug(f"Résultats chargés depuis {self.results_file}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des résultats: {e}")
            sys.exit(1)
    
    def generate_report(self):
        """Génère le rapport dans le format spécifié"""
        if self.format == "html":
            return self.generate_html_report()
        elif self.format == "markdown":
            return self.generate_markdown_report()
        elif self.format == "text":
            return self.generate_text_report()
        else:
            logger.error(f"Format de rapport non supporté: {self.format}")
            return None
    
    def generate_text_report(self):
        """Génère un rapport au format texte"""
        output_file = os.path.join(self.output_dir, "performance_report.txt")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # En-tête
                f.write("===================================\n")
                f.write("  RAPPORT D'ANALYSE DE PERFORMANCE \n")
                f.write("===================================\n\n")
                
                meta = self.results["metadata"]
                f.write(f"Date d'analyse: {meta['timestamp']}\n")
                f.write(f"Fichier analysé: {meta['file_name']}\n")
                f.write(f"Langage détecté: {meta['language']}\n")
                f.write(f"Taille du fichier: {meta['file_size']} octets\n")
                f.write(f"Nombre d'itérations: {meta['iterations']}\n")
                f.write(f"Niveau de test: {meta['test_level']}\n\n")
                
                sys_info = meta["system_info"]
                f.write("Informations système:\n")
                f.write(f"  - Plateforme: {sys_info['platform']} {sys_info['platform_release']}\n")
                f.write(f"  - Architecture: {sys_info['architecture']}\n")
                f.write(f"  - Processeur: {sys_info['processor']}\n")
                f.write(f"  - RAM: {sys_info['ram']:.2f} Go\n")
                f.write(f"  - CPU physiques/logiques: {sys_info['cpu_count']}/{sys_info['cpu_count_logical']}\n\n")
                
                if "loc" in self.results["code_metrics"]:
                    loc = self.results["code_metrics"]["loc"]
                    f.write("Métriques de code:\n")
                    f.write(f"  - Lignes totales: {loc['total_lines']}\n")
                    f.write(f"  - Lignes de code: {loc['code_lines']}\n")
                    f.write(f"  - Lignes de commentaires: {loc['comment_lines']} ")
                    f.write(f"({loc['comment_ratio']*100:.1f}%)\n")
                    f.write(f"  - Lignes vides: {loc['empty_lines']}\n\n")
                
                if "functions" in self.results["code_metrics"]:
                    f.write(f"Nombre de fonctions: {len(self.results['code_metrics']['functions'])}\n")
                
                if "classes" in self.results["code_metrics"]:
                    f.write(f"Nombre de classes: {len(self.results['code_metrics']['classes'])}\n\n")
                
                if "execution_time" in self.results["performance"]:
                    exec_time = self.results["performance"]["execution_time"]
                    if "error" not in exec_time:
                        f.write("Temps d'exécution:\n")
                        f.write(f"  - Minimum: {exec_time['min']:.4f} secondes\n")
                        f.write(f"  - Maximum: {exec_time['max']:.4f} secondes\n")
                        f.write(f"  - Moyenne: {exec_time['mean']:.4f} secondes\n")
                        f.write(f"  - Médiane: {exec_time['median']:.4f} secondes\n")
                        f.write(f"  - Écart-type: {exec_time['stdev']:.4f} secondes\n\n")
                
                if "memory_usage" in self.results["performance"]:
                    mem_usage = self.results["performance"]["memory_usage"]
                    if "error" not in mem_usage:
                        f.write("Utilisation mémoire:\n")
                        f.write(f"  - Minimum: {mem_usage['min']:.2f} Mo\n")
                        f.write(f"  - Maximum: {mem_usage['max']:.2f} Mo\n")
                        f.write(f"  - Moyenne: {mem_usage['mean']:.2f} Mo\n")
                        f.write(f"  - Médiane: {mem_usage['median']:.2f} Mo\n")
                        f.write(f"  - Écart-type: {mem_usage['stdev']:.2f} Mo\n\n")
                
                if "cpu_usage" in self.results["performance"]:
                    cpu_usage = self.results["performance"]["cpu_usage"]
                    if "error" not in cpu_usage:
                        f.write("Utilisation CPU:\n")
                        f.write(f"  - Minimum: {cpu_usage['min']:.2f}%\n")
                        f.write(f"  - Maximum: {cpu_usage['max']:.2f}%\n")
                        f.write(f"  - Moyenne: {cpu_usage['mean']:.2f}%\n")
                        f.write(f"  - Médiane: {cpu_usage['median']:.2f}%\n")
                        f.write(f"  - Écart-type: {cpu_usage['stdev']:.2f}%\n\n")
                
                if "io_operations" in self.results["performance"]:
                    io_ops = self.results["performance"]["io_operations"]
                    if "error" not in io_ops:
                        f.write("Opérations I/O:\n")
                        f.write("  Lecture:\n")
                        f.write(f"    - Moyenne: {io_ops['read_bytes']['mean']/1024:.2f} Ko\n")
                        f.write(f"    - Maximum: {io_ops['read_bytes']['max']/1024:.2f} Ko\n")
                        f.write("  Écriture:\n")
                        f.write(f"    - Moyenne: {io_ops['write_bytes']['mean']/1024:.2f} Ko\n")
                        f.write(f"    - Maximum: {io_ops['write_bytes']['max']/1024:.2f} Ko\n\n")
                
                if "complexity_analysis" in self.results["performance"]:
                    complexity = self.results["performance"]["complexity_analysis"]
                    if complexity and isinstance(complexity, dict) and not "error" in complexity:
                        f.write("Analyse de complexité:\n")
                        for func, analysis in complexity.items():
                            if "complexity_class" in analysis:
                                f.write(f"  - {func}: {analysis['complexity_class']}\n")
                        f.write("\n")
                
                if "issues" in self.results and self.results["issues"]:
                    f.write("Problèmes détectés:\n")
                    for issue in self.results["issues"]:
                        f.write(f"  - [{issue['severity'].upper()}] {issue['description']}\n")
                    f.write("\n")
                
                f.write("\nRapport généré le " + datetime.now().strftime("%Y-%m-%d à %H:%M:%S") + "\n")
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport texte: {e}")
            return None
        
        logger.info(f"Rapport texte généré: {output_file}")
        return output_file
    
    def generate_markdown_report(self):
        """Génère un rapport au format Markdown"""
        output_file = os.path.join(self.output_dir, "performance_report.md")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Rapport d'analyse de performance\n\n")
                
                meta = self.results["metadata"]
                f.write("## Informations générales\n\n")
                f.write(f"- **Date d'analyse:** {meta['timestamp']}\n")
                f.write(f"- **Fichier analysé:** `{meta['file_name']}`\n")
                f.write(f"- **Langage détecté:** {meta['language']}\n")
                f.write(f"- **Taille du fichier:** {meta['file_size']} octets\n")
                f.write(f"- **Nombre d'itérations:** {meta['iterations']}\n")
                f.write(f"- **Niveau de test:** {meta['test_level']}\n\n")
                
                sys_info = meta["system_info"]
                f.write("## Informations système\n\n")
                f.write(f"- **Plateforme:** {sys_info['platform']} {sys_info['platform_release']}\n")
                f.write(f"- **Architecture:** {sys_info['architecture']}\n")
                f.write(f"- **Processeur:** {sys_info['processor']}\n")
                f.write(f"- **RAM:** {sys_info['ram']:.2f} Go\n")
                f.write(f"- **CPU physiques/logiques:** {sys_info['cpu_count']}/{sys_info['cpu_count_logical']}\n\n")
                
                f.write("## Métriques de code\n\n")
                
                if "loc" in self.results["code_metrics"]:
                    loc = self.results["code_metrics"]["loc"]
                    f.write("### Structure du code\n\n")
                    f.write("| Métrique | Valeur |\n")
                    f.write("|---------|-------|\n")
                    f.write(f"| Lignes totales | {loc['total_lines']} |\n")
                    f.write(f"| Lignes de code | {loc['code_lines']} |\n")
                    f.write(f"| Lignes de commentaires | {loc['comment_lines']} ({loc['comment_ratio']*100:.1f}%) |\n")
                    f.write(f"| Lignes vides | {loc['empty_lines']} |\n\n")
                
                if "functions" in self.results["code_metrics"]:
                    f.write("### Fonctions\n\n")
                    f.write(f"Nombre total de fonctions: **{len(self.results['code_metrics']['functions'])}**\n\n")
                    if self.verbose and self.results["code_metrics"]["functions"]:
                        f.write("| Nom de fonction | Position |\n")
                        f.write("|----------------|----------|\n")
                        for func in self.results["code_metrics"]["functions"]:
                            f.write(f"| `{func['name']}` | {func['position']} |\n")
                        f.write("\n")
                
                if "classes" in self.results["code_metrics"]:
                    f.write("### Classes\n\n")
                    f.write(f"Nombre total de classes: **{len(self.results['code_metrics']['classes'])}**\n\n")
                    if self.verbose and self.results["code_metrics"]["classes"]:
                        f.write("| Nom de classe | Position |\n")
                        f.write("|--------------|----------|\n")
                        for cls in self.results["code_metrics"]["classes"]:
                            f.write(f"| `{cls['name']}` | {cls['position']} |\n")
                        f.write("\n")
                
                f.write("## Résultats de performance\n\n")
                
                if "execution_time" in self.results["performance"]:
                    exec_time = self.results["performance"]["execution_time"]
                    if "error" not in exec_time:
                        f.write("### Temps d'exécution\n\n")
                        f.write("| Métrique | Valeur (secondes) |\n")
                        f.write("|---------|------------------|\n")
                        f.write(f"| Minimum | {exec_time['min']:.4f} |\n")
                        f.write(f"| Maximum | {exec_time['max']:.4f} |\n")
                        f.write(f"| Moyenne | {exec_time['mean']:.4f} |\n")
                        f.write(f"| Médiane | {exec_time['median']:.4f} |\n")
                        f.write(f"| Écart-type | {exec_time['stdev']:.4f} |\n\n")
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "execution_time.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "execution_time.png")
                                f.write(f"![Graphique des temps d'exécution]({chart_path})\n\n")
                
                if "memory_usage" in self.results["performance"]:
                    mem_usage = self.results["performance"]["memory_usage"]
                    if "error" not in mem_usage:
                        f.write("### Utilisation mémoire\n\n")
                        f.write("| Métrique | Valeur (Mo) |\n")
                        f.write("|---------|------------|\n")
                        f.write(f"| Minimum | {mem_usage['min']:.2f} |\n")
                        f.write(f"| Maximum | {mem_usage['max']:.2f} |\n")
                        f.write(f"| Moyenne | {mem_usage['mean']:.2f} |\n")
                        f.write(f"| Médiane | {mem_usage['median']:.2f} |\n")
                        f.write(f"| Écart-type | {mem_usage['stdev']:.2f} |\n\n")
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "memory_usage.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "memory_usage.png")
                                f.write(f"![Graphique d'utilisation mémoire]({chart_path})\n\n")
                
                if "cpu_usage" in self.results["performance"]:
                    cpu_usage = self.results["performance"]["cpu_usage"]
                    if "error" not in cpu_usage:
                        f.write("### Utilisation CPU\n\n")
                        f.write("| Métrique | Valeur (%) |\n")
                        f.write("|---------|----------|\n")
                        f.write(f"| Minimum | {cpu_usage['min']:.2f} |\n")
                        f.write(f"| Maximum | {cpu_usage['max']:.2f} |\n")
                        f.write(f"| Moyenne | {cpu_usage['mean']:.2f} |\n")
                        f.write(f"| Médiane | {cpu_usage['median']:.2f} |\n")
                        f.write(f"| Écart-type | {cpu_usage['stdev']:.2f} |\n\n")
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "cpu_usage.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "cpu_usage.png")
                                f.write(f"![Graphique d'utilisation CPU]({chart_path})\n\n")
                
                if "io_operations" in self.results["performance"]:
                    io_ops = self.results["performance"]["io_operations"]
                    if "error" not in io_ops:
                        f.write("### Opérations I/O\n\n")
                        f.write("#### Lecture\n\n")
                        f.write("| Métrique | Valeur (Ko) |\n")
                        f.write("|---------|------------|\n")
                        f.write(f"| Minimum | {io_ops['read_bytes']['min']/1024:.2f} |\n")
                        f.write(f"| Maximum | {io_ops['read_bytes']['max']/1024:.2f} |\n")
                        f.write(f"| Moyenne | {io_ops['read_bytes']['mean']/1024:.2f} |\n")
                        f.write(f"| Médiane | {io_ops['read_bytes']['median']/1024:.2f} |\n\n")
                        
                        f.write("#### Écriture\n\n")
                        f.write("| Métrique | Valeur (Ko) |\n")
                        f.write("|---------|------------|\n")
                        f.write(f"| Minimum | {io_ops['write_bytes']['min']/1024:.2f} |\n")
                        f.write(f"| Maximum | {io_ops['write_bytes']['max']/1024:.2f} |\n")
                        f.write(f"| Moyenne | {io_ops['write_bytes']['mean']/1024:.2f} |\n")
                        f.write(f"| Médiane | {io_ops['write_bytes']['median']/1024:.2f} |\n\n")
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "io_operations.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "io_operations.png")
                                f.write(f"![Graphique des opérations I/O]({chart_path})\n\n")
                
                if "complexity_analysis" in self.results["performance"]:
                    complexity = self.results["performance"]["complexity_analysis"]
                    if complexity and isinstance(complexity, dict) and not "error" in complexity:
                        f.write("### Analyse de complexité algorithmique\n\n")
                        f.write("| Fonction | Complexité |\n")
                        f.write("|---------|----------|\n")
                        for func, analysis in complexity.items():
                            if "complexity_class" in analysis:
                                f.write(f"| `{func}` | {analysis['complexity_class']} |\n")
                        f.write("\n")
                
                if "issues" in self.results and self.results["issues"]:
                    f.write("## Problèmes détectés\n\n")
                    for issue in self.results["issues"]:
                        severity = "⚠️" if issue['severity'] == "warning" else "❌"
                        f.write(f"- {severity} **{issue['type']}**: {issue['description']}\n")
                    f.write("\n")
                
                f.write("\n---\n")
                f.write(f"*Rapport généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')} par CodePerformanceMonitor*\n")
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport Markdown: {e}")
            return None
        
        logger.info(f"Rapport Markdown généré: {output_file}")
        return output_file
    
    def generate_html_report(self):
        """Génère un rapport au format HTML"""
        output_file = os.path.join(self.output_dir, "performance_report.html")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport d'analyse de performance</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #2980b9;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
            margin-top: 30px;
        }
        h3 {
            color: #3498db;
        }
        .container {
            background-color: #f9f9f9;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px 15px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .warning {
            color: #ff9800;
            font-weight: bold;
        }
        .error {
            color: #f44336;
            font-weight: bold;
        }
        .chart {
            max-width: 100%;
            height: auto;
            margin: 20px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #777;
        }
        code {
            background-color: #f5f5f5;
            padding: 2px 5px;
            border-radius: 3px;
            font-family: monospace;
        }
        .metric-card {
            display: inline-block;
            width: 30%;
            margin: 1%;
            background-color: white;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2980b9;
        }
        .metric-label {
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        @media (max-width: 768px) {
            .metric-card {
                width: 100%;
                margin: 10px 0;
            }
        }
    </style>
</head>
<body>
""")
                
                meta = self.results["metadata"]
                
                f.write(f"""
    <h1>Rapport d'analyse de performance</h1>
    
    <div class="container">
        <h2>Informations générales</h2>
        <table>
            <tr><th>Date d'analyse</th><td>{meta['timestamp']}</td></tr>
            <tr><th>Fichier analysé</th><td><code>{meta['file_name']}</code></td></tr>
            <tr><th>Langage détecté</th><td>{meta['language']}</td></tr>
            <tr><th>Taille du fichier</th><td>{meta['file_size']} octets</td></tr>
            <tr><th>Nombre d'itérations</th><td>{meta['iterations']}</td></tr>
            <tr><th>Niveau de test</th><td>{meta['test_level']}</td></tr>
        </table>
    </div>
""")
                
                sys_info = meta["system_info"]
                f.write(f"""
    <div class="container">
        <h2>Informations système</h2>
        <table>
            <tr><th>Plateforme</th><td>{sys_info['platform']} {sys_info['platform_release']}</td></tr>
            <tr><th>Architecture</th><td>{sys_info['architecture']}</td></tr>
            <tr><th>Processeur</th><td>{sys_info['processor']}</td></tr>
            <tr><th>RAM</th><td>{sys_info['ram']:.2f} Go</td></tr>
            <tr><th>CPU physiques/logiques</th><td>{sys_info['cpu_count']}/{sys_info['cpu_count_logical']}</td></tr>
        </table>
    </div>
""")
                
                f.write("""
    <div class="container">
        <h2>Métriques de code</h2>
""")
                
                if "loc" in self.results["code_metrics"]:
                    loc = self.results["code_metrics"]["loc"]
                    f.write(f"""
        <h3>Structure du code</h3>
        <div class="metric-card">
            <div class="metric-label">Lignes totales</div>
            <div class="metric-value">{loc['total_lines']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Lignes de code</div>
            <div class="metric-value">{loc['code_lines']}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Lignes de commentaires</div>
            <div class="metric-value">{loc['comment_lines']} ({loc['comment_ratio']*100:.1f}%)</div>
        </div>
""")
                
                if "functions" in self.results["code_metrics"]:
                    f.write(f"""
        <h3>Fonctions</h3>
        <p>Nombre total de fonctions: <strong>{len(self.results['code_metrics']['functions'])}</strong></p>
""")
                    
                    if self.verbose and self.results["code_metrics"]["functions"]:
                        f.write("""
        <table>
            <tr>
                <th>Nom de fonction</th>
                <th>Position</th>
            </tr>
""")
                        for func in self.results["code_metrics"]["functions"]:
                            f.write(f"            <tr><td><code>{func['name']}</code></td><td>{func['position']}</td></tr>\n")
                        f.write("        </table>\n")
                
                if "classes" in self.results["code_metrics"]:
                    f.write(f"""
        <h3>Classes</h3>
        <p>Nombre total de classes: <strong>{len(self.results['code_metrics']['classes'])}</strong></p>
""")
                    
                    if self.verbose and self.results["code_metrics"]["classes"]:
                        f.write("""
        <table>
            <tr>
                <th>Nom de classe</th>
                <th>Position</th>
            </tr>
""")
                        for cls in self.results["code_metrics"]["classes"]:
                            f.write(f"            <tr><td><code>{cls['name']}</code></td><td>{cls['position']}</td></tr>\n")
                        f.write("        </table>\n")
                
                f.write("    </div>\n")  
                f.write("""
    <div class="container">
        <h2>Résultats de performance</h2>
""")
                
                if "execution_time" in self.results["performance"]:
                    exec_time = self.results["performance"]["execution_time"]
                    if "error" not in exec_time:
                        f.write("""
        <h3>Temps d'exécution</h3>
        <div class="metric-card">
            <div class="metric-label">Minimum</div>
            <div class="metric-value">{:.4f} s</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Maximum</div>
            <div class="metric-value">{:.4f} s</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Moyenne</div>
            <div class="metric-value">{:.4f} s</div>
        </div>
""".format(exec_time['min'], exec_time['max'], exec_time['mean']))
                        
                        f.write("""
        <table>
            <tr>
                <th>Métrique</th>
                <th>Valeur (secondes)</th>
            </tr>
            <tr><td>Minimum</td><td>{:.4f}</td></tr>
            <tr><td>Maximum</td><td>{:.4f}</td></tr>
            <tr><td>Moyenne</td><td>{:.4f}</td></tr>
            <tr><td>Médiane</td><td>{:.4f}</td></tr>
            <tr><td>Écart-type</td><td>{:.4f}</td></tr>
        </table>
""".format(exec_time['min'], exec_time['max'], exec_time['mean'], exec_time['median'], exec_time['stdev']))
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "execution_time.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "execution_time.png")
                                f.write(f"""
        <div>
            <img src="{chart_path}" alt="Graphique des temps d'exécution" class="chart">
        </div>
""")
                
                if "memory_usage" in self.results["performance"]:
                    mem_usage = self.results["performance"]["memory_usage"]
                    if "error" not in mem_usage:
                        f.write("""
        <h3>Utilisation mémoire</h3>
        <div class="metric-card">
            <div class="metric-label">Minimum</div>
            <div class="metric-value">{:.2f} Mo</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Maximum</div>
            <div class="metric-value">{:.2f} Mo</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Moyenne</div>
            <div class="metric-value">{:.2f} Mo</div>
        </div>
""".format(mem_usage['min'], mem_usage['max'], mem_usage['mean']))
                        
                        f.write("""
        <table>
            <tr>
                <th>Métrique</th>
                <th>Valeur (Mo)</th>
            </tr>
            <tr><td>Minimum</td><td>{:.2f}</td></tr>
            <tr><td>Maximum</td><td>{:.2f}</td></tr>
            <tr><td>Moyenne</td><td>{:.2f}</td></tr>
            <tr><td>Médiane</td><td>{:.2f}</td></tr>
            <tr><td>Écart-type</td><td>{:.2f}</td></tr>
        </table>
""".format(mem_usage['min'], mem_usage['max'], mem_usage['mean'], mem_usage['median'], mem_usage['stdev']))
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "memory_usage.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "memory_usage.png")
                                f.write(f"""
        <div>
            <img src="{chart_path}" alt="Graphique d'utilisation mémoire" class="chart">
        </div>
""")
                
                if "cpu_usage" in self.results["performance"]:
                    cpu_usage = self.results["performance"]["cpu_usage"]
                    if "error" not in cpu_usage:
                        f.write("""
        <h3>Utilisation CPU</h3>
        <div class="metric-card">
            <div class="metric-label">Minimum</div>
            <div class="metric-value">{:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Maximum</div>
            <div class="metric-value">{:.2f}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Moyenne</div>
            <div class="metric-value">{:.2f}%</div>
        </div>
""".format(cpu_usage['min'], cpu_usage['max'], cpu_usage['mean']))
                        
                        f.write("""
        <table>
            <tr>
                <th>Métrique</th>
                <th>Valeur (%)</th>
            </tr>
            <tr><td>Minimum</td><td>{:.2f}</td></tr>
            <tr><td>Maximum</td><td>{:.2f}</td></tr>
            <tr><td>Moyenne</td><td>{:.2f}</td></tr>
            <tr><td>Médiane</td><td>{:.2f}</td></tr>
            <tr><td>Écart-type</td><td>{:.2f}</td></tr>
        </table>
""".format(cpu_usage['min'], cpu_usage['max'], cpu_usage['mean'], cpu_usage['median'], cpu_usage['stdev']))
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "cpu_usage.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "cpu_usage.png")
                                f.write(f"""
        <div>
            <img src="{chart_path}" alt="Graphique d'utilisation CPU" class="chart">
        </div>
""")
                
                if "io_operations" in self.results["performance"]:
                    io_ops = self.results["performance"]["io_operations"]
                    if "error" not in io_ops:
                        f.write("""
        <h3>Opérations I/O</h3>
        <h4>Lecture</h4>
        <table>
            <tr>
                <th>Métrique</th>
                <th>Valeur (Ko)</th>
            </tr>
            <tr><td>Minimum</td><td>{:.2f}</td></tr>
            <tr><td>Maximum</td><td>{:.2f}</td></tr>
            <tr><td>Moyenne</td><td>{:.2f}</td></tr>
            <tr><td>Médiane</td><td>{:.2f}</td></tr>
        </table>
        
        <h4>Écriture</h4>
        <table>
            <tr>
                <th>Métrique</th>
                <th>Valeur (Ko)</th>
            </tr>
            <tr><td>Minimum</td><td>{:.2f}</td></tr>
            <tr><td>Maximum</td><td>{:.2f}</td></tr>
            <tr><td>Moyenne</td><td>{:.2f}</td></tr>
            <tr><td>Médiane</td><td>{:.2f}</td></tr>
        </table>
""".format(io_ops['read_bytes']['min']/1024, io_ops['read_bytes']['max']/1024, 
           io_ops['read_bytes']['mean']/1024, io_ops['read_bytes']['median']/1024,
           io_ops['write_bytes']['min']/1024, io_ops['write_bytes']['max']/1024,
           io_ops['write_bytes']['mean']/1024, io_ops['write_bytes']['median']/1024))
                        
                        if self.show_charts and "visualization" in self.results and "available_charts" in self.results["visualization"]:
                            if "io_operations.png" in self.results["visualization"]["available_charts"]:
                                chart_path = os.path.join("charts", "io_operations.png")
                                f.write(f"""
        <div>
            <img src="{chart_path}" alt="Graphique des opérations I/O" class="chart">
        </div>
""")
                
                if "complexity_analysis" in self.results["performance"]:
                    complexity = self.results["performance"]["complexity_analysis"]
                    if complexity and isinstance(complexity, dict) and not "error" in complexity:
                        f.write("""
        <h3>Analyse de complexité algorithmique</h3>
        <table>
            <tr>
                <th>Fonction</th>
                <th>Complexité</th>
            </tr>
""")
                        for func, analysis in complexity.items():
                            if "complexity_class" in analysis:
                                f.write(f"            <tr><td><code>{func}</code></td><td>{analysis['complexity_class']}</td></tr>\n")
                        f.write("        </table>\n")
                
                f.write("    </div>\n") 
                
                if "issues" in self.results and self.results["issues"]:
                    f.write("""
    <div class="container">
        <h2>Problèmes détectés</h2>
        <table>
            <tr>
                <th>Type</th>
                <th>Sévérité</th>
                <th>Description</th>
            </tr>
""")
                    for issue in self.results["issues"]:
                        severity_class = "warning" if issue['severity'] == "warning" else "error"
                        severity_icon = "⚠️" if issue['severity'] == "warning" else "❌"
                        f.write(f"""            <tr>
                <td>{issue['type']}</td>
                <td class="{severity_class}">{severity_icon} {issue['severity'].upper()}</td>
                <td>{issue['description']}</td>
            </tr>
""")
                    f.write("        </table>\n    </div>\n")
                
                f.write(f"""
    <div class="footer">
        <p>Rapport généré le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')} par CodePerformanceMonitor</p>
    </div>
</body>
</html>
""")
        
        except Exception as e:
            return None
        
        logger.info(f"Rapport HTML généré: {output_file}")
        return output_file
    
    def generate_charts(self):
        """Génère les graphiques pour visualiser les données de performance"""
        charts_dir = os.path.join(self.output_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        charts_generated = []
        
        try:
            if "execution_time" in self.results["performance"] and "raw_data" in self.results["performance"]["execution_time"]:
                exec_time_data = self.results["performance"]["execution_time"]["raw_data"]
                if exec_time_data:
                    plt.figure(figsize=(10, 6))
                    plt.plot(exec_time_data, 'b-', label='Temps d\'exécution')
                    plt.axhline(y=self.results["performance"]["execution_time"]["mean"], 
                               color='r', linestyle='-', label='Moyenne')
                    plt.xlabel('Itération')
                    plt.ylabel('Temps (secondes)')
                    plt.title('Temps d\'exécution par itération')
                    plt.legend()
                    plt.grid(True)
                    plt.tight_layout()
                    chart_path = os.path.join(charts_dir, "execution_time.png")
                    plt.savefig(chart_path)
                    plt.close()
                    charts_generated.append("execution_time.png")
                    logger.debug(f"Graphique de temps d'exécution généré: {chart_path}")
            
            if "memory_usage" in self.results["performance"] and "raw_data" in self.results["performance"]["memory_usage"]:
                mem_data = self.results["performance"]["memory_usage"]["raw_data"]
                if mem_data:
                    plt.figure(figsize=(10, 6))
                    plt.plot(mem_data, 'g-', label='Utilisation mémoire')
                    plt.axhline(y=self.results["performance"]["memory_usage"]["mean"], 
                               color='r', linestyle='-', label='Moyenne')
                    plt.xlabel('Itération')
                    plt.ylabel('Mémoire (Mo)')
                    plt.title('Utilisation mémoire par itération')
                    plt.legend()
                    plt.grid(True)
                    plt.tight_layout()
                    chart_path = os.path.join(charts_dir, "memory_usage.png")
                    plt.savefig(chart_path)
                    plt.close()
                    charts_generated.append("memory_usage.png")
                    logger.debug(f"Graphique d'utilisation mémoire généré: {chart_path}")
            
            if "cpu_usage" in self.results["performance"] and "raw_data" in self.results["performance"]["cpu_usage"]:
                cpu_data = self.results["performance"]["cpu_usage"]["raw_data"]
                if cpu_data:
                    plt.figure(figsize=(10, 6))
                    plt.plot(cpu_data, 'r-', label='Utilisation CPU')
                    plt.axhline(y=self.results["performance"]["cpu_usage"]["mean"], 
                               color='b', linestyle='-', label='Moyenne')
                    plt.xlabel('Itération')
                    plt.ylabel('CPU (%)')
                    plt.title('Utilisation CPU par itération')
                    plt.legend()
                    plt.grid(True)
                    plt.tight_layout()
                    chart_path = os.path.join(charts_dir, "cpu_usage.png")
                    plt.savefig(chart_path)
                    plt.close()
                    charts_generated.append("cpu_usage.png")
                    logger.debug(f"Graphique d'utilisation CPU généré: {chart_path}")
            
            if ("io_operations" in self.results["performance"] and 
                "read_bytes" in self.results["performance"]["io_operations"] and 
                "write_bytes" in self.results["performance"]["io_operations"] and
                "raw_data" in self.results["performance"]["io_operations"]["read_bytes"] and
                "raw_data" in self.results["performance"]["io_operations"]["write_bytes"]):
                
                read_data = self.results["performance"]["io_operations"]["read_bytes"]["raw_data"]
                write_data = self.results["performance"]["io_operations"]["write_bytes"]["raw_data"]
                
                if read_data and write_data and len(read_data) == len(write_data):
                    plt.figure(figsize=(10, 6))
                    plt.plot([r/1024 for r in read_data], 'b-', label='Lecture')
                    plt.plot([w/1024 for w in write_data], 'g-', label='Écriture')
                    plt.xlabel('Itération')
                    plt.ylabel('Ko')
                    plt.title('Opérations I/O par itération')
                    plt.legend()
                    plt.grid(True)
                    plt.tight_layout()
                    chart_path = os.path.join(charts_dir, "io_operations.png")
                    plt.savefig(chart_path)
                    plt.close()
                    charts_generated.append("io_operations.png")
                    logger.debug(f"Graphique des opérations I/O généré: {chart_path}")
            
            if "visualization" not in self.results:
                self.results["visualization"] = {}
            
            self.results["visualization"]["available_charts"] = charts_generated
            
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)
            
            logger.info(f"{len(charts_generated)} graphiques générés dans {charts_dir}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des graphiques: {e}")
    
    def run(self):
        """Exécute le processus complet de génération de rapport"""
        if self.show_charts:
            self.generate_charts()
        
        report_file = self.generate_report()
        
        if report_file:
            logger.info(f"Rapport généré avec succès: {report_file}")
            return report_file
        else:
            return None

def main():
    parser = argparse.ArgumentParser(description='Génère un rapport de performance à partir des résultats d\'analyse.')
    parser.add_argument('-r', '--results', required=True, help='Chemin vers le fichier de résultats JSON')
    parser.add_argument('--output', '-o', help='Répertoire de sortie pour le rapport')
    parser.add_argument('--format', '-f', choices=['html', 'markdown', 'text'], default='html',
                        help='Format du rapport (html, markdown, text)')
    parser.add_argument('--no-charts', '-nc', action='store_true', help='Ne pas générer de graphiques')
    parser.add_argument('--verbose', '-v', action='store_true', help='Afficher plus d\'informations dans le rapport')
    parser.add_argument('--open', '-op', action='store_true', help='Ouvrir le rapport après génération')
    
    args = parser.parse_args()
    

    generator = ReportGenerator(
        results_file=args.results,
        output_dir=args.output,
        format=args.format,
        verbose=args.verbose,
        show_charts=not args.no_charts
    )
    
    report_file = generator.run()
    
    if args.open and report_file:
        try:
            webbrowser.open(f'file://{os.path.abspath(report_file)}')
        except Exception as e:
            logger.error(f"Impossible d'ouvrir le rapport: {e}")

if __name__ == "__main__":
    main()