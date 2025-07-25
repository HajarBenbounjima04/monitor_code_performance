# 🚀 CodePerformanceMonitor

A multi-dimensional code performance analysis tool built with Bash and Python.  
It supports parallel execution (threads, forks, subshells), detailed logging, and customizable analysis.

---

## 🛠 Features

- Measure execution time over multiple iterations
- Analyze performance with custom Python analyzers
- Support for parallel execution (threading, forking, subshell)
- Logging of results into a user-defined directory
- Option to restore configuration (admin only)
- Modular and extendable architecture

---

## 📂 Structure

monitor_code_performance/
├── monitor_performance.sh # Main script to execute and analyze performance
├── code_analyzer.py # Python module for analyzing execution results
├── parallel_executor.py # Runs commands in parallel (thread/fork/subshell)
├── logs/ # Default directory for logs (can be changed)
├── README.md # You are here :)

---

## 📦 Requirements

- Bash (v4+)
- Python 3
- Required tools: `time`, `jq`, `grep`, `awk`, `sed`, etc.

---

## 🚀 Usage

```bash
./monitor_performance.sh [options] file_path

Available Options

╔═════════════════════════════════════════════════════════════════════╗
║  CodePerformanceMonitor v1.0.0                                      ║
║  Multi-dimensional code performance analyzer                        ║
╚═════════════════════════════════════════════════════════════════════╝

USAGE:
  ./monitor_performance.sh [options] file_path

OPTIONS:
  -h, --help            Display this help message
  -i, --iterations N    Run N iterations (default: 5)
  -L, --load ID         Load a specific analysis by ID
  -f, --fork            Use forked processes for parallel execution
  -t, --thread          Use threads for parallel execution
  -s, --subshell        Use subshells for parallel execution
  -l, --log DIR         Specify a custom log directory
  -r, --restore         Reset configuration (admin only)

ERROR CODES:
  100 : Unknown or unsupported option
  101 : Missing required parameter
  102 : File not found
  103 : Required system command missing
  104 : Failed to install required package
  105 : Analysis ID not found
  106 : --restore option restricted to administrators
  107 : Failed to create log directory
  108 : Failure during execution of a secondary script
  109 : Required system command missing (e.g. java)

📌 Examples

./monitor_performance.sh my_script.py
./monitor_performance.sh -i 10 -f my_script.py
./monitor_performance.sh -t -i 5 my_script.py
./monitor_performance.sh -s my_script.py
```
