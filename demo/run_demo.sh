#!/bin/bash
# HTAN Skill Demo — Keystroke injection for screen recording
#
# Usage:
#   1. Open Terminal, resize to 120x35
#   2. Start: claude --plugin-dir ~/Documents/projects/htan2/htan-skill
#   3. Start screen recording (Cmd+Shift+5)
#   4. In a SECOND terminal: bash demo/run_demo.sh
#   5. Press Enter after each prompt completes in Claude
#   6. Stop recording when done

type_prompt() {
    local text="$1"
    echo ""
    echo "━━━ Next prompt: $text"
    echo "    Press Enter when Claude is ready..."
    read -r
    osascript -e "tell application \"System Events\" to keystroke \"$text\""
    sleep 0.5
    osascript -e 'tell application "System Events" to keystroke return'
    echo "    ✓ Sent. Wait for Claude to finish, then press Enter."
    read -r
}

echo "╔══════════════════════════════════════════╗"
echo "║         HTAN Skill Demo Script           ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Switch to Claude Code window now.       ║"
echo "║  Press Enter here to send each prompt.   ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Press Enter to begin..."
read -r

# --- Act 1: Setup ---
echo "═══ ACT 1: Setup ═══"

type_prompt "/htan"

type_prompt "Set up the htan skill — create a venv and install the package"

type_prompt "Configure portal credentials with htan init"

type_prompt "Add the uv run htan permission rule to .claude/settings.json"

# --- Act 2: Discovery ---
echo ""
echo "═══ ACT 2: Data Discovery ═══"

type_prompt "Give me an overview of what data is available in HTAN"

type_prompt "Find all scRNA-seq files from breast cancer, show me the 10 smallest open-access ones"

type_prompt "What clinical demographics are available for HTAN OHSU patients?"

# --- Act 3: Deep Query ---
echo ""
echo "═══ ACT 3: BigQuery ═══"

type_prompt "Using BigQuery, how many unique participants per cancer type have both scRNA-seq and imaging data?"

# --- Act 4: Publications ---
echo ""
echo "═══ ACT 4: Publications ═══"

type_prompt "Search for HTAN publications about spatial transcriptomics from 2024"

# --- Act 5: Data Model ---
echo ""
echo "═══ ACT 5: Data Model ═══"

type_prompt "What attributes are required for an scRNA-seq Level 1 manifest? Show valid values for Library Construction Method."

# --- Act 6: Downloads ---
echo ""
echo "═══ ACT 6: Downloads ═══"

type_prompt "Download the smallest open-access file we found earlier using synapse get"

type_prompt "For the controlled-access files, show me how I would download one via Gen3 dry run only"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           Demo complete!                 ║"
echo "║     Stop screen recording now.           ║"
echo "╚══════════════════════════════════════════╝"
