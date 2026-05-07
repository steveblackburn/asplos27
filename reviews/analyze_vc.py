import csv
import os
from collections import defaultdict
import statistics

def main():
    pcinfo_file = "../assignments/data/from-hotcrp/asplos27-apr-pcinfo.csv"
    vc_assignments_file = "../assignments/data/to-hotcrp/asplos27-apr-vc-assignments.csv"
    paper_stats_file = "data/analysis/paper-stats.csv"
    pc_assignments_file = "../assignments/data/to-hotcrp/asplos27-apr-pc-assignments.csv"
    tpms_file = "../assignments/data/from-tpms/asplos27_scores.csv"
    reviews_file = "data/from-hotcrp/asplos27-apr-reviews.csv"
    output_file = "data/analysis/vc-stats.csv"

    # 1. Load VCs: email -> True, and store names
    vc_emails = set()
    vc_names = {} # email -> (first, last)
    if os.path.exists(pcinfo_file):
        with open(pcinfo_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                if 'vc' in tags:
                    vc_emails.add(email)
                    vc_names[email] = (row['given_name'], row['family_name'])
    else:
        print(f"Error: PC info file not found at {pcinfo_file}")
        return

    # 2. Load VC Assignments: paper -> vc_email
    paper_to_vc = {}
    if os.path.exists(vc_assignments_file):
        with open(vc_assignments_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                email = row['email']
                paper_to_vc[paper] = email
    else:
        print(f"Error: VC assignments file not found at {vc_assignments_file}")
        return

    # 3. Load Paper Stats: paper -> {rank, bucket}
    paper_data = {}
    if os.path.exists(paper_stats_file):
        with open(paper_stats_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                rank = row.get('rank')
                if rank:
                    rank = int(rank)
                    if rank >= 81:
                        bucket = 'sc_advance'
                    elif rank >= 61:
                        bucket = 'sc_adjudicate'
                    else:
                        bucket = 'sc_reject'
                    paper_data[paper] = {'rank': rank, 'bucket': bucket}
    else:
        print(f"Error: Paper stats file not found at {paper_stats_file}")
        return

    # 4. Load PC Assignments: paper -> list of reviewer emails
    paper_to_reviewers = defaultdict(list)
    if os.path.exists(pc_assignments_file):
        with open(pc_assignments_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['action'] == 'primary' or row['action'] == 'secondary':
                    paper = row['paper']
                    email = row['email']
                    if email != 'all':
                        paper_to_reviewers[paper].append(email)
    else:
        print(f"Error: PC assignments file not found at {pc_assignments_file}")
        return

    # 5. Load TPMS Scores: (paper, email) -> tpms_score
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

    # 6. Load Reviews: paper -> list of review stats
    paper_reviews = defaultdict(list)
    paper_non_vc_counts = defaultdict(int)
    if os.path.exists(reviews_file):
        with open(reviews_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                email = row.get('email')
                
                if email and email not in vc_emails:
                    paper_non_vc_counts[paper] += 1
                
                def get_int(val):
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return None

                paper_reviews[paper].append({
                    'confidence': get_int(row.get('Confidence')),
                    'expertise': get_int(row.get('Reviewer expertise'))
                })
    else:
        print(f"Error: Reviews file not found at {reviews_file}")
        return

    # 7. Compute VC Stats
    vc_stats = {}
    for vc in vc_emails:
        papers_assigned = [paper for paper, email in paper_to_vc.items() if email == vc]
        num_papers = len(papers_assigned)
        
        num_papers_ready = sum(1 for paper in papers_assigned if paper_non_vc_counts[paper] >= 3)
        
        num_advance = 0
        num_adjudicate = 0
        num_reject = 0
        pcls = []
        
        for paper in papers_assigned:
            data = paper_data.get(paper)
            if data:
                pcls.append(data['rank'])
                if data['bucket'] == 'sc_advance':
                    num_advance += 1
                elif data['bucket'] == 'sc_adjudicate':
                    num_adjudicate += 1
                elif data['bucket'] == 'sc_reject':
                    num_reject += 1
                    
        mean_pcl = sum(pcls) / len(pcls) if pcls else None
        median_pcl = statistics.median(pcls) if pcls else None
        
        # TPMS scores
        vc_tpms = []
        for paper in papers_assigned:
            reviewers = paper_to_reviewers.get(paper, [])
            for email in reviewers:
                score = tpms_scores.get((paper, email))
                if score is not None:
                    vc_tpms.append(score)
        
        mean_tpms = sum(vc_tpms) / len(vc_tpms) if vc_tpms else None
        
        # Experience and Confidence
        expertises = []
        confidences = []
        for paper in papers_assigned:
            reviews = paper_reviews.get(paper, [])
            for r in reviews:
                if r['expertise'] is not None: expertises.append(r['expertise'])
                if r['confidence'] is not None: confidences.append(r['confidence'])
                
        def mean(lst):
            return sum(lst) / len(lst) if lst else None

        mean_expertise = mean(expertises)
        mean_confidence = mean(confidences)
        
        vc_stats[vc] = {
            'num_papers': num_papers,
            'num_papers_ready': num_papers_ready,
            'num_advance': num_advance,
            'num_adjudicate': num_adjudicate,
            'num_reject': num_reject,
            'mean_pcl': mean_pcl,
            'median_pcl': median_pcl,
            'mean_tpms': mean_tpms,
            'mean_expertise': mean_expertise,
            'mean_confidence': mean_confidence
        }

    # 8. Output Results
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'vc_name', 'num_assigned_papers', 'num_papers_ready',
            'num_sc_advance', 'num_sc_adjudicate', 'num_sc_reject', 
            'mean_pctl', 'median_pctl', 
            'mean_reviewer_tpms', 'mean_reviewer_experience', 'mean_reviewer_confidence'
        ])
        
        for vc in sorted(vc_emails, key=lambda e: vc_names[e][1]):
            stats = vc_stats[vc]
            
            def fmt(val):
                return f"{val:.2f}" if val is not None else ''

            writer.writerow([
                f"{vc_names[vc][0]} {vc_names[vc][1]}",
                stats['num_papers'],
                stats['num_papers_ready'],
                stats['num_advance'],
                stats['num_adjudicate'],
                stats['num_reject'],
                fmt(stats['mean_pcl']),
                fmt(stats['median_pcl']),
                fmt(stats['mean_tpms']),
                fmt(stats['mean_expertise']),
                fmt(stats['mean_confidence'])
            ])
            
    print(f"Successfully wrote VC stats to {output_file}")

if __name__ == '__main__':
    main()
