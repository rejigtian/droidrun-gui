#!/bin/bash
# Helper script to run AndroidWorld benchmarks with DroidRun

# Check if ANDROID_WORLD_PATH is set
if [ -z "$ANDROID_WORLD_PATH" ]; then
    echo "Error: ANDROID_WORLD_PATH environment variable is not set."
    echo "Please set it to the path of your AndroidWorld installation."
    echo "Example: export ANDROID_WORLD_PATH=/path/to/android_world"
    exit 1
fi

# Default values
TASK_IDS=""
TASK_NAMES=""
LLM_PROVIDER="OpenAI"
LLM_MODEL="gpt-4o-mini"
PERFORM_SETUP=false
MAX_STEPS=50
COMBINATIONS=1
RESULTS_DIR="eval_results"
LIST_TASKS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --task-ids)
            shift
            TASK_IDS="$1"
            ;;
        --task-names)
            shift
            TASK_NAMES="$1"
            ;;
        --llm-provider)
            shift
            LLM_PROVIDER="$1"
            ;;
        --llm-model)
            shift
            LLM_MODEL="$1"
            ;;
        --setup)
            PERFORM_SETUP=true
            ;;
        --max-steps)
            shift
            MAX_STEPS="$1"
            ;;
        --combinations)
            shift
            COMBINATIONS="$1"
            ;;
        --results-dir)
            shift
            RESULTS_DIR="$1"
            ;;
        --list-tasks)
            LIST_TASKS=true
            ;;
        --help)
            echo "Usage: ./run_benchmark.sh [options]"
            echo ""
            echo "Options:"
            echo "  --task-ids ID1 ID2...    Run tasks with these IDs"
            echo "  --task-names NAME1...    Run tasks with these names"
            echo "  --llm-provider PROVIDER  Set LLM provider (OpenAI, Anthropic, etc.)"
            echo "  --llm-model MODEL        Set LLM model name"
            echo "  --setup                  Perform initial emulator setup"
            echo "  --max-steps N            Maximum steps per task"
            echo "  --combinations N         Number of parameter combinations per task"
            echo "  --results-dir DIR        Directory to save results"
            echo "  --list-tasks             List available tasks and exit"
            echo "  --help                   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
    shift
done

# Construct the python command
CMD="python -m eval.android_world_bench"

# Add arguments
if [ "$LIST_TASKS" = true ]; then
    CMD="$CMD --list-tasks"
fi

if [ -n "$TASK_IDS" ]; then
    CMD="$CMD --task-ids $TASK_IDS"
fi

if [ -n "$TASK_NAMES" ]; then
    CMD="$CMD --task-names $TASK_NAMES"
fi

CMD="$CMD --llm-provider $LLM_PROVIDER --llm-model $LLM_MODEL"

if [ "$PERFORM_SETUP" = true ]; then
    CMD="$CMD --perform-emulator-setup"
fi

CMD="$CMD --max-steps $MAX_STEPS --n-task-combinations $COMBINATIONS --results-dir $RESULTS_DIR"

# Run the command
echo "Running: $CMD"
eval $CMD 