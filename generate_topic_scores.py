import argparse
import collections
import csv
import os

def main():
    parser = argparse.ArgumentParser(description="Calculate reviewer expertise scores for paper submissions.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix (e.g., asplos27-apr)")
    parser.add_argument("--data-dir", default="data/from-hotcrp", help="Directory containing input CSV files")
    parser.add_argument("--output", default="data/paper_reviewer_topic_scores.csv", help="Output CSV file path")
    args = parser.parse_args()

    prefix = args.prefix
    data_dir = args.data_dir
    output_file = args.output

    topics_file = os.path.join(data_dir, f"{prefix}-topics.csv")
    pcinfo_file = os.path.join(data_dir, f"{prefix}-pcinfo.csv")
    conflicts_file = os.path.join(data_dir, f"{prefix}-pcconflicts.csv")

    print(f"Reading topics from {topics_file}")
    print(f"Reading pcinfo from {pcinfo_file}")
    print(f"Reading conflicts from {conflicts_file}")

    # 1. Read topics
    # paper -> list of topics
    paper_topics = collections.defaultdict(list)
    try:
        with open(topics_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_topics[row['paper']].append(row['topic'])
    except FileNotFoundError:
        print(f"Error: File not found: {topics_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in topics file: {e}")
        return

    # 2. Read reviewer expertise
    # email -> topic -> score
    reviewer_expertise = {}
    try:
        with open(pcinfo_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                print(f"Error: {pcinfo_file} is empty or has no header.")
                return
            
            topic_cols = [col for col in fieldnames if col.startswith("topic: ")]
            
            for row in reader:
                email = row['email']
                expertise = {}
                for col in topic_cols:
                    topic_name = col.replace("topic: ", "")
                    val = row[col]
                    if val and val.strip():  # If not empty or whitespace
                        try:
                            expertise[topic_name] = int(val)
                        except ValueError:
                            # Handle cases where value is not an integer if any
                            pass
                reviewer_expertise[email] = expertise
    except FileNotFoundError:
        print(f"Error: File not found: {pcinfo_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in pcinfo file: {e}")
        return

    # 3. Read conflicts
    # set of (paper, email)
    conflicts = set()
    try:
        with open(conflicts_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conflicts.add((row['paper'], row['email']))
    except FileNotFoundError:
        print(f"Error: File not found: {conflicts_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in conflicts file: {e}")
        return

    # 4. Calculate scores
    results = []
    all_papers = sorted(list(paper_topics.keys()), key=int)
    all_reviewers = sorted(list(reviewer_expertise.keys()))

    for paper in all_papers:
        topics = paper_topics[paper]
        for email in all_reviewers:
            if (paper, email) in conflicts:
                score = 0
            else:
                expertise = reviewer_expertise[email]
                sum_score = 0
                for topic in topics:
                    rating = expertise.get(topic, 0)  # Option A: treat missing as 0
                    sum_score += rating + 2
                
                if topics:
                    avg = sum_score / len(topics)
                    score = avg * 25
                else:
                    score = 0

            results.append({
                'paper': paper,
                'reviewer': email,
                'score': round(score, 2)  # Round to 2 decimal places
            })

    # 5. Write output
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print(f"Writing results to {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['paper', 'reviewer', 'score'])
        writer.writeheader()
        writer.writerows(results)

    print("Done.")

if __name__ == "__main__":
    main()
