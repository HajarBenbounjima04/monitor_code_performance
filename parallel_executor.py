"""
Gestionnaire d'exécution parallèle pour le monitoring de performance
Supporte fork, thread et subshell 
"""

import os
import sys
import json
import time
import argparse
import threading
import multiprocessing
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import psutil
import statistics
from typing import List, Dict, Any, Tuple
import signal
import tempfile
import shutil

class PerformanceCollector:
    """Collecteur de métriques de performance"""
    
    def __init__(self):
        self.metrics = {
            'execution_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'process_metrics': [],
            'parallel_metrics': {}
        }
    
    def collect_system_snapshot(self) -> Dict[str, Any]:
        """Collecte un instantané des métriques système"""
        try:
            return {
                'timestamp': time.time(),
                'cpu_percent': psutil.cpu_percent(interval=None),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_available': psutil.virtual_memory().available,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
        except Exception as e:
            return {'error': str(e)}

class CodeCompiler:
    """Gestionnaire de compilation pour différents langages"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.temp_dir = tempfile.mkdtemp(prefix='parallel_exec_')
        
    def compile_if_needed(self, file_path: str) -> Tuple[List[str], str]:
        """Compile le fichier si nécessaire et retourne la commande d'exécution"""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.java':
            return self._compile_java(file_path)
        elif ext == '.cpp':
            return self._compile_cpp(file_path)
        elif ext == '.c':
            return self._compile_c(file_path)
        elif ext == '.go':
            return self._compile_go(file_path)
        else:
            return self._get_interpreter_command(file_path, ext)
    
    def _compile_java(self, file_path: str) -> Tuple[List[str], str]:
        """Compile un fichier Java"""
        try:
            class_name = os.path.splitext(os.path.basename(file_path))[0]
            
            compile_result = subprocess.run(
                ['javac', '-d', self.temp_dir, file_path],
                capture_output=True, text=True, timeout=30
            )
            
            if compile_result.returncode != 0:
                print(f"Java compilation error: {compile_result.stderr}", file=sys.stderr)
                raise Exception(f"Erreur de compilation Java: {compile_result.stderr}")
            class_file = os.path.join(self.temp_dir, f"{class_name}.class")
            if not os.path.exists(class_file):
                for root, dirs, files in os.walk(self.temp_dir):
                    if f"{class_name}.class" in files:
                        relative_path = os.path.relpath(root, self.temp_dir)
                        if relative_path != '.':
                            full_class_name = f"{relative_path.replace(os.sep, '.')}.{class_name}"
                        else:
                            full_class_name = class_name
                        return (['java', '-cp', self.temp_dir, full_class_name], "java_compiled")
                
                raise Exception(f"Classe compilée {class_name}.class non trouvée")
            
            return (['java', '-cp', self.temp_dir, class_name], "java_compiled")
            
        except Exception as e:
            print(f"Java compilation error: {e}", file=sys.stderr)
            return (['echo', f'Erreur: {e}'], "java_error")
            return (['java', '-cp', self.temp_dir, class_name], "java_compiled")
            
        except Exception as e:
            if self.verbose:
                print(f"Erreur compilation Java: {e}")
            return (['echo', f'Erreur: {e}'], "java_error")
    
    def _compile_cpp(self, file_path: str) -> Tuple[List[str], str]:
        """Compile un fichier C++"""
        try:
            output_file = os.path.join(self.temp_dir, 'cpp_executable')
            compile_result = subprocess.run(
                ['g++', '-O2', '-o', output_file, file_path],
                capture_output=True, text=True, timeout=30
            )
            
            if compile_result.returncode != 0:
                raise Exception(f"Erreur de compilation C++: {compile_result.stderr}")
            
            return ([output_file], "cpp_compiled")
            
        except Exception as e:
            if self.verbose:
                print(f"Erreur compilation C++: {e}")
            return (['echo', f'Erreur: {e}'], "cpp_error")
    
    def _compile_c(self, file_path: str) -> Tuple[List[str], str]:
        """Compile un fichier C"""
        try:
            output_file = os.path.join(self.temp_dir, 'c_executable')
            compile_result = subprocess.run(
                ['gcc', '-O2', '-o', output_file, file_path],
                capture_output=True, text=True, timeout=30
            )
            
            if compile_result.returncode != 0:
                raise Exception(f"Erreur de compilation C: {compile_result.stderr}")
            
            return ([output_file], "c_compiled")
            
        except Exception as e:
            if self.verbose:
                print(f"Erreur compilation C: {e}")
            return (['echo', f'Erreur: {e}'], "c_error")
    
    def _compile_go(self, file_path: str) -> Tuple[List[str], str]:
        """Compile un fichier Go"""
        try:
            output_file = os.path.join(self.temp_dir, 'go_executable')
            compile_result = subprocess.run(
                ['go', 'build', '-o', output_file, file_path],
                capture_output=True, text=True, timeout=30
            )
            
            if compile_result.returncode != 0:
                raise Exception(f"Erreur de compilation Go: {compile_result.stderr}")
            
            return ([output_file], "go_compiled")
            
        except Exception as e:
            if self.verbose:
                print(f"Erreur compilation Go: {e}")
            return (['echo', f'Erreur: {e}'], "go_error")
    
    def _get_interpreter_command(self, file_path: str, ext: str) -> Tuple[List[str], str]:
        """Retourne la commande pour les langages interprétés"""
        command_map = {
            '.py': (['python3', file_path], "python"),
            '.js': (['node', file_path], "javascript"),
            '.sh': (['bash', file_path], "bash"),
            '.rb': (['ruby', file_path], "ruby"),
            '.php': (['php', file_path], "php"),
            '.pl': (['perl', file_path], "perl")
        }
        
        return command_map.get(ext, (['python3', file_path], "unknown"))
    
    def cleanup(self):
        """Nettoie les fichiers temporaires"""
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

class ForkExecutor:
    """Gestionnaire d'exécution avec fork() - VERSION OPTIMISÉE"""
    
    def __init__(self, collector: PerformanceCollector):
        self.collector = collector
        self.child_pids = []
    
    def execute_with_fork(self, command: List[str], iterations: int) -> Dict[str, Any]:
        """Exécute le code en utilisant fork() - optimisé"""
        results = []
        
        for i in range(iterations):
            start_time = time.time()
            
            pid = os.fork()
            if pid == 0: 
                try:
                    result = subprocess.run(
                        command, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        timeout=10,
                        text=True
                    )
                    if result.returncode != 0 and result.stderr:
                        print(f"Fork error: {result.stderr}", file=sys.stderr)   

                    os._exit(result.returncode)
                except subprocess.TimeoutExpired:
                    print("Fork timeout", file=sys.stderr)
                    os._exit(124)  
                except Exception as e:
                    print(f"Fork exception: {e}", file=sys.stderr)
                    os._exit(1)
            else: 
                self.child_pids.append(pid)
                
                try:
                    _, status = os.waitpid(pid, 0)
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    results.append({
                        'iteration': i + 1,
                        'execution_time': execution_time,
                        'child_pid': pid,
                        'exit_status': os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1,
                        'success': os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
                    })
                    
                except OSError as e:
                    end_time = time.time()
                    results.append({
                        'iteration': i + 1,
                        'execution_time': end_time - start_time,
                        'child_pid': pid,
                        'exit_status': -1,
                        'success': False,
                        'error': str(e)
                    })
        
        return self._analyze_fork_results(results)
    
    def _analyze_fork_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyse les résultats de l'exécution fork"""
        successful_results = [r for r in results if r.get('success', False)]
        execution_times = [r['execution_time'] for r in successful_results]
        
        if not execution_times:
            execution_times = [0.0]
        
        return {
            'execution_type': 'fork',
            'total_iterations': len(results),
            'successful_iterations': len(successful_results),
            'failed_iterations': len(results) - len(successful_results),
            'execution_times': {
                'values': execution_times,
                'mean': statistics.mean(execution_times),
                'median': statistics.median(execution_times),
                'stdev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                'min': min(execution_times),
                'max': max(execution_times)
            },
            'process_metrics': results,
            'parallel_efficiency': self._calculate_fork_efficiency(results)
        }
    
    def _calculate_fork_efficiency(self, results: List[Dict]) -> Dict[str, Any]:
        """Calcule l'efficacité de l'exécution fork"""
        successful_runs = [r for r in results if r.get('success', False)]
        failed_runs = [r for r in results if not r.get('success', False)]
        
        return {
            'success_rate': len(successful_runs) / len(results) if results else 0,
            'failure_rate': len(failed_runs) / len(results) if results else 0,
            'average_processes': len(results),
            'process_creation_efficiency': len(successful_runs) / len(results) if results else 0
        }

class ThreadExecutor:
    
    """Gestionnaire d'exécution avec threads - VERSION OPTIMISÉE CORRIGÉE"""
    
    def __init__(self, collector: PerformanceCollector):
        self.collector = collector
    
    def execute_with_threads(self, command: List[str], iterations: int) -> Dict[str, Any]:
        """Exécute le code en utilisant des threads - VERSION CORRIGÉE"""
        results = []
        results_lock = threading.Lock()
        
        def run_single_iteration(iteration_num):
            start_time = time.time()
            thread_id = threading.get_ident()
            
            try:
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    start_new_session=True  
                )
                end_time = time.time()
                
                execution_result = {
                    'iteration': iteration_num,
                    'thread_id': thread_id,
                    'execution_time': end_time - start_time,
                    'return_code': result.returncode,
                    'success': result.returncode == 0
                }
                
                if result.returncode != 0 and result.stderr:
                    execution_result['stderr'] = result.stderr[:200] 
                
                with results_lock:
                    results.append(execution_result)
                    
            except subprocess.TimeoutExpired:
                end_time = time.time()
                with results_lock:
                    results.append({
                        'iteration': iteration_num,
                        'thread_id': thread_id,
                        'execution_time': end_time - start_time,
                        'return_code': 124,
                        'success': False,
                        'error': 'timeout'
                    })
            except Exception as e:
                end_time = time.time()
                with results_lock:
                    results.append({
                        'iteration': iteration_num,
                        'thread_id': thread_id,
                        'execution_time': end_time - start_time,
                        'return_code': -1,
                        'success': False,
                        'error': str(e)
                    })
        
        optimal_workers = min(iterations, multiprocessing.cpu_count(), 8) 
        
        start_execution = time.time()
        
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            futures = []
            for i in range(iterations):
                future = executor.submit(run_single_iteration, i + 1)
                futures.append(future)
            
            completed = 0
            for future in futures:
                try:
                    future.result(timeout=12)  
                    completed += 1
                except Exception as e:
                    print(f"Thread task failed: {e}", file=sys.stderr)
        
        end_execution = time.time()
        
        if len(results) != iterations:
            print(f"Warning: Expected {iterations} results, got {len(results)}", file=sys.stderr)
        
        return self._analyze_thread_results(results, end_execution - start_execution)
    
    def _analyze_thread_results(self, results: List[Dict], total_time: float) -> Dict[str, Any]:
        """Analyse les résultats de l'exécution thread - VERSION AMÉLIORÉE"""
        if not results:
            return {
                'execution_type': 'thread',
                'total_iterations': 0,
                'successful_iterations': 0,
                'failed_iterations': 0,
                'execution_times': {
                    'values': [0.0],
                    'mean': 0.0,
                    'median': 0.0,
                    'stdev': 0.0,
                    'min': 0.0,
                    'max': 0.0
                },
                'thread_metrics': [],
                'concurrency_analysis': {
                    'total_threads': 0,
                    'success_rate': 0.0,
                    'average_execution_time': 0.0,
                    'thread_efficiency': 0.0,
                    'actual_parallelism': 0.0
                }
            }
        
        successful_results = [r for r in results if r.get('success', False)]
        execution_times = [r['execution_time'] for r in successful_results]
        
        if not execution_times:
            execution_times = [0.0]
        
        unique_threads = len(set(r['thread_id'] for r in results))
        
        if successful_results:
            sequential_time = sum(execution_times)
            parallel_time = total_time
            actual_parallelism = sequential_time / parallel_time if parallel_time > 0 else 1.0
        else:
            actual_parallelism = 0.0
        
        return {
            'execution_type': 'thread',
            'total_iterations': len(results),
            'successful_iterations': len(successful_results),
            'failed_iterations': len(results) - len(successful_results),
            'unique_threads_used': unique_threads,
            'execution_times': {
                'values': execution_times,
                'mean': statistics.mean(execution_times),
                'median': statistics.median(execution_times),
                'stdev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                'min': min(execution_times),
                'max': max(execution_times)
            },
            'thread_metrics': results,
            'concurrency_analysis': {
                'total_threads': unique_threads,
                'success_rate': len(successful_results) / len(results) if results else 0,
                'average_execution_time': statistics.mean(execution_times) if execution_times else 0,
                'thread_efficiency': self._calculate_thread_efficiency(results, total_time),
                'actual_parallelism': actual_parallelism,
                'parallel_overhead': total_time - (max(execution_times) if execution_times else 0)
            }
        }
    
    def _calculate_thread_efficiency(self, results: List[Dict], total_time: float) -> float:
        """Calcule l'efficacité des threads - VERSION CORRIGÉE"""
        successful_results = [r for r in results if r.get('success', False)]
        if not successful_results or total_time <= 0:
            return 0.0
        
        individual_times = [r['execution_time'] for r in successful_results]
        sequential_time = sum(individual_times)
        
        threads_used = len(set(r['thread_id'] for r in results))
        theoretical_parallel_time = total_time * threads_used
        
        efficiency = sequential_time / theoretical_parallel_time if theoretical_parallel_time > 0 else 0.0
        
        return min(efficiency, 1.0)
class SubshellExecutor:
    """Gestionnaire d'exécution avec subshells - VERSION OPTIMISÉE"""
    
    def __init__(self, collector: PerformanceCollector):
        self.collector = collector
    
    def execute_with_subshells(self, command: List[str], iterations: int) -> Dict[str, Any]:
        """Exécute le code en utilisant des sous-shells"""
        results = []
        
        for i in range(iterations):
            start_time = time.time()
            
            if len(command) == 1:
                subshell_command = f"({command[0]})"
            else:
                subshell_command = f"({' '.join(command)})"
            
            try:
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    timeout=10,
                    shell=False, 
                )
                end_time = time.time()
                results.append({
                    'iteration': i + 1,
                    'execution_time': end_time - start_time,
                    'return_code': result.returncode,
                    'success': result.returncode == 0
                })
                if result.returncode != 0:
                    print(f"Subshell error (iter {i+1}): {result.stderr}", file=sys.stderr)
                
            except subprocess.TimeoutExpired:
                results.append({
                    'iteration': i + 1,
                    'execution_time': 10.0,
                    'return_code': -1,
                    'success': False,
                    'error': 'timeout'
                })
            except Exception as e:
                results.append({
                    'iteration': i + 1,
                    'execution_time': 0.0,
                    'return_code': -1,
                    'success': False,
                    'error': str(e)
                })
        
        return self._analyze_subshell_results(results)
    
    def _analyze_subshell_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyse les résultats de l'exécution subshell"""
        successful_results = [r for r in results if r.get('success', False)]
        execution_times = [r['execution_time'] for r in successful_results]
        
        if not execution_times:
            execution_times = [0.0]
        
        return {
            'execution_type': 'subshell',
            'total_iterations': len(results),
            'successful_iterations': len(successful_results),
            'failed_iterations': len(results) - len(successful_results),
            'execution_times': {
                'values': execution_times,
                'mean': statistics.mean(execution_times),
                'median': statistics.median(execution_times),
                'stdev': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                'min': min(execution_times),
                'max': max(execution_times)
            },
            'subshell_metrics': results,
            'isolation_analysis': self._analyze_subshell_isolation(results)
        }
    
    def _analyze_subshell_isolation(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyse l'isolation des subshells"""
        successful_results = [r for r in results if r.get('success', False)]
        return {
            'success_rate': len(successful_results) / len(results) if results else 0,
            'average_execution_time': statistics.mean([r['execution_time'] for r in successful_results]) if successful_results else 0,
            'isolation_efficiency': len(successful_results) / len(results) if results else 0
        }

class ParallelExecutor:
    """Gestionnaire principal d'exécution parallèle - VERSION CORRIGÉE"""
    
    def __init__(self, file_path: str, output_dir: str, verbose: bool = False):
        self.file_path = file_path
        self.output_dir = output_dir
        self.verbose = verbose
        self.collector = PerformanceCollector()
        self.compiler = CodeCompiler(verbose)
        
        self.command, self.compile_info = self.compiler.compile_if_needed(file_path)
    def _test_command(self, command: List[str]) -> bool:
        """Teste si la commande peut s'exécuter - VERSION AMÉLIORÉE"""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                timeout=2, 
                text=True
            )
            
            return True
            
        except subprocess.TimeoutExpired:
            return True
        except (FileNotFoundError, OSError) as e:
            print(f"Command test failed: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Command test exception: {e}", file=sys.stderr)
            return True 
    def execute(self, execution_type: str, iterations: int, program_args: str = None) -> Dict[str, Any]:
        """Exécute le code avec le type d'exécution spécifié - VERSION OPTIMISÉE"""
        if self.verbose:
            print(f"Exécution de {self.file_path} avec {execution_type} ({iterations} itérations)")
            print(f"Commande: {' '.join(self.command)}")
            print(f"Type de compilation: {self.compile_info}")
        
        command = self.command.copy()
        if program_args:
            command.extend(program_args.split())
        
        if not self._test_command_optimized(command, execution_type):
            raise Exception(f"Impossible d'exécuter la commande: {' '.join(command)}")
        
        start_total_time = time.time()
        
        try:
            if execution_type == 'fork':
                executor = ForkExecutor(self.collector)
                results = executor.execute_with_fork(command, iterations)
            elif execution_type == 'thread':
                if iterations > 1:
                    test_executor = ThreadExecutor(self.collector)
                    try:
                        test_executor.execute_with_threads(command, 1)
                    except:
                        pass  
                
                executor = ThreadExecutor(self.collector)
                results = executor.execute_with_threads(command, iterations)
            elif execution_type == 'subshell':
                executor = SubshellExecutor(self.collector)
                results = executor.execute_with_subshells(command, iterations)
            else:
                raise ValueError(f"Type d'exécution non supporté: {execution_type}")
            
        finally:
            end_total_time = time.time()
        
        results['total_execution_time'] = end_total_time - start_total_time
        results['file_path'] = self.file_path
        results['command'] = command
        results['compile_info'] = self.compile_info
        results['timestamp'] = time.time()
        results['system_info'] = self._get_system_info()
        
        self._save_results(results)
        
        return results

    def _test_command_optimized(self, command: List[str], execution_type: str) -> bool:
        """Teste si la commande peut s'exécuter - VERSION OPTIMISÉE"""
        try:
            timeout = 1 if execution_type == 'thread' else 2
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                timeout=timeout,
                text=True,
                start_new_session=True  
            )
            
            return True  
            
        except subprocess.TimeoutExpired:
            return True
        except (FileNotFoundError, OSError) as e:
            print(f"Command test failed: {e}", file=sys.stderr)
            return False
        except Exception as e:
            if self.verbose:
                print(f"Command test exception: {e}", file=sys.stderr)
            return True  
      
    def _test_command(self, command: List[str]) -> bool:
        """Teste si la commande peut s'exécuter"""
        try:
            result = subprocess.run(
                command, 
                capture_output=True, 
                timeout=5,
                text=True
            )
            return True 
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
        except Exception:
            return True  
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Collecte les informations système"""
        return {
            'cpu_count': multiprocessing.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
            'platform': sys.platform
        }
    
    def _save_results(self, results: Dict[str, Any]) -> None:
        """Sauvegarde les résultats dans un fichier JSON"""
        timestamp = int(time.time())
        output_file = os.path.join(self.output_dir, f'parallel_analysis_{timestamp}.json')
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            if self.verbose:
                print(f"Résultats sauvegardés dans: {output_file}")
                
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {e}", file=sys.stderr)
    
    def generate_comparison_report(self, results: Dict[str, Any]) -> str:
        """Génère un rapport de comparaison des performances"""
        report = []
        report.append("# Rapport d'Analyse Parallèle\n")
        
        exec_type = results.get('execution_type', 'unknown')
        report.append(f"## Type d'exécution: {exec_type.upper()}\n")
        
        report.append(f"**Fichier analysé:** {results.get('file_path', 'N/A')}")
        report.append(f"**Type de compilation:** {results.get('compile_info', 'N/A')}")
        report.append(f"**Commande:** `{' '.join(results.get('command', []))}`")
        report.append(f"**Itérations totales:** {results.get('total_iterations', 0)}")
        report.append(f"**Itérations réussies:** {results.get('successful_iterations', 0)}")
        report.append(f"**Temps total d'exécution:** {results.get('total_execution_time', 0):.4f}s\n")
        
        exec_times = results.get('execution_times', {})
        report.append("### Statistiques de Performance")
        report.append(f"- **Temps moyen:** {exec_times.get('mean', 0):.4f}s")
        report.append(f"- **Médiane:** {exec_times.get('median', 0):.4f}s")
        report.append(f"- **Écart-type:** {exec_times.get('stdev', 0):.4f}s")
        report.append(f"- **Minimum:** {exec_times.get('min', 0):.4f}s")
        report.append(f"- **Maximum:** {exec_times.get('max', 0):.4f}s\n")
        
        if exec_type == 'fork':
            self._add_fork_metrics_to_report(report, results)
        elif exec_type == 'thread':
            self._add_thread_metrics_to_report(report, results)
        elif exec_type == 'subshell':
            self._add_subshell_metrics_to_report(report, results)
        
        report.append("### Recommandations")
        recommendations = self._generate_recommendations(results)
        for rec in recommendations:
            report.append(f"- {rec}")
        
        return '\n'.join(report)
    
    def _add_fork_metrics_to_report(self, report: List[str], results: Dict[str, Any]) -> None:
        """Ajoute les métriques fork au rapport"""
        parallel_eff = results.get('parallel_efficiency', {})
        
        report.append("### Métriques Fork")
        report.append(f"- **Taux de succès:** {parallel_eff.get('success_rate', 0):.2%}")
        report.append(f"- **Taux d'échec:** {parallel_eff.get('failure_rate', 0):.2%}")
        report.append(f"- **Efficacité processus:** {parallel_eff.get('process_creation_efficiency', 0):.2%}")
        report.append("")
    
    def _add_thread_metrics_to_report(self, report: List[str], results: Dict[str, Any]) -> None:
        """Ajoute les métriques thread au rapport"""
        concurrency = results.get('concurrency_analysis', {})
        
        report.append("### Métriques Thread")
        report.append(f"- **Threads utilisés:** {results.get('unique_threads_used', 0)}")
        report.append(f"- **Taux de succès:** {concurrency.get('success_rate', 0):.2%}")
        report.append(f"- **Efficacité threads:** {concurrency.get('thread_efficiency', 0):.2%}")
        report.append("")
    
    def _add_subshell_metrics_to_report(self, report: List[str], results: Dict[str, Any]) -> None:
        """Ajoute les métriques subshell au rapport"""
        isolation = results.get('isolation_analysis', {})
        
        report.append("### Métriques Subshell")
        report.append(f"- **Taux de succès:** {isolation.get('success_rate', 0):.2%}")
        report.append(f"- **Efficacité isolation:** {isolation.get('isolation_efficiency', 0):.2%}")
        report.append("")
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Génère des recommandations basées sur les résultats"""
        recommendations = []
        exec_type = results.get('execution_type', '')
        exec_times = results.get('execution_times', {})
        success_rate = results.get('successful_iterations', 0) / max(results.get('total_iterations', 1), 1)
        
        mean_time = exec_times.get('mean', 0)
        stdev_time = exec_times.get('stdev', 0)
        
        if success_rate < 0.9:
            recommendations.append("Taux d'échec élevé - vérifiez la stabilité du code ou les dépendances")
        
        if stdev_time > mean_time * 0.3:
            recommendations.append("Forte variabilité détectée - considérez plus d'itérations pour la stabilité")
        
        if mean_time < 0.001:
            recommendations.append("Temps d'exécution très faible - augmentez la charge de travail pour des mesures plus précises")
        
        if exec_type == 'fork':
            if mean_time < 0.01:
                recommendations.append("Fork: Temps d'exécution très court - le coût de création de processus peut dominer")
            parallel_eff = results.get('parallel_efficiency', {})
            if parallel_eff.get('success_rate', 1) < 0.9:
                recommendations.append("Fork: Taux d'échec élevé - vérifiez la stabilité du code")
        
        elif exec_type == 'thread':
            concurrency = results.get('concurrency_analysis', {})
            if concurrency.get('thread_efficiency', 0) < 0.5:
                recommendations.append("Thread: Faible efficacité - possible contention ou code non thread-safe")
            if results.get('unique_threads_used', 0) < min(results.get('total_iterations', 1), multiprocessing.cpu_count()):
                recommendations.append("Thread: Sous-utilisation des threads disponibles")
        
        elif exec_type == 'subshell':
            isolation = results.get('isolation_analysis', {})
            if isolation.get('isolation_efficiency', 0) < 0.8:
                recommendations.append("Subshell: Efficacité d'isolation faible - considérez l'exécution directe")
        
        if mean_time > 1.0:
            recommendations.append("Temps d'exécution élevé - considérez l'optimisation du code")
        elif mean_time < 0.001:
            recommendations.append("Temps d'exécution très faible - les mesures peuvent être imprécises")
        
        if not recommendations:
            recommendations.append("Performance acceptable avec la méthode d'exécution choisie")
        
        return recommendations
    
    def cleanup(self):
        """Nettoie les ressources"""
        self.compiler.cleanup()

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Exécuteur parallèle pour l\'analyse de performance')
    parser.add_argument('--file', required=True, help='Fichier à analyser')
    parser.add_argument('--output', required=True, help='Répertoire de sortie')
    parser.add_argument('--execution-type', required=True, choices=['fork', 'thread', 'subshell'],
                        help='Type d\'exécution parallèle')
    parser.add_argument('--iterations', type=int, default=5, help='Nombre d\'itérations')
    parser.add_argument('--args', help='Arguments à passer au programme')
    parser.add_argument('--verbose', action='store_true', help='Mode verbeux')
    parser.add_argument('--test-level', choices=['light', 'medium', 'heavy'], default='medium',
                        help='Niveau de test')
    
    args = parser.parse_args()
    
    if not os.path.isfile(args.file):
        print(f"Erreur: Le fichier {args.file} n'existe pas", file=sys.stderr)
        sys.exit(1)
    
    os.makedirs(args.output, exist_ok=True)
    
    iterations_map = {'light': 3, 'medium': 5, 'heavy': 10}
    iterations = iterations_map.get(args.test_level, args.iterations)
    
    executor = ParallelExecutor(args.file, args.output, args.verbose)
    
    try:
        results = executor.execute(args.execution_type, iterations, args.args)
        
        report = executor.generate_comparison_report(results)
        
        timestamp = int(time.time())
        report_file = os.path.join(args.output, f'parallel_execution_report_{timestamp}.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        if args.verbose:
            print(f"Rapport généré: {report_file}")
            print("\n" + "="*60)
            print("RÉSUMÉ D'EXÉCUTION")
            print("="*60)
            exec_times = results.get('execution_times', {})
            print(f"Type d'exécution: {results.get('execution_type', 'unknown').upper()}")
            print(f"Fichier: {results.get('file_path', 'N/A')}")
            print(f"Type de compilation: {results.get('compile_info', 'N/A')}")
            print(f"Itérations: {results.get('total_iterations', 0)} (réussies: {results.get('successful_iterations', 0)})")
            print(f"Temps moyen: {exec_times.get('mean', 0):.6f}s")
            print(f"Écart-type: {exec_times.get('stdev', 0):.6f}s")
            print(f"Min/Max: {exec_times.get('min', 0):.6f}s / {exec_times.get('max', 0):.6f}s")
            print(f"Temps total: {results.get('total_execution_time', 0):.4f}s")
            
            recommendations = executor._generate_recommendations(results)
            if recommendations:
                print(f"\nRecommandations principales:")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"  {i}. {rec}")
        else:
            exec_times = results.get('execution_times', {})
            success_rate = results.get('successful_iterations', 0) / max(results.get('total_iterations', 1), 1)
            print(f"{results.get('execution_type', 'unknown').upper()}: {exec_times.get('mean', 0):.6f}s±{exec_times.get('stdev', 0):.6f}s (success: {success_rate:.1%})")
        
    except KeyboardInterrupt:
        print("\nInterruption par l'utilisateur", file=sys.stderr)
        executor.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"Erreur lors de l'exécution: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        executor.cleanup()
        sys.exit(1)
    finally:
        executor.cleanup()

if __name__ == '__main__':
    main()