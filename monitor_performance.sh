#!/bin/bash

VERSION="1.0.0"
RESULTS_DIR="$HOME/Monitor_Performance"
CONFIG_FILE="$RESULTS_DIR/config.json"
HISTORY_DIR="$RESULTS_DIR/history"
CURRENT_DATE=$(date +"%Y-%m-%d_%H-%M-%S")
TEMP_DIR="/tmp/code_performance_monitor_$CURRENT_DATE"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

check_dependencies() {
    handle_info "Vérification des dépendances..."
    if [[ "$1" == *.java ]]; then
        if ! command -v java &> /dev/null || ! command -v javac &> /dev/null; then
            handle_error 103 "Java n'est pas installé. Veuillez exécuter : sudo apt install default-jdk"
        fi
    fi
    commands=("python3" "pip3" "time" "ps" "grep" "awk" "sed")
    packages=("matplotlib" "numpy" "pandas" "psutil" "memory_profiler" "line_profiler" "py-spy" "big_o")
    for cmd in "${commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
           handle_error 103 "Commande '$cmd' introuvable. Veuillez l'installer." 
        fi
    done
    for pkg in "${packages[@]}"; do
        if ! python3 -c "import $pkg" &> /dev/null; then
            handle_attention "Package Python '$pkg' introuvable. Installation..."
            pip3 install "$pkg" || {
                handle_error 104 "Échec de l'installation de '$pkg'."
            }
        fi
    done
    handle_success "Toutes les dépendances sont satisfaites."
}

init_directories() {
    if [[ -n "$LOG_DIR" ]]; then
        DEFAULT_LOG_DIR="$LOG_DIR"
    elif [[ "$EUID" -eq 0 ]]; then
        DEFAULT_LOG_DIR="/var/log/Monitor_Performance"
    else
        DEFAULT_LOG_DIR="$RESULTS_DIR/logs"
    fi

    LOG_DIR="$DEFAULT_LOG_DIR"
    LOG_FILE="$LOG_DIR/history.log"

    mkdir -p "$LOG_DIR" || handle_error 107 "Impossible de créer le répertoire de log."

    exec > >(tee -a "$LOG_FILE") 2>&1

    if [ ! -d "$RESULTS_DIR" ]; then
        mkdir -p "$RESULTS_DIR"
        mkdir -p "$HISTORY_DIR"
        handle_info "Création du répertoire de résultats à $RESULTS_DIR"

        echo '{
            "default_iterations": 5,
            "test_levels": ["light", "medium", "heavy"],
            "notification_threshold": 20,
            "languages": {
                "py": "python3",
                "js": "node",
                "java": "java",
                "cpp": "g++ -o /tmp/cpptemp && /tmp/cpptemp",
                "c": "gcc -o /tmp/ctemp && /tmp/ctemp"
            }
        }' > "$CONFIG_FILE"
    fi

    mkdir -p "$TEMP_DIR"
}

log_info() {
    local timestamp
    timestamp=$(date "+%Y-%m-%d-%H-%M-%S")
    echo "$timestamp : $USER : INFO : $1" >> "$LOG_FILE"
}

log_success() {
    local timestamp
    timestamp=$(date "+%Y-%m-%d-%H-%M-%S")
    echo "$timestamp : $USER : SUCCÈS : $1" >> "$LOG_FILE"
}

log_error() {
    local timestamp
    timestamp=$(date "+%Y-%m-%d-%H-%M-%S")
    echo "$timestamp : $USER : ERREUR : $1" >> "$LOG_FILE"
}

handle_info() {
    log_info "$1"
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_attention() {
    local timestamp
    timestamp=$(date "+%Y-%m-%d-%H-%M-%S")
    echo "$timestamp : $USER : ATTENTION : $1" >> "$LOG_FILE"
}

handle_attention() {
    log_attention "$1"
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}


handle_success() {
    log_success "$1"
    echo -e "${GREEN}[SUCCÈS]${NC} $1"
}


handle_error() {
    local code="$1"
    local message="$2"

    log_error "[ERREUR $code] $message"

    echo -e "${RED}[ERREUR $code]${NC} $message"
    echo

    display_help
    exit "$code"
}

display_logo() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║  ${BOLD}CodePerformanceMonitor v$VERSION${NC}${CYAN}                     ║"
    echo "║  Analyse multidimensionnelle des performances de code ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

display_help() {
    echo -e "${BOLD}UTILISATION:${NC}"
    echo "  $0 [options] chemin_fichier"
    echo
    echo -e "${BOLD}OPTIONS:${NC}"
    echo "  -h, --help            Affiche cette aide"
    echo "  -i, --iterations N    Exécute N itérations (défaut: 5)"
    echo "  -L, --load ID         Charge l'analyse ID"
    echo "  -f, --fork            Utilise des processus fork pour l'exécution parallèle"
    echo "  -t, --thread          Utilise des threads pour l'exécution parallèle"
    echo "  -s, --subshell        Utilise des sous-shells pour l'exécution parallèle"
    echo "  -l, --log DIR         Spécifie le répertoire de log"
    echo "  -r, --restore         Réinitialise la configuration (admin uniquement)"

    echo
    echo -e "${BOLD}CODES D'ERREUR:${NC}"
    echo "  100 : Option inconnue ou non supportée"
    echo "  101 : Paramètre obligatoire manquant"
    echo "  102 : Le fichier spécifié n'existe pas"
    echo "  103 : Commande système requise introuvable"
    echo "  104 : Échec de l’installation d’un package requis"
    echo "  105 : ID d’analyse introuvable"
    echo "  106 : Option --restore réservée aux administrateurs"
    echo "  107 : Échec lors de la création du répertoire de log"
    echo "  108 : Échec d'exécution d'un script secondaire"
    echo "  109 : Commande système requise introuvable (ex. java)"



    echo
    echo -e "${BOLD}EXEMPLES:${NC}"
    echo "  $0 mon_script.py"
    echo "  $0 -i 10 -f mon_script.py"
    echo "  $0 -t -i 5 mon_script.py"
    echo "  $0 -s mon_script.py"
    echo
}

analyze_code_file() {
    local file_path="$1"
    local file_extension="${file_path##*.}"
    local filename=$(basename "$file_path")
    local analysis_id=$(date +"%Y%m%d%H%M%S")_$(echo "$filename" | md5sum | cut -c1-6)
    handle_info "Analyse du fichier: $file_path (ID: $analysis_id)"
    local analysis_dir="$HISTORY_DIR/$analysis_id"
    mkdir -p "$analysis_dir"
    cp "$file_path" "$analysis_dir/original_$filename"
    
    local execution_type="sequential"
    if [ "$USE_FORK" = true ]; then
        execution_type="fork"
    elif [ "$USE_THREAD" = true ]; then
        execution_type="thread"
    elif [ "$USE_SUBSHELL" = true ]; then
        execution_type="subshell"
    fi

    if [ "$execution_type" != "sequential" ]; then
    handle_info " Mode d'exécution: $execution_type"
    python3 "$(dirname "$0")/parallel_executor.py" \
        --file "$file_path" \
        --output "$analysis_dir" \
        --iterations "$ITERATIONS" \
        --execution-type "$execution_type" \
        ${VERBOSE_FLAG:+--verbose} \
        ${TEST_LEVEL:+--test-level "$TEST_LEVEL"} \
        ${PROGRAM_ARGS:+--args "$PROGRAM_ARGS"}
    ret_code=$?
    else
        python3 "$(dirname "$0")/code_analyzer.py" \
            --file "$file_path" \
            --output "$analysis_dir" \
            --iterations "$ITERATIONS" \
            ${VERBOSE_FLAG:+--verbose} \
            ${TEST_LEVEL:+--test-level "$TEST_LEVEL"} \
            ${PROGRAM_ARGS:+--args "$PROGRAM_ARGS"}
        ret_code=$?
    fi

    if [ "$ret_code" -ne 0 ]; then
        handle_error 108 "Le script d'analyse a échoué avec le code $ret_code."
    fi



    handle_success "Analyse terminée avec l'ID: $analysis_id"
    display_report "$analysis_dir"
    if [ -n "$COMPARE_ID" ]; then
        compare_analyses "$COMPARE_ID" "$analysis_id"
    fi
    return 0
}

display_report() {
    local report_dir="$1"
    handle_info "=== RAPPORT D'ANALYSE ==="
    python3 "$(dirname "$0")/report_generator.py" -r "$report_dir/analysis_results.json" -o "$report_dir" ${VERBOSE_FLAG:+--verbose}
}


load_analysis() {
    local id="$1"
    local dir="$HISTORY_DIR/$id"
    if [ ! -d "$dir" ]; then
        handle_error 105 "L'analyse avec l'ID $id n'existe pas."
    fi
    handle_info "Chargement de l'analyse: $id"
    display_report "$dir"
}

cleanup() {
   handle_info "Nettoyage des fichiers temporaires..."
    rm -rf "$TEMP_DIR"
}



main() {
    ITERATIONS=5
    VERBOSE_FLAG=""
    COMPARE_ID=""
    LOAD_ID=""
    PARALLEL=1
    TEST_LEVEL="medium"
    PROGRAM_ARGS=""
    USE_FORK=false
    USE_THREAD=false
    USE_SUBSHELL=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                display_logo
                display_help
                exit 0
                ;;
            -i|--iterations)
                ITERATIONS="$2"
                shift 2
                ;;
            -L|--load)
                LOAD_ID="$2"
                shift 2
                ;;
            -f|--fork)
                USE_FORK=true
                USE_THREAD=false
                USE_SUBSHELL=false
                shift
                ;;
            -t|--thread)
                USE_THREAD=true
                USE_FORK=false
                USE_SUBSHELL=false
                shift
                ;;
            -s|--subshell)
                USE_SUBSHELL=true
                USE_FORK=false
                USE_THREAD=false
                shift
                ;;
            -r|--restore)
                if [ "$(id -u)" -ne 0 ]; then
                    handle_error 106 "Option --restore requiert les privilèges administrateur."
                fi
                RESTORE=true
                shift
                ;;
            -l|--log)
                LOG_DIR="$2"
                shift 2
                ;;
            -*)
                handle_error 100 "Option inconnue: $1"
                ;;
            *)
                FILE_PATH="$1"
                shift
                ;;
        esac
    done
    
    display_logo
    init_directories
    check_dependencies

    if [ "$RESTORE" = true ]; then
        handle_info "Réinitialisation de la configuration..."
        rm -rf "$RESULTS_DIR" "$TEMP_DIR" "$HISTORY_DIR" "$CONFIG_FILE"
        handle_success "Configuration réinitialisée avec succès."
        exit 0
    fi
    
    if [ -n "$LOAD_ID" ]; then
        load_analysis "$LOAD_ID"
        exit $?
    fi
    

    if [[ -z "$FILE_PATH" || "$FILE_PATH" == -* ]]; then
        handle_error 101 "Fichier de code non spécifié."
    fi

    if [[ ! -f "$FILE_PATH" ]]; then
        handle_error 102 "Le fichier '$FILE_PATH' n'existe pas : $1"
    fi

    
    trap cleanup EXIT
    analyze_code_file "$FILE_PATH"

    handle_info "Consultez $LOG_FILE pour les détails."
}

main "$@"