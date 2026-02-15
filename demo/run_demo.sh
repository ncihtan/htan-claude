#!/bin/bash
# HTAN Skill Demo — Run prompts headlessly and save outputs to markdown
#
# Usage:
#   cd <project-with-htan-installed>
#   bash /path/to/htan-skill/demo/run_demo.sh [output_dir]
#
# Runs each demo prompt via `claude -p` and saves the output as .md files.
# Requires: claude CLI, htan package installed in project venv

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_MD="$SCRIPT_DIR/../skills/htan/SKILL.md"
OUTPUT_DIR="${1:-demo/output}"
mkdir -p "$OUTPUT_DIR"

if [[ ! -f "$SKILL_MD" ]]; then
    echo "ERROR: Cannot find SKILL.md at $SKILL_MD"
    exit 1
fi

run_prompt() {
    local num="$1"
    local name="$2"
    local prompt="$3"
    local outfile="$OUTPUT_DIR/${num}_${name}.md"

    echo "━━━ [$num] $name"
    echo "    Prompt: $prompt"
    echo "    Output: $outfile"

    # stream-json captures everything: tool calls, thinking, results
    claude -p \
        --append-system-prompt-file "$SKILL_MD" \
        --allowedTools "Bash(uv run htan *)" "Bash(uv run synapse *)" \
        --output-format stream-json \
        --verbose \
        "$prompt" \
        > "$OUTPUT_DIR/${num}_${name}.jsonl" 2>&1

    # Extract final text response into readable markdown
    {
        echo "# $prompt"
        echo ""
        echo "---"
        echo ""
        python3 -c "
import json, sys
result_text = None
assistant_parts = []
for line in open(sys.argv[1]):
    line = line.strip()
    if not line:
        continue
    try:
        evt = json.loads(line)
    except json.JSONDecodeError:
        continue
    if evt.get('type') == 'result':
        result_text = evt.get('result', '')
    elif evt.get('type') == 'assistant' and 'message' in evt:
        for block in evt['message'].get('content', []):
            if block.get('type') == 'text':
                assistant_parts.append(block['text'])
print(result_text if result_text is not None else ''.join(assistant_parts))
" "$OUTPUT_DIR/${num}_${name}.jsonl" 2>/dev/null || echo "(no result parsed)"
    } > "$outfile"

    echo "    ✓ Done ($(wc -l < "$outfile") lines)"
    echo "      Trace: ${num}_${name}.jsonl"
    echo ""
}

echo "╔══════════════════════════════════════════════╗"
echo "║         HTAN Skill Demo (Headless)           ║"
echo "║  Running prompts and saving to: $OUTPUT_DIR  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# --- Act 1: Data Discovery ---
run_prompt "01" "overview" \
    "Give me an overview of what data is available in HTAN"

run_prompt "02" "scrna-breast" \
    "Find all scRNA-seq files from breast cancer, show me the 10 smallest open-access ones"

run_prompt "03" "demographics-ohsu" \
    "What clinical demographics are available for HTAN OHSU patients?"

# --- Act 2: BigQuery ---
run_prompt "04" "bigquery-multimodal" \
    "Using BigQuery, how many unique participants per cancer type have both scRNA-seq and imaging data?"

# --- Act 3: Publications ---
run_prompt "05" "pubs-spatial" \
    "Search for HTAN publications about spatial transcriptomics from 2024"

# --- Act 4: Data Model ---
run_prompt "06" "model-scrna" \
    "What attributes are required for an scRNA-seq Level 1 manifest? Show valid values for Library Construction Method."

# --- Act 5: Downloads ---
run_prompt "07" "download-open" \
    "Find the smallest open-access scRNA-seq file from breast cancer and download it using synapse get"

run_prompt "08" "download-controlled" \
    "Show me how I would download a controlled-access file via Gen3 dry run only"

echo "╔══════════════════════════════════════════════╗"
echo "║           Demo complete!                     ║"
echo "║  Outputs saved to: $OUTPUT_DIR/              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
ls -1 "$OUTPUT_DIR"/*.md
