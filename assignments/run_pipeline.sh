#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo
echo "Step 1: Generating topic scores..."
python3 generate_topic_scores.py

echo
echo "Step 2: Rescaling scores..."
python3 rescale_scores.py

echo
echo "Step 3: Combining scores..."
python3 combine_scores.py

echo
echo "Step 4: Analyzing and splitting scores..."
python3 analyze_scores.py

echo
echo "Step 5: Running reviewer assignment..."
python3 assign_reviewers.py --min-relative-score 0.75

echo
echo "Step 6: Analyzing assignments..."
python3 analyze_assignments.py

echo
echo "Step 7: Checking author submission limits..."
python3 check_authors.py

echo
echo "Step 8: Analyzing topics..."
python3 analyze_topics.py

echo "All scripts executed successfully!"
