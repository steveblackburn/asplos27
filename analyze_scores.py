import argparse
import collections
import csv
import os

def calculate_percentile(scores, percentile):
    """Calculate rank-based percentile (value at index)."""
    if not scores:
        return None
    scores_sorted = sorted(scores)
    index = int(percentile * len(scores_sorted))
    # Ensure index is within bounds
    index = min(index, len(scores_sorted) - 1)
    return scores_sorted[index]

def main():
    parser = argparse.ArgumentParser(description="Analyze combined review scores.")
    parser.add_argument("--input", default="data/paper_reviewer_combined_scores.csv", help="Input CSV file")
    parser.add_argument("--output", default="data/paper_stats.csv", help="Output CSV file")
    args = parser.parse_args()

    input_file = args.input
    output_file = args.output

    print(f"Reading scores from {input_file}")

    all_scores = []
    paper_scores = collections.defaultdict(list)

    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                score = float(row['score'])

                if score > 0:
                    all_scores.append(score)

                paper_scores[paper].append(score)
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in input file: {e}")
        return

    # 1. Calculate and print percentiles
    if all_scores:
        p90 = calculate_percentile(all_scores, 0.90)
        p95 = calculate_percentile(all_scores, 0.95)

        print(f"Overall 90th percentile score (non-zero): {p90}")
        print(f"Overall 95th percentile score (non-zero): {p95}")
    else:
        print("No non-zero scores found to calculate percentiles.")

    # 2. Process per-paper scores and write CSV
    results = []
    sorted_papers = sorted(list(paper_scores.keys()), key=int)

    for paper in sorted_papers:
        scores = paper_scores[paper]
        # Filter non-zero
        non_zero_scores = [s for s in scores if s > 0]
        # Sort descending
        non_zero_scores.sort(reverse=True)

        # Construct row: paper, score1, score2, ...
        # Convert to int for output since combined scores were rounded to integers
        row_data = [paper] + [int(s) for s in non_zero_scores]
        results.append(row_data)

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"Writing paper stats to {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # No header as planned
        writer.writerows(results)

    print("Done.")

if __name__ == "__main__":
    main()
