import argparse
import csv
import os

def main():
    parser = argparse.ArgumentParser(description="Combine topic scores and TPMS scores.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix (e.g., asplos27-apr)")
    parser.add_argument("--topic-file", default="data/paper-reviewer-topic-scores.csv", help="Topic scores CSV file")
    parser.add_argument("--tpms-file", default="data/from-tpms/asplos27_scores.csv", help="TPMS scores CSV file")
    parser.add_argument("--output", default="data/paper-reviewer-combined-scores.csv", help="Output CSV file path")
    parser.add_argument("--conflicts-dir", default="data/from-hotcrp", help="Directory containing conflicts file")
    parser.add_argument("--method", choices=['weighted', 'mult', 'min', 'max'], default='weighted', help="Combination method")
    parser.add_argument("--weight-topic", type=float, default=0.5, help="Weight for topic score (for weighted method)")
    parser.add_argument("--weight-tpms", type=float, default=0.5, help="Weight for TPMS score (for weighted method)")
    args = parser.parse_args()

    prefix = args.prefix
    topic_file = args.topic_file
    tpms_file = args.tpms_file
    output_file = args.output
    conflicts_dir = args.conflicts_dir
    method = args.method
    w_topic = args.weight_topic
    w_tpms = args.weight_tpms

    conflicts_file = os.path.join(conflicts_dir, f"{prefix}-pcconflicts.csv")

    print(f"Reading conflicts from {conflicts_file}")
    print(f"Reading topic scores from {topic_file}")
    print(f"Reading TPMS scores from {tpms_file}")

    # 1. Read conflicts
    conflicts = set()
    try:
        with open(conflicts_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conflicts.add((row['paper'], row['email']))
    except FileNotFoundError:
        print(f"Warning: Conflicts file not found: {conflicts_file}")
        print("Proceeding without strict conflicts enforcement.")
    except KeyError as e:
        print(f"Error: Missing expected column in conflicts file: {e}")
        return

    # 1.5 Read valid papers from authors file (ground truth)
    valid_papers = set()
    authors_file = os.path.join(conflicts_dir, f"{prefix}-authors.csv")
    try:
        with open(authors_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                valid_papers.add(row['paper'])
    except FileNotFoundError:
        print(f"Warning: Authors file not found: {authors_file}")
        print("Cannot enforce ground truth for valid papers.")
    except KeyError as e:
        print(f"Error: Missing expected column in authors file: {e}")
        return

    # 2. Read topic scores
    topic_scores = {}
    try:
        with open(topic_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic_scores[(row['paper'], row['reviewer'])] = float(row['score'])
    except FileNotFoundError:
        print(f"Error: Topic scores file not found: {topic_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in topic scores file: {e}")
        return

    # 3. Read TPMS scores
    tpms_scores = {}
    try:
        with open(tpms_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    tpms_scores[(row[0], row[1])] = float(row[2])
    except FileNotFoundError:
        print(f"Error: TPMS scores file not found: {tpms_file}")
        return

    # Warn if any paper exists in TPMS but not in topic scores
    topic_papers = set(p for p, r in topic_scores.keys())
    tpms_papers = set(p for p, r in tpms_scores.keys())
    tpms_only_papers = tpms_papers - topic_papers
    
    if tpms_only_papers:
        print(f"Warning: The following {len(tpms_only_papers)} papers exist in TPMS but not in topic scores (suggests withdrawal):")
        for p in sorted(list(tpms_only_papers), key=int):
            print(f"  {p}")

    # 4. Combine scores
    results = []
    
    # Identify missing reviewers
    topic_reviewers = set(r for p, r in topic_scores.keys())
    tpms_reviewers = set(r for p, r in tpms_scores.keys())
    missing_reviewers = topic_reviewers - tpms_reviewers
    
    if missing_reviewers:
        print(f"Warning: The following {len(missing_reviewers)} reviewers are missing from TPMS data:")
        for r in sorted(list(missing_reviewers)):
            print(f"  {r}")
            
    all_pairs = set(topic_scores.keys()).union(set(tpms_scores.keys()))

    for paper, reviewer in sorted(list(all_pairs), key=lambda x: (int(x[0]), x[1])):
        if valid_papers and paper not in valid_papers:
            continue
        if (paper, reviewer) in conflicts:
            final_score = 0
        else:
            t_score = topic_scores.get((paper, reviewer), 0.0)
            
            if (paper, reviewer) in tpms_scores:
                m_score = tpms_scores[(paper, reviewer)]
                
                if method == 'weighted':
                    combined = (w_topic * t_score + w_tpms * m_score) / (w_topic + w_tpms)
                elif method == 'mult':
                    combined = t_score * m_score
                elif method == 'min':
                    combined = min(t_score, m_score)
                elif method == 'max':
                    combined = max(t_score, m_score)
                else:
                    combined = 0.0
            else:
                # Reviewer missing from TPMS data for this paper (or entirely)
                # Use topic score alone
                combined = t_score

            # Scale to 0-100 and round to integer
            final_score = round(combined * 100)
            # Ensure within 0-100
            final_score = max(0, min(100, final_score))

        results.append({
            'paper': paper,
            'reviewer': reviewer,
            'score': final_score
        })

    # 5. Write output
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"Writing combined scores to {output_file} using method: {method}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['paper', 'reviewer', 'score'])
        writer.writeheader()
        writer.writerows(results)

    print("Done.")

if __name__ == "__main__":
    main()
