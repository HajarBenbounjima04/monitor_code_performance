import os
import sys
import time
import json
import signal
import argparse
import subprocess
import statistics
import traceback
import tempfile
import re
from datetime import datetime
import shutil
import platform
from pathlib import Path
import threading
import concurrent.futures
import logging

try:
    import psutil
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from memory_profiler import memory_usage
    import big_o
except ImportError as e:
    print(f"Erreur: bibliothèque manquante - {e}")
    print("Veuillez installer les dépendances avec: pip install matplotlib numpy pandas psutil memory_profiler line_profiler py-spy big_o")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger('CodeAnalyzer')

class CodeAnalyzer:
    def __init__(self, file_path, output_dir, iterations=5, verbose=False, test_level="medium", program_args=""):
        self.file_path = os.path.abspath(file_path)
        self.file_name = os.path.basename(file_path)
        self.file_extension = os.path.splitext(file_path)[1][1:].lower()
        self.output_dir = output_dir
        self.iterations = iterations
        self.verbose = verbose
        self.test_level = test_level
        self.program_args = program_args.split() if program_args else []
        self.results = {
            "metadata": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_name": self.file_name,
                "file_size": os.path.getsize(file_path),
                "language": self.detect_language(),
                "iterations": iterations,
                "test_level": test_level,
                "system_info": self.get_system_info()
            },
            "performance": {
                "execution_time": {},
                "memory_usage": {},
                "cpu_usage": {},
                "io_operations": {},
                "complexity_analysis": {}
            },
            "code_metrics": {
                "loc": 0,
                "complexity": 0,
                "functions": [],
                "classes": [],
                "imports": []
            },
            "issues": []
        }
        
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_factors = {
            "light": 1,
            "medium": 5,
            "heavy": 20
        }
        
        logger.debug(f"Initialisé l'analyseur pour {self.file_path} avec {iterations} itérations en mode {test_level}")
    
    def detect_language(self):
        """Détecte le langage de programmation en fonction de l'extension de fichier"""
        language_map = {
            "py": "Python",
            "js": "JavaScript",
            "java": "Java",
            "c": "C",
            "cpp": "C++",
            "h": "C/C++ Header",
            "hpp": "C++ Header",
            "cs": "C#",
            "go": "Go",
            "rb": "Ruby",
            "php": "PHP",
            "pl": "Perl",
            "sh": "Bash/Shell",
            "r": "R",
            "swift": "Swift",
            "ts": "TypeScript"
        }
        
        return language_map.get(self.file_extension, "Unknown")
    
    def get_system_info(self):
        """Récupère les informations système"""
        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "ram": psutil.virtual_memory().total / (1024 ** 3),  # En Go
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True)
        }
        return system_info
    
    def count_lines_of_code(self):
        """Compte les lignes de code, commentaires et lignes vides"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.readlines()
            
            total_lines = len(content)
            empty_lines = len([line for line in content if line.strip() == ''])
            
            if self.file_extension == 'py':
                comment_pattern = r'^\s*#'
            elif self.file_extension in ['js', 'java', 'c', 'cpp', 'cs']:
                comment_pattern = r'^\s*(//|/\*|\*)'
            else:
                comment_pattern = r'^\s*(#|//|/\*|\*)'
            
            comment_lines = len([line for line in content if re.match(comment_pattern, line.strip())])
            code_lines = total_lines - empty_lines - comment_lines
            
            metrics = {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "empty_lines": empty_lines,
                "comment_ratio": comment_lines / total_lines if total_lines > 0 else 0
            }
            
            self.results["code_metrics"]["loc"] = metrics
            return metrics
        
        except Exception as e:
            logger.error(f"Erreur lors du comptage des lignes de code: {e}")
            return {"error": str(e)}
    
    def analyze_imports(self):
        """Analyse les imports/includes dans le code"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            imports = []
            
            if self.file_extension == 'py':
                import_patterns = [
                    r'import\s+([a-zA-Z0-9_.,\s]+)',
                    r'from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_.,\s*]+)'
                ]
                
                for pattern in import_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        if len(match.groups()) == 1:
                            modules = match.group(1).split(',')
                            for module in modules:
                                imports.append(module.strip())
                        elif len(match.groups()) == 2:
                            module = match.group(1)
                            imports.append(f"{module}.{match.group(2)}")
            
            elif self.file_extension in ['c', 'cpp', 'h', 'hpp']:
                include_pattern = r'#include\s+[<"]([^>"]+)[>"]'
                matches = re.finditer(include_pattern, content)
                for match in matches:
                    imports.append(match.group(1))
            
            elif self.file_extension in ['java']:
                import_pattern = r'import\s+([a-zA-Z0-9_.]+\*?);'
                matches = re.finditer(import_pattern, content)
                for match in matches:
                    imports.append(match.group(1))
            
            self.results["code_metrics"]["imports"] = imports
            return imports
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des imports: {e}")
            return {"error": str(e)}
    
    def analyze_functions(self):
        """Analyse les fonctions/méthodes dans le code"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            functions = []
            
            if self.file_extension == 'py':
                function_pattern = r'def\s+([a-zA-Z0-9_]+)\s*\('
                matches = re.finditer(function_pattern, content)
                for match in matches:
                    function_name = match.group(1)
                    start_pos = match.start()
                    
                    lines_before = content[:start_pos].splitlines()
                    decorators = []
                    
                    if lines_before:
                        line_idx = len(lines_before) - 1
                        while line_idx >= 0 and '@' in lines_before[line_idx]:
                            decorator = lines_before[line_idx].strip()
                            decorators.append(decorator)
                            line_idx -= 1
                    
                    functions.append({
                        "name": function_name,
                        "decorators": decorators[::-1] if decorators else [],
                        "position": start_pos
                    })
            
            elif self.file_extension in ['c', 'cpp', 'h', 'hpp']:
                function_pattern = r'(\w+)\s+(\w+)\s*\([^)]*\)\s*{'
                matches = re.finditer(function_pattern, content)
                for match in matches:
                    return_type = match.group(1)
                    function_name = match.group(2)
                    
                    if return_type not in ['if', 'for', 'while', 'switch']:
                        functions.append({
                            "name": function_name,
                            "return_type": return_type,
                            "position": match.start()
                        })
            
            elif self.file_extension in ['java']:
                method_pattern = r'(public|private|protected)?\s+\w+\s+(\w+)\s*\([^)]*\)\s*{'
                matches = re.finditer(method_pattern, content)
                for match in matches:
                    visibility = match.group(1) or "default"
                    method_name = match.group(2)
                    
                    functions.append({
                        "name": method_name,
                        "visibility": visibility,
                        "position": match.start()
                    })
            
            self.results["code_metrics"]["functions"] = functions
            return functions
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des fonctions: {e}")
            return {"error": str(e)}
    
    def analyze_classes(self):
        """Analyse les classes dans le code"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            classes = []
            
            if self.file_extension == 'py':
                class_pattern = r'class\s+([a-zA-Z0-9_]+)(?:\s*\(([^)]*)\))?:'
                matches = re.finditer(class_pattern, content)
                for match in matches:
                    class_name = match.group(1)
                    inheritance = match.group(2).split(',') if match.group(2) else []
                    inheritance = [cls.strip() for cls in inheritance]
                    
                    classes.append({
                        "name": class_name,
                        "inheritance": inheritance,
                        "position": match.start()
                    })
            
            elif self.file_extension in ['java', 'cpp', 'cs']:
                class_pattern = r'(public|private|protected)?\s+class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'
                matches = re.finditer(class_pattern, content)
                for match in matches:
                    visibility = match.group(1) or "default"
                    class_name = match.group(2)
                    parent_class = match.group(3) if match.group(3) else None
                    interfaces = match.group(4).split(',') if match.group(4) else []
                    interfaces = [intf.strip() for intf in interfaces]
                    
                    classes.append({
                        "name": class_name,
                        "visibility": visibility,
                        "parent_class": parent_class,
                        "interfaces": interfaces,
                        "position": match.start()
                    })
            
            self.results["code_metrics"]["classes"] = classes
            return classes
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des classes: {e}")
            return {"error": str(e)}
    
    def measure_execution_time(self):
        """Mesure le temps d'exécution du programme"""
        times = []
        command = self.get_execution_command()
        
        if not command:
            logger.error(f"Langage non supporté pour l'exécution: {self.file_extension}")
            return {"error": "Langage non supporté"}
        
        logger.debug(f"Commande d'exécution: {' '.join(command + self.program_args)}")
        
        for i in range(self.iterations):
            logger.debug(f"Itération de test {i+1}/{self.iterations}")
            
            try:
                start_time = time.time()
                completed_process = subprocess.run(
                    command + self.program_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=300 * self.load_factors[self.test_level] 
                )
                end_time = time.time()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                
                if self.verbose:
                    logger.debug(f"Temps d'exécution pour l'itération {i+1}: {execution_time:.4f} secondes")
                    if completed_process.returncode != 0:
                        logger.warning(f"Code de retour non nul: {completed_process.returncode}")
                        logger.warning(f"Stderr: {completed_process.stderr.decode('utf-8', errors='replace')}")
            
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout lors de l'exécution à l'itération {i+1}")
                times.append(300 * self.load_factors[self.test_level])
            
            except Exception as e:
                logger.error(f"Erreur lors de la mesure du temps d'exécution: {e}")
                times.append(float('nan'))
        
        valid_times = [t for t in times if not np.isnan(t)]
        
        if not valid_times:
            return {"error": "Toutes les exécutions ont échoué"}
        
        statistics_result = {
            "min": min(valid_times),
            "max": max(valid_times),
            "mean": statistics.mean(valid_times),
            "median": statistics.median(valid_times),
            "stdev": statistics.stdev(valid_times) if len(valid_times) > 1 else 0,
            "raw_data": times
        }
        
        self.results["performance"]["execution_time"] = statistics_result
        return statistics_result
    
    def measure_memory_usage(self):
        """Mesure l'utilisation de la mémoire du programme"""
        command = self.get_execution_command()
        
        if not command:
            logger.error(f"Langage non supporté pour l'analyse mémoire: {self.file_extension}")
            return {"error": "Langage non supporté"}
        
        memory_usages = []
        
        for i in range(self.iterations):
            logger.debug(f"Analyse mémoire - Itération {i+1}/{self.iterations}")
            
            try:
                if self.file_extension == 'py':
                    def run_script():
                        subprocess.run(
                            command + self.program_args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=300 * self.load_factors[self.test_level]
                        )
                    
                    mem_usage = memory_usage(
                        run_script,
                        interval=0.1,
                        timeout=300 * self.load_factors[self.test_level],
                        include_children=True
                    )
                    
                    peak_memory = max(mem_usage) if mem_usage else 0
                    memory_usages.append(peak_memory)
                
                else:
                    process = subprocess.Popen(
                        command + self.program_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    pid = process.pid
                    peak_memory = 0
                    
                    try:
                        p = psutil.Process(pid)
                        
                        while process.poll() is None:
                            try:
                                memory_info = p.memory_info()
                                current_memory = memory_info.rss / (1024 * 1024)  
                                peak_memory = max(peak_memory, current_memory)
                                time.sleep(0.1)
                            except psutil.NoSuchProcess:
                                break
                        
                        memory_usages.append(peak_memory)
                    
                    except psutil.NoSuchProcess:
                        logger.warning(f"Le processus {pid} a terminé avant de pouvoir mesurer la mémoire")
                    
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
            
            except Exception as e:
                logger.error(f"Erreur lors de la mesure de l'utilisation mémoire: {e}")
                memory_usages.append(float('nan'))
        
        valid_memory = [m for m in memory_usages if not np.isnan(m)]
        
        if not valid_memory:
            return {"error": "Toutes les mesures de mémoire ont échoué"}
        
        statistics_result = {
            "min": min(valid_memory),
            "max": max(valid_memory),
            "mean": statistics.mean(valid_memory),
            "median": statistics.median(valid_memory),
            "stdev": statistics.stdev(valid_memory) if len(valid_memory) > 1 else 0,
            "unit": "MB",
            "raw_data": memory_usages
        }
        
        self.results["performance"]["memory_usage"] = statistics_result
        return statistics_result
    
    def measure_cpu_usage(self):
        """Mesure l'utilisation CPU du programme"""
        command = self.get_execution_command()
        
        if not command:
            logger.error(f"Langage non supporté pour l'analyse CPU: {self.file_extension}")
            return {"error": "Langage non supporté"}
        
        cpu_usages = []
        
        for i in range(self.iterations):
            logger.debug(f"Analyse CPU - Itération {i+1}/{self.iterations}")
            
            try:
                process = subprocess.Popen(
                    command + self.program_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                pid = process.pid
                cpu_samples = []
                
                try:
                    p = psutil.Process(pid)
                    
                    start_time = time.time()
                    while process.poll() is None:
                        try:
                            cpu_percent = p.cpu_percent(interval=0.2)
                            cpu_samples.append(cpu_percent)
                            
                            if time.time() - start_time > 300 * self.load_factors[self.test_level]:
                                process.terminate()
                                break
                        except psutil.NoSuchProcess:
                            break
                    
                    avg_cpu = statistics.mean(cpu_samples) if cpu_samples else 0
                    cpu_usages.append(avg_cpu)
                
                except psutil.NoSuchProcess:
                    logger.warning(f"Le processus {pid} a terminé avant de pouvoir mesurer le CPU")
                
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            
            except Exception as e:
                logger.error(f"Erreur lors de la mesure de l'utilisation CPU: {e}")
                cpu_usages.append(float('nan'))
        
        valid_cpu = [c for c in cpu_usages if not np.isnan(c)]
        
        if not valid_cpu:
            return {"error": "Toutes les mesures CPU ont échoué"}
        
        statistics_result = {
            "min": min(valid_cpu),
            "max": max(valid_cpu),
            "mean": statistics.mean(valid_cpu),
            "median": statistics.median(valid_cpu),
            "stdev": statistics.stdev(valid_cpu) if len(valid_cpu) > 1 else 0,
            "unit": "percent",
            "raw_data": cpu_usages
        }
        
        self.results["performance"]["cpu_usage"] = statistics_result
        return statistics_result
    
    def measure_io_operations(self):
        """Mesure les opérations d'entrée/sortie du programme"""
        command = self.get_execution_command()
        
        if not command:
            logger.error(f"Langage non supporté pour l'analyse I/O: {self.file_extension}")
            return {"error": "Langage non supporté"}
        
        if platform.system() not in ['Linux', 'Darwin']:
            logger.warning("La mesure des opérations I/O n'est supportée que sur Linux/Unix")
            return {"error": "Système non supporté"}
        
        io_stats = []
        
        for i in range(self.iterations):
            logger.debug(f"Analyse I/O - Itération {i+1}/{self.iterations}")
            
            try:
                process = subprocess.Popen(
                    command + self.program_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                pid = process.pid
                read_bytes_start = 0
                write_bytes_start = 0
                
                try:
                    p = psutil.Process(pid)
                    
                    io_counters_start = p.io_counters() if hasattr(p, 'io_counters') else None
                    if io_counters_start:
                        read_bytes_start = io_counters_start.read_bytes
                        write_bytes_start = io_counters_start.write_bytes
                    
                    process.wait(timeout=300 * self.load_factors[self.test_level])
                    
                    io_counters_end = p.io_counters() if hasattr(p, 'io_counters') else None
                    
                    if io_counters_end:
                        read_bytes = io_counters_end.read_bytes - read_bytes_start
                        write_bytes = io_counters_end.write_bytes - write_bytes_start
                        
                        io_stats.append({
                            "read_bytes": read_bytes,
                            "write_bytes": write_bytes,
                            "total_bytes": read_bytes + write_bytes
                        })
                
                except psutil.NoSuchProcess:
                    logger.warning(f"Le processus {pid} a terminé avant de pouvoir mesurer les I/O")
                
                except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
                    process.terminate()
                    logger.warning("Timeout lors de la mesure des opérations I/O")
            
            except Exception as e:
                logger.error(f"Erreur lors de la mesure des opérations I/O: {e}")
        
        if not io_stats:
            return {"error": "Toutes les mesures I/O ont échoué"}
        
        read_values = [stat["read_bytes"] for stat in io_stats]
        write_values = [stat["write_bytes"] for stat in io_stats]
        total_values = [stat["total_bytes"] for stat in io_stats]
        
        statistics_result = {
            "read_bytes": {
                "min": min(read_values),
                "max": max(read_values),
                "mean": statistics.mean(read_values),
                "median": statistics.median(read_values),
                "stdev": statistics.stdev(read_values) if len(read_values) > 1 else 0
            },
            "write_bytes": {
                "min": min(write_values),
                "max": max(write_values),
                "mean": statistics.mean(write_values),
                "median": statistics.median(write_values),
                "stdev": statistics.stdev(write_values) if len(write_values) > 1 else 0
            },
            "total_bytes": {
                "min": min(total_values),
                "max": max(total_values),
                "mean": statistics.mean(total_values),
                "median": statistics.median(total_values),
                "stdev": statistics.stdev(total_values) if len(total_values) > 1 else 0
            },
            "raw_data": io_stats
        }
        
        self.results["performance"]["io_operations"] = statistics_result
        return statistics_result
    
    def analyze_complexity(self):
        """Analyse la complexité algorithmique (principalement pour Python)"""
        if self.file_extension != 'py':
            logger.warning(f"L'analyse de complexité automatique n'est actuellement supportée que pour Python")
            return {"error": "Langage non supporté"}
        
        try:
            temp_dir = tempfile.mkdtemp()
            temp_module_path = os.path.join(temp_dir, "temp_module.py")
            
            shutil.copy(self.file_path, temp_module_path)
            
            complexity_script = os.path.join(temp_dir, "complexity_analyzer.py")
            
            with open(complexity_script, 'w') as f:
                f.write("""
import sys
import os
import time
import importlib.util
import big_o

# Charger le module temporaire
spec = importlib.util.spec_from_file_location("temp_module", os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_module.py"))
temp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(temp_module)

# Identifier les fonctions à tester
functions_to_test = [name for name, obj in vars(temp_module).items() 
                     if callable(obj) and not name.startswith('_')]

results = {}

for func_name in functions_to_test:
    try:
        func = getattr(temp_module, func_name)
        
        # Générer des données de test croissantes pour la fonction
        # Note: ceci est simplifié et peut ne pas fonctionner pour toutes les fonctions
        def generate_test_data(n):
            # Par défaut, générer une liste d'entiers
            return list(range(n))
        
        # Fonction de test qui appelle la fonction avec les données
        def test_func(data):
            # Essayer d'appeler avec différents patterns
            try:
                return func(data)
            except:
                try:
                    # Pour les fonctions qui ne prennent pas de liste directement
                    if isinstance(data, list) and len(data) > 0:
                        return func(data[0])
                except:
                    pass
            return None
        
        # Mesurer la complexité
        best_fit, others = big_o.big_o(test_func, generate_test_data, min_n=10, max_n=1000)
        
        # Stocker les résultats
        results[func_name] = {
            "complexity_class": str(best_fit),
            "alternative_fits": {str(cls): str(fit) for cls, fit in others.items()}
        }
    except Exception as e:
        results[func_name] = {"error": str(e)}

# Exporter les résultats
import json
print(json.dumps(results))
                """)
            
            try:
                completed = subprocess.run(
                    [sys.executable, complexity_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=300 * self.load_factors[self.test_level]
                )
                
                if completed.returncode == 0:
                    complexity_results = json.loads(completed.stdout.decode('utf-8'))
                    self.results["performance"]["complexity_analysis"] = complexity_results
                    return complexity_results
                else:
                    logger.error(f"Erreur lors de l'analyse de complexité: {completed.stderr.decode('utf-8')}")
                    return {"error": completed.stderr.decode('utf-8')}
            
            except subprocess.TimeoutExpired:
                logger.error("Timeout lors de l'analyse de complexité")
                return {"error": "Timeout"}
            
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution de l'analyse de complexité: {e}")
                return {"error": str(e)}
            
            finally:
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de complexité: {e}")
            return {"error": str(e)}
    
    def get_execution_command(self):
        """Détermine la commande d'exécution en fonction du langage"""
        if self.file_extension == 'py':
            return [sys.executable, self.file_path]
        elif self.file_extension == 'js':
            return ['node', self.file_path]
        elif self.file_extension == 'java':
            class_name = os.path.splitext(os.path.basename(self.file_path))[0]
            return ['java', class_name]
        elif self.file_extension == 'cpp':
            output_file = os.path.join(tempfile.gettempdir(), "cpp_temp_executable")
            subprocess.run(['g++', self.file_path, '-o', output_file], check=True)
            return [output_file]
        elif self.file_extension == 'c':
            output_file = os.path.join(tempfile.gettempdir(), "c_temp_executable")
            subprocess.run(['gcc', self.file_path, '-o', output_file], check=True)
            return [output_file]
        elif self.file_extension == 'sh' or self.file_extension == 'bash':
            return ['bash', self.file_path]
        else:
            logger.warning(f"Extension de fichier non supportée: {self.file_extension}")
            return None
    
    def run_parallel_test(self, num_parallel=2):
        """Exécute des tests en parallèle pour simuler une charge"""
        if num_parallel <= 1:
            logger.warning("Le nombre de processus parallèles doit être supérieur à 1")
            return {"error": "Nombre de processus invalide"}
        
        command = self.get_execution_command()
        if not command:
            logger.error(f"Langage non supporté pour les tests parallèles: {self.file_extension}")
            return {"error": "Langage non supporté"}
        
        logger.debug(f"Exécution de {num_parallel} processus en parallèle")
        
        processes = []
        start_time = time.time()
        
        for i in range(num_parallel):
            try:
                p = subprocess.Popen(
                    command + self.program_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                processes.append(p)
            except Exception as e:
                logger.error(f"Erreur lors du démarrage du processus parallèle {i}: {e}")
        
        exit_codes = []
        for p in processes:
            try:
                p.wait(timeout=300 * self.load_factors[self.test_level])
                exit_codes.append(p.returncode)
            except subprocess.TimeoutExpired:
                p.terminate()
                exit_codes.append(-1)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        result = {
            "num_processes": num_parallel,
            "total_time": total_time,
            "average_time_per_process": total_time / num_parallel,
            "all_succeeded": all(code == 0 for code in exit_codes),
            "exit_codes": exit_codes
        }
        
        self.results["performance"]["parallel_test"] = result
        return result
    
    def detect_performance_issues(self):
        """Détecte les problèmes de performance potentiels"""
        issues = []
        
        if "execution_time" in self.results["performance"]:
            exec_times = self.results["performance"]["execution_time"]
            if "stdev" in exec_times and "mean" in exec_times:
                if exec_times["stdev"] > exec_times["mean"] * 0.5:
                    issues.append({
                        "severity": "warning",
                        "type": "inconsistent_execution_time",
                        "description": "Les temps d'exécution sont très variables, ce qui peut indiquer un comportement imprévisible ou des dépendances externes."
                    })
        
        if "memory_usage" in self.results["performance"]:
            mem_usage = self.results["performance"]["memory_usage"]
            if "max" in mem_usage:
                if mem_usage["max"] > 1000:  
                    issues.append({
                        "severity": "warning",
                        "type": "high_memory_usage",
                        "description": f"Utilisation élevée de la mémoire détectée: {mem_usage['max']:.2f} Mo"
                    })
        
        if "complexity_analysis" in self.results["performance"]:
            complexity = self.results["performance"]["complexity_analysis"]
            for func_name, analysis in complexity.items():
                if "complexity_class" in analysis:
                    if "O(n^2)" in analysis["complexity_class"] or "O(n^3)" in analysis["complexity_class"] or "O(exp)" in analysis["complexity_class"]:
                        issues.append({
                            "severity": "warning",
                            "type": "high_complexity",
                            "description": f"La fonction '{func_name}' a une complexité algorithmique élevée: {analysis['complexity_class']}"
                        })
        
        self.results["issues"] = issues
        return issues
    
    def generate_visualization(self):
        """Génère des visualisations pour les résultats de performance"""
        charts_dir = os.path.join(self.output_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        if "execution_time" in self.results["performance"] and "raw_data" in self.results["performance"]["execution_time"]:
            times = self.results["performance"]["execution_time"]["raw_data"]
            
            plt.figure(figsize=(10, 6))
            plt.plot(range(1, len(times) + 1), times, 'o-', linewidth=2, markersize=8)
            plt.title('Temps d\'exécution par itération')
            plt.xlabel('Itération')
            plt.ylabel('Temps (secondes)')
            plt.grid(True)
            plt.savefig(os.path.join(charts_dir, 'execution_time.png'))
            plt.close()
        
        if "memory_usage" in self.results["performance"] and "raw_data" in self.results["performance"]["memory_usage"]:
            memory = self.results["performance"]["memory_usage"]["raw_data"]
            
            plt.figure(figsize=(10, 6))
            plt.plot(range(1, len(memory) + 1), memory, 'o-', linewidth=2, markersize=8, color='green')
            plt.title('Utilisation de la mémoire par itération')
            plt.xlabel('Itération')
            plt.ylabel('Mémoire (Mo)')
            plt.grid(True)
            plt.savefig(os.path.join(charts_dir, 'memory_usage.png'))
            plt.close()
        
        if "cpu_usage" in self.results["performance"] and "raw_data" in self.results["performance"]["cpu_usage"]:
            cpu = self.results["performance"]["cpu_usage"]["raw_data"]
            
            plt.figure(figsize=(10, 6))
            plt.plot(range(1, len(cpu) + 1), cpu, 'o-', linewidth=2, markersize=8, color='red')
            plt.title('Utilisation CPU par itération')
            plt.xlabel('Itération')
            plt.ylabel('CPU (%)')
            plt.grid(True)
            plt.savefig(os.path.join(charts_dir, 'cpu_usage.png'))
            plt.close()
        
        if "io_operations" in self.results["performance"] and "raw_data" in self.results["performance"]["io_operations"]:
            io_data = self.results["performance"]["io_operations"]["raw_data"]
            
            read_bytes = [data["read_bytes"] / (1024 * 1024) for data in io_data]  # En Mo
            write_bytes = [data["write_bytes"] / (1024 * 1024) for data in io_data]  # En Mo
            
            plt.figure(figsize=(10, 6))
            plt.bar(range(1, len(io_data) + 1), read_bytes, label='Lecture', color='blue', alpha=0.7)
            plt.bar(range(1, len(io_data) + 1), write_bytes, bottom=read_bytes, label='Écriture', color='orange', alpha=0.7)
            plt.title('Opérations I/O par itération')
            plt.xlabel('Itération')
            plt.ylabel('Données (Mo)')
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(charts_dir, 'io_operations.png'))
            plt.close()
        
        self.results["visualization"] = {
            "charts_directory": charts_dir,
            "available_charts": os.listdir(charts_dir)
        }
    
    def save_results(self):
        """Sauvegarde les résultats dans un fichier JSON"""
        results_file = os.path.join(self.output_dir, "analysis_results.json")
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Résultats sauvegardés dans {results_file}")
        return results_file
    
    def run_analysis(self):
        """Exécute toutes les analyses"""
        try:
            logger.info("Analyse statique du code...")
            self.count_lines_of_code()
            self.analyze_imports()
            self.analyze_functions()
            self.analyze_classes()
            
            logger.info("Mesure du temps d'exécution...")
            self.measure_execution_time()
            
            logger.info("Mesure de l'utilisation mémoire...")
            self.measure_memory_usage()
            
            logger.info("Mesure de l'utilisation CPU...")
            self.measure_cpu_usage()
            
            logger.info("Mesure des opérations I/O...")
            try:
                self.measure_io_operations()
            except Exception as e:
                logger.warning(f"La mesure des opérations I/O a échoué: {e}")
            
            if self.test_level == "heavy":
                logger.info("Exécution de tests en parallèle...")
                self.run_parallel_test(num_parallel=4)
            
            if self.file_extension == 'py':
                logger.info("Analyse de la complexité algorithmique...")
                self.analyze_complexity()
            
            logger.info("Détection des problèmes de performance...")
            self.detect_performance_issues()
            
            logger.info("Génération des visualisations...")
            self.generate_visualization()
            
            logger.info("Sauvegarde des résultats...")
            results_file = self.save_results()
            
            logger.info(f"Analyse terminée avec succès. Résultats sauvegardés dans {results_file}")
            return self.results
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse: {e}")
            logger.error(traceback.format_exc())
            return {"error": str(e), "traceback": traceback.format_exc()}


def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="Analyseur de performance de code")
    parser.add_argument('--file', '-f', required=True, help='Chemin vers le fichier à analyser')
    parser.add_argument('--output', '-o', required=True, help='Répertoire de sortie pour les résultats')
    parser.add_argument('--iterations', '-i', type=int, default=5, help='Nombre d\'itérations pour les tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')
    parser.add_argument('--test-level', '-t', choices=['light', 'medium', 'heavy'], default='medium', help='Niveau de test')
    parser.add_argument('--args', '-a', default='', help='Arguments à passer au programme analysé')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    analyzer = CodeAnalyzer(
        file_path=args.file,
        output_dir=args.output,
        iterations=args.iterations,
        verbose=args.verbose,
        test_level=args.test_level,
        program_args=args.args
    )
    
    analyzer.run_analysis()
    
    sys.exit(0)