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
    parser = argparse.ArgumentParser(description="Filter review scores for PC and VC members.")
    parser.add_argument("--input", default="data/paper-reviewer-combined-scores.csv", help="Input CSV file")
    parser.add_argument("--pc-info", default="data/from-hotcrp/asplos27-apr-pcinfo.csv", help="PC info CSV from HotCRP")
    parser.add_argument("--output-pc", default="data/paper-stats-pc.csv", help="Output CSV file for PC/ERC scores")
    parser.add_argument("--output-vc", default="data/paper-stats-vc.csv", help="Output CSV file for VC scores")
    args = parser.parse_args()

    input_file = args.input
    pcinfo_file = args.pc_info
    output_pc_file = args.output_pc
    output_vc_file = args.output_vc

    # Load PC info
    pc_reviewers = set()
    vc_reviewers = set()
    
    print(f"Reading PC info from {pcinfo_file}")
    try:
        with open(pcinfo_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                if 'pc-full' in tags or 'erc' in tags:
                    pc_reviewers.add(email)
                if 'vc' in tags:
                    vc_reviewers.add(email)
    except FileNotFoundError:
        print(f"Error: PC info file not found: {pcinfo_file}")
        return

    print(f"Reading scores from {input_file}")

    all_scores = []
    pc_scores = collections.defaultdict(list)
    vc_scores = collections.defaultdict(list)

    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score = float(row['score'])

                if score > 0:
                    all_scores.append(score)
                    
                    if reviewer in pc_reviewers:
                        pc_scores[paper].append(score)
                    if reviewer in vc_reviewers:
                        vc_scores[paper].append(score)
                        
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in input file: {e}")
        return

    # Calculate and print percentiles on all non-zero scores
    if all_scores:
        p90 = calculate_percentile(all_scores, 0.90)
        p95 = calculate_percentile(all_scores, 0.95)

        print(f"Overall 90th percentile score (non-zero): {p90}")
        print(f"Overall 95th percentile score (non-zero): {p95}")
    else:
        print("No non-zero scores found to calculate percentiles.")

    # Process PC scores
    results_pc = []
    sorted_papers_pc = sorted(list(pc_scores.keys()), key=int)
    for paper in sorted_papers_pc:
        scores = pc_scores[paper]
        scores.sort(reverse=True)
        results_pc.append([paper] + [int(s) for s in scores])

    # Process VC scores
    results_vc = []
    sorted_papers_vc = sorted(list(vc_scores.keys()), key=int)
    for paper in sorted_papers_vc:
        scores = vc_scores[paper]
        scores.sort(reverse=True)
        results_vc.append([paper] + [int(s) for s in scores])

    # Write PC scores
    pc_dir = os.path.dirname(output_pc_file)
    if pc_dir and not os.path.exists(pc_dir):
        os.makedirs(pc_dir, exist_ok=True)
    print(f"Writing PC scores to {output_pc_file}")
    with open(output_pc_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # No header as planned
        writer.writerows(results_pc)

    # Write VC scores
    vc_dir = os.path.dirname(output_vc_file)
    if vc_dir and not os.path.exists(vc_dir):
        os.makedirs(vc_dir, exist_ok=True)
    print(f"Writing VC scores to {output_vc_file}")
    with open(output_vc_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # No header as planned
        writer.writerows(results_vc)

    print("Done.")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
