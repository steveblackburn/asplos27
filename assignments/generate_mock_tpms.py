import argparse
import csv
import os
import random

def main():
    parser = argparse.ArgumentParser(description="Generate mock TPMS scores based on topic scores.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix (e.g., asplos27-apr)")
    parser.add_argument("--seed-file", default="data/paper-reviewer-topic-scores.csv", help="Seed CSV file")
    parser.add_argument("--output", default="data/from-tpms/tpms-mock.csv", help="Output CSV file path")
    parser.add_argument("--conflicts-dir", default="data/from-hotcrp", help="Directory containing conflicts file")
    parser.add_argument("--real-data", default=None, help="Path to sample real TPMS data CSV")
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

    # 1.5 Read real data and model if available
    real_scores = {}
    real_reviewers = set()
    slope = 1.0
    intercept = 0.0
    noise_std = 0.2 # Default noise if no real data

    if args.real_data:
        print(f"Reading real TPMS data from {args.real_data}")
        try:
            with open(args.real_data, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        paper = row[0]
                        reviewer = row[1]
                        score = float(row[2])
                        real_scores[(paper, reviewer)] = score
                        real_reviewers.add(reviewer)
        except FileNotFoundError:
            print(f"Error: Real data file not found: {args.real_data}")
            return
        
        # Read topic scores for overlap
        topic_scores = {}
        try:
            with open(seed_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    topic_scores[(row['paper'], row['reviewer'])] = float(row['score'])
        except Exception as e:
            print(f"Error reading seed file for modeling: {e}")
            return
            
        # Find overlap
        common_pairs = set(real_scores.keys()).intersection(set(topic_scores.keys()))
        print(f"Found {len(common_pairs)} common pairs for modeling.")
        
        if len(common_pairs) > 1:
            # Linear regression
            x_vals = [topic_scores[p] for p in common_pairs]
            y_vals = [real_scores[p] for p in common_pairs]
            
            mean_x = sum(x_vals) / len(x_vals)
            mean_y = sum(y_vals) / len(y_vals)
            
            num = sum((x_vals[i] - mean_x) * (y_vals[i] - mean_y) for i in range(len(x_vals)))
            den = sum((x_vals[i] - mean_x)**2 for i in range(len(x_vals)))
            
            if den != 0:
                slope = num / den
                intercept = mean_y - slope * mean_x
                
                # Calculate residuals std dev
                residuals = [y_vals[i] - (slope * x_vals[i] + intercept) for i in range(len(x_vals))]
                mean_res = sum(residuals) / len(residuals)
                var_res = sum((r - mean_res)**2 for r in residuals) / len(residuals)
                noise_std = var_res**0.5
                
                print(f"Model: TPMS = {slope:.4f} * TopicScore + {intercept:.4f}")
                print(f"Noise StdDev: {noise_std:.4f}")
            else:
                print("Cannot compute regression, denominator is zero. Using default noise.")
        else:
            print("Not enough common pairs to model. Using default noise.")

    # 2. Read seed data and generate mock scores
    results = []
    try:
        with open(seed_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score_str = row['score']

                # Skip reviewers missing from actual TPMS data if real data is provided
                if args.real_data and reviewer not in real_reviewers:
                    continue

                try:
                    orig_score = float(score_str)
                except ValueError:
                    orig_score = 0.0

                if (paper, reviewer) in conflicts:
                    new_score = 0.0
                elif args.real_data and (paper, reviewer) in real_scores:
                    # Use real data if available
                    new_score = real_scores[(paper, reviewer)]
                else:
                    # Use model
                    if args.real_data:
                        # Use calculated slope, intercept, and noise
                        noise = random.gauss(0, noise_std)
                        new_score = slope * orig_score + intercept + noise
                    else:
                        # Fallback to old behavior if no real data provided
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

    print(f"Writing data to {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # NO HEADER!
        for row in results:
            writer.writerow([row['paper'], row['reviewer'], f"{row['score']:.4f}"])

    print("Done.")

if __name__ == "__main__":
    main()
