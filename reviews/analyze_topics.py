import csv
import os
from collections import defaultdict
import statistics

def main():
    topics_file = "../assignments/data/from-hotcrp/asplos27-apr-topics.csv"
    assignments_file = "../assignments/data/to-hotcrp/asplos27-apr-pc-assignments.csv"
    tpms_file = "../assignments/data/from-tpms/asplos27_scores.csv"
    reviews_file = "data/from-hotcrp/asplos27-apr-reviews.csv"
    paper_stats_file = "data/analysis/paper-stats.csv"
    output_file = "data/analysis/topic-review-stats.csv"

    # 1. Load Topics: paper -> list of topics
    paper_to_topics = defaultdict(list)
    all_topics = set()
    if os.path.exists(topics_file):
        with open(topics_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                topic = row['topic']
                paper_to_topics[paper].append(topic)
                all_topics.add(topic)
    else:
        print(f"Error: Topics file not found at {topics_file}")
        return

    # 2. Load Assignments: paper -> list of reviewer emails
    paper_to_reviewers = defaultdict(list)
    if os.path.exists(assignments_file):
        with open(assignments_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['action'] == 'primary' or row['action'] == 'secondary':
                    paper = row['paper']
                    email = row['email']
                    if email != 'all':
                        paper_to_reviewers[paper].append(email)
    else:
        print(f"Error: Assignments file not found at {assignments_file}")
        return

    # 3. Load TPMS Scores: (paper, email) -> tpms_score
    tpms_scores = {}
    if os.path.exists(tpms_file):
        with open(tpms_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 3:
                    paper, email, score = parts
                    tpms_scores[(paper, email)] = float(score)
    else:
        print(f"Error: TPMS scores file not found at {tpms_file}")
        return

    # 4. Load Reviews: paper -> list of review stats
    paper_reviews = defaultdict(list)
    if os.path.exists(reviews_file):
        with open(reviews_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                
                def get_int(val):
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return None

                paper_reviews[paper].append({
                    'confidence': get_int(row.get('Confidence')),
                    'expertise': get_int(row.get('Reviewer expertise')),
                    'arch': get_int(row.get('Advances computer architecture research')),
                    'pl': get_int(row.get('Advances programming languages research')),
                    'os': get_int(row.get('Advances operating systems research')),
                    'new_area': get_int(row.get('Introduces new area')),
                    'overall': get_int(row.get('Overall Strong ASPLOS paper')),
                    'ranking': get_int(row.get('Ranking'))
                })
    else:
        print(f"Error: Reviews file not found at {reviews_file}")
        return

    # 5. Load Paper Ranks: paper -> percentile_rank
    paper_ranks = {}
    if os.path.exists(paper_stats_file):
        with open(paper_stats_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                rank = row.get('rank')
                if rank:
                    paper_ranks[paper] = int(rank)
    else:
        print(f"Error: Paper stats file not found at {paper_stats_file}")
        return

    # 6. Compute Topic Stats
    topic_stats = {}
    for topic in all_topics:
        papers_in_topic = [paper for paper, topics in paper_to_topics.items() if topic in topics]
        num_papers = len(papers_in_topic)
        
        # TPMS scores of assigned reviewers
        topic_tpms = []
        for paper in papers_in_topic:
            reviewers = paper_to_reviewers.get(paper, [])
            for email in reviewers:
                score = tpms_scores.get((paper, email))
                if score is not None:
                    topic_tpms.append(score)
        
        median_tpms = statistics.median(topic_tpms) if topic_tpms else None
        
        # Review scores
        confidences = []
        expertises = []
        archs = []
        pls = []
        oss = []
        new_areas = []
        overalls = []
        rankings = []
        
        for paper in papers_in_topic:
            reviews = paper_reviews.get(paper, [])
            for r in reviews:
                if r['confidence'] is not None: confidences.append(r['confidence'])
                if r['expertise'] is not None: expertises.append(r['expertise'])
                if r['arch'] is not None: archs.append(r['arch'])
                if r['pl'] is not None: pls.append(r['pl'])
                if r['os'] is not None: oss.append(r['os'])
                if r['new_area'] is not None: new_areas.append(r['new_area'])
                if r['overall'] is not None: overalls.append(r['overall'])
                if r['ranking'] is not None: rankings.append(r['ranking'])
                
        def mean(lst):
            return sum(lst) / len(lst) if lst else None

        mean_confidence = mean(confidences)
        mean_expertise = mean(expertises)
        mean_arch = mean(archs)
        mean_pl = mean(pls)
        mean_os = mean(oss)
        mean_new_area = mean(new_areas)
        mean_overall = mean(overalls)
        mean_ranking = mean(rankings)
        
        # Percentile scores
        pcls = []
        for paper in papers_in_topic:
            pcl = paper_ranks.get(paper)
            if pcl is not None:
                pcls.append(pcl)
        
        mean_pcl = mean(pcls)
        
        topic_stats[topic] = {
            'num_papers': num_papers,
            'median_tpms': median_tpms,
            'mean_confidence': mean_confidence,
            'mean_expertise': mean_expertise,
            'mean_arch': mean_arch,
            'mean_pl': mean_pl,
            'mean_os': mean_os,
            'mean_new_area': mean_new_area,
            'mean_overall': mean_overall,
            'mean_ranking': mean_ranking,
            'mean_pcl': mean_pcl
        }

    # 7. Output Results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'topic', 'num_submitted_papers', 'median_tpms', 
            'mean_confidence', 'mean_expertise', 
            'mean_arch', 'mean_pl', 'mean_os', 'mean_new_area', 
            'mean_overall', 'mean_ranking', 'mean_percentile'
        ])
        
        for topic in sorted(all_topics):
            stats = topic_stats[topic]
            
            def fmt(val):
                return f"{val:.2f}" if val is not None else ''

            writer.writerow([
                topic,
                stats['num_papers'],
                fmt(stats['median_tpms']),
                fmt(stats['mean_confidence']),
                fmt(stats['mean_expertise']),
                fmt(stats['mean_arch']),
                fmt(stats['mean_pl']),
                fmt(stats['mean_os']),
                fmt(stats['mean_new_area']),
                fmt(stats['mean_overall']),
                fmt(stats['mean_ranking']),
                fmt(stats['mean_pcl'])
            ])
            
    print(f"Successfully wrote topic stats to {output_file}")

if __name__ == '__main__':
    main()
