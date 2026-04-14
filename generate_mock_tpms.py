import argparse
import csv
import os
import random

def main():
    parser = argparse.ArgumentParser(description="Generate mock TPMS scores based on topic scores.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix (e.g., asplos27-apr)")
    parser.add_argument("--seed-file", default="data/paper_reviewer_topic_scores.csv", help="Seed CSV file")
    parser.add_argument("--output", default="data/from-tpms/tpms-mock.csv", help="Output CSV file path")
    parser.add_argument("--conflicts-dir", default="data/from-hotcrp", help="Directory containing conflicts file")
    args = parser.parse_args()

    prefix = args.prefix
    seed_file = args.seed_file
    output_file = args.output
    conflicts_dir = args.conflicts_dir

    conflicts_file = os.path.join(conflicts_dir, f"{prefix}-pcconflicts.csv")

    print(f"Reading conflicts from {conflicts_file}")
    print(f"Reading seed data from {seed_file}")

    # 1. Read conflicts
    conflicts = set()
    try:
        with open(conflicts_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conflicts.add((row['paper'], row['email']))
    except FileNotFoundError:
        print(f"Warning: Conflicts file not found: {conflicts_file}")
        print("Proceeding without conflicts check.")
    except KeyError as e:
        print(f"Error: Missing expected column in conflicts file: {e}")
        return

    # 2. Read seed data and generate mock scores
    results = []
    try:
        with open(seed_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score_str = row['score']

                try:
                    orig_score = float(score_str)
                except ValueError:
                    orig_score = 0.0

                if (paper, reviewer) in conflicts:
                    new_score = 0.0
                else:
                    # Add noise +/- 0.2
                    noise = random.uniform(-0.2, 0.2)
                    new_score = orig_score + noise
                    # Clip to [0, 1]
                    new_score = max(0.0, min(1.0, new_score))

                results.append({
                    'paper': paper,
                    'reviewer': reviewer,
                    'score': new_score
                })
    except FileNotFoundError:
        print(f"Error: Seed file not found: {seed_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in seed file: {e}")
        return

    # 3. Write output
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"Writing mock data to {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['paper', 'reviewer', 'score'])
        writer.writeheader()
        for row in results:
            writer.writerow({
                'paper': row['paper'],
                'reviewer': row['reviewer'],
                'score': f"{row['score']:.4f}"
            })

    print("Done.")

if __name__ == "__main__":
    main()
