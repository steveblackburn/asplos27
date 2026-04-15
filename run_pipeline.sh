#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Step 1: Generating topic scores..."
python3 generate_topic_scores.py

echo "Step 2: Generating mock TPMS scores..."
# Note: This generates mock data. If you have real TPMS data, 
# you should skip this step or provide the path to real data.
python3 generate_mock_tpms.py

echo "Step 3: Combining scores..."
python3 combine_scores.py

echo "Step 4: Analyzing and splitting scores..."
python3 analyze_scores.py

echo "Step 5: Running reviewer assignment..."
python3 assign_reviewers.py

echo "All scripts executed successfully!"
