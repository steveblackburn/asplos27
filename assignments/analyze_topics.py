import csv
import statistics
from collections import defaultdict
import os

def main():
    topics_file = "data/from-hotcrp/asplos27-apr-topics.csv"
    tpms_file = "data/paper-reviewer-scaled-tpms.csv"
    topic_scores_file = "data/paper-reviewer-scaled-topic.csv"
    assignments_file = "data/pc-assignments.csv"
    output_file = "data/analysis/topic-analysis.csv"

    # Read assignments
    paper_to_assigned = defaultdict(list)
    try:
        print(f"Reading assignments from {assignments_file}")
        with open(assignments_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_to_assigned[row['paper']].append(row['reviewer'])
    except FileNotFoundError:
        print(f"Error: Assignments file not found: {assignments_file}")
        return

    # Read topics
    topic_to_papers = defaultdict(set)
    try:
        print(f"Reading topics from {topics_file}")
        with open(topics_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic_to_papers[row['topic']].add(row['paper'])
    except FileNotFoundError:
        print(f"Error: Topics file not found: {topics_file}")
        return

    # Read TPMS scores
    paper_tpms_scores = defaultdict(list)
    tpms_scores_dict = {}
    try:
        print(f"Reading TPMS scores from {tpms_file}")
        with open(tpms_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score = float(row['score'])
                paper_tpms_scores[paper].append(score)
                tpms_scores_dict[(paper, reviewer)] = score
    except FileNotFoundError:
        print(f"Error: TPMS scores file not found: {tpms_file}")
        return

    # Read Topic scores
    paper_topic_scores = defaultdict(list)
    topic_scores_dict = {}
    try:
        print(f"Reading Topic scores from {topic_scores_file}")
        with open(topic_scores_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score = float(row['score'])
                paper_topic_scores[paper].append(score)
                topic_scores_dict[(paper, reviewer)] = score
    except FileNotFoundError:
        print(f"Error: Topic scores file not found: {topic_scores_file}")
        return

    # Analyze
    output_rows = []
    for topic, papers in topic_to_papers.items():
        count = len(papers)
        
        all_tpms = []
        all_topic = []
        assigned_tpms = []
        assigned_topic = []
        
        for p in papers:
            all_tpms.extend(paper_tpms_scores[p])
            all_topic.extend(paper_topic_scores[p])
            
            assigned_revs = paper_to_assigned.get(p, [])
            for r in assigned_revs:
                if (p, r) in tpms_scores_dict:
                    assigned_tpms.append(tpms_scores_dict[(p, r)])
                if (p, r) in topic_scores_dict:
                    assigned_topic.append(topic_scores_dict[(p, r)])
            
        median_all_tpms = statistics.median(all_tpms) if all_tpms else 0.0
        median_all_topic = statistics.median(all_topic) if all_topic else 0.0
        median_assigned_tpms = statistics.median(assigned_tpms) if assigned_tpms else 0.0
        median_assigned_topic = statistics.median(assigned_topic) if assigned_topic else 0.0
        
        output_rows.append([topic, count, median_assigned_tpms, median_assigned_topic, median_all_tpms, median_all_topic])

    # Sort by median_assigned_tpms ascending (worst to best)
    output_rows.sort(key=lambda x: x[2])

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    print(f"Writing analysis to {output_file}")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['topic', 'paper_count', 'median_assigned_tpms', 'median_assigned_topic', 'median_all_tpms', 'median_all_topic'])
        for row in output_rows:
            writer.writerow([row[0], row[1], f"{row[2]:.4f}", f"{row[3]:.4f}", f"{row[4]:.4f}", f"{row[5]:.4f}"])

    print("Done.")

if __name__ == "__main__":
    main()
