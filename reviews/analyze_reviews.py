import csv
from collections import defaultdict
import os

def main():
    tpms_file = "../assignments/data/from-tpms/asplos27_scores.csv"
    combined_file = "../assignments/data/paper-reviewer-combined-scores.csv"
    reviews_file = "data/from-hotcrp/asplos27-apr-reviews.csv"
    output_file = "data/analysis/reviewer-stats.csv"

    # Load TPMS scores
    tpms_scores = {} # (paper_id, email) -> score
    if os.path.exists(tpms_file):
        with open(tpms_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    paper_id = row[0]
                    email = row[1]
                    score = float(row[2])
                    tpms_scores[(paper_id, email)] = score
    else:
        print(f"Warning: TPMS file not found at {tpms_file}")

    # Load Combined scores
    combined_scores = {} # (paper_id, email) -> score
    if os.path.exists(combined_file):
        with open(combined_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_id = row['paper']
                email = row['reviewer']
                score = float(row['score'])
                combined_scores[(paper_id, email)] = score
    else:
        print(f"Warning: Combined scores file not found at {combined_file}")

    pcinfo_file = "../assignments/data/from-hotcrp/asplos27-apr-pcinfo.csv"
    # Load PC info
    reviewer_roles = {} # email -> role ('pc-full', 'erc')
    if os.path.exists(pcinfo_file):
        with open(pcinfo_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                if 'pc-full' in tags:
                    reviewer_roles[email] = 'pc-full'
                elif 'erc' in tags:
                    reviewer_roles[email] = 'erc'
    else:
        print(f"Warning: PC info file not found at {pcinfo_file}")

    assignments_file = "../assignments/data/to-hotcrp/asplos27-apr-pc-assignments.csv"
    assigned_emails = set()
    if os.path.exists(assignments_file):
        with open(assignments_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                if email != 'all': # Skip the clearreview row
                    assigned_emails.add(email)
    else:
        print(f"Warning: Assignments file not found at {assignments_file}")

    # Accumulate stats and group by paper
    reviewer_stats = defaultdict(lambda: {
        'name': '',
        'reviews_count': 0,
        'tpms_scores': [],
        'combined_scores': [],
        'expertise_scores': [],
        'confidence_scores': [],
        'overall_scores': [],
        'papers': []
    })

    paper_scores = defaultdict(lambda: {
        'tpms': [],
        'combined': [],
        'expertise': [],
        'confidence': [],
        'overall': []
    })

    global_min = {'tpms': float('inf'), 'combined': float('inf'), 'expertise': float('inf'), 'confidence': float('inf'), 'overall': float('inf')}
    global_max = {'tpms': float('-inf'), 'combined': float('-inf'), 'expertise': float('-inf'), 'confidence': float('-inf'), 'overall': float('-inf')}

    reviews = []

    with open(reviews_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row['email']
            name = row['reviewername']
            paper = row['paper']
            
            reviews.append({
                'email': email,
                'paper': paper,
                'expertise': row.get('Reviewer expertise'),
                'confidence': row.get('Confidence'),
                'overall': row.get('Overall Strong ASPLOS paper')
            })

            stats = reviewer_stats[email]
            stats['name'] = name
            stats['reviews_count'] += 1
            stats['papers'].append(paper)
            
            # TPMS
            tpms_score = tpms_scores.get((paper, email))
            if tpms_score is not None:
                stats['tpms_scores'].append(tpms_score)
                paper_scores[paper]['tpms'].append(tpms_score)
                global_min['tpms'] = min(global_min['tpms'], tpms_score)
                global_max['tpms'] = max(global_max['tpms'], tpms_score)
            
            # Combined Score
            r_score = combined_scores.get((paper, email))
            if r_score is not None:
                stats['combined_scores'].append(r_score)
                paper_scores[paper]['combined'].append(r_score)
                global_min['combined'] = min(global_min['combined'], r_score)
                global_max['combined'] = max(global_max['combined'], r_score)
            
            # Expertise
            expertise = row.get('Reviewer expertise')
            if expertise:
                try:
                    val = int(expertise)
                    stats['expertise_scores'].append(val)
                    paper_scores[paper]['expertise'].append(val)
                    global_min['expertise'] = min(global_min['expertise'], val)
                    global_max['expertise'] = max(global_max['expertise'], val)
                except ValueError:
                    pass
                
            # Confidence
            confidence = row.get('Confidence')
            if confidence:
                try:
                    val = int(confidence)
                    stats['confidence_scores'].append(val)
                    paper_scores[paper]['confidence'].append(val)
                    global_min['confidence'] = min(global_min['confidence'], val)
                    global_max['confidence'] = max(global_max['confidence'], val)
                except ValueError:
                    pass
                
            # Overall
            overall = row.get('Overall Strong ASPLOS paper')
            if overall:
                try:
                    val = int(overall)
                    stats['overall_scores'].append(val)
                    paper_scores[paper]['overall'].append(val)
                    global_min['overall'] = min(global_min['overall'], val)
                    global_max['overall'] = max(global_max['overall'], val)
                except ValueError:
                    pass

    # Compute ranges
    ranges = {}
    for key in global_min:
        ranges[key] = global_max[key] - global_min[key] if global_max[key] > global_min[key] else 0.0

    # Compute paper averages
    paper_avgs = {}
    for paper, scores in paper_scores.items():
        paper_avgs[paper] = {
            'tpms': sum(scores['tpms']) / len(scores['tpms']) if scores['tpms'] else None,
            'combined': sum(scores['combined']) / len(scores['combined']) if scores['combined'] else None,
            'expertise': sum(scores['expertise']) / len(scores['expertise']) if scores['expertise'] else None,
            'confidence': sum(scores['confidence']) / len(scores['confidence']) if scores['confidence'] else None,
            'overall': sum(scores['overall']) / len(scores['overall']) if scores['overall'] else None
        }

    # Compute reviewer diffs
    reviewer_diffs = defaultdict(lambda: {
        'tpms': [],
        'combined': [],
        'expertise': [],
        'confidence': [],
        'overall': []
    })

    for review in reviews:
        email = review['email']
        paper = review['paper']
        
        paper_avg = paper_avgs.get(paper)
        if not paper_avg:
            continue
            
        # TPMS
        tpms_score = tpms_scores.get((paper, email))
        if tpms_score is not None and paper_avg['tpms'] is not None:
            diff = tpms_score - paper_avg['tpms']
            norm_diff = (diff / ranges['tpms'] * 100) if ranges['tpms'] > 0 else 0.0
            reviewer_diffs[email]['tpms'].append(norm_diff)
            
        # Combined
        r_score = combined_scores.get((paper, email))
        if r_score is not None and paper_avg['combined'] is not None:
            diff = r_score - paper_avg['combined']
            norm_diff = (diff / ranges['combined'] * 100) if ranges['combined'] > 0 else 0.0
            reviewer_diffs[email]['combined'].append(norm_diff)
            
        # Expertise
        if review['expertise']:
            try:
                val = int(review['expertise'])
                if paper_avg['expertise'] is not None:
                    diff = val - paper_avg['expertise']
                    norm_diff = (diff / ranges['expertise'] * 100) if ranges['expertise'] > 0 else 0.0
                    reviewer_diffs[email]['expertise'].append(norm_diff)
            except ValueError:
                pass
                
        # Confidence
        if review['confidence']:
            try:
                val = int(review['confidence'])
                if paper_avg['confidence'] is not None:
                    diff = val - paper_avg['confidence']
                    norm_diff = (diff / ranges['confidence'] * 100) if ranges['confidence'] > 0 else 0.0
                    reviewer_diffs[email]['confidence'].append(norm_diff)
            except ValueError:
                pass
                
        # Overall
        if review['overall']:
            try:
                val = int(review['overall'])
                if paper_avg['overall'] is not None:
                    diff = val - paper_avg['overall']
                    norm_diff = (diff / ranges['overall'] * 100) if ranges['overall'] > 0 else 0.0
                    reviewer_diffs[email]['overall'].append(norm_diff)
            except ValueError:
                pass

    # Compute averages and average diffs for all reviewers
    computed_stats = {}
    for email, stats in reviewer_stats.items():
        avg_tpms = sum(stats['tpms_scores']) / len(stats['tpms_scores']) if stats['tpms_scores'] else None
        avg_r_score = sum(stats['combined_scores']) / len(stats['combined_scores']) if stats['combined_scores'] else None
        avg_expertise = sum(stats['expertise_scores']) / len(stats['expertise_scores']) if stats['expertise_scores'] else None
        avg_confidence = sum(stats['confidence_scores']) / len(stats['confidence_scores']) if stats['confidence_scores'] else None
        avg_overall = sum(stats['overall_scores']) / len(stats['overall_scores']) if stats['overall_scores'] else None
        
        diffs = reviewer_diffs[email]
        avg_diff_tpms = sum(diffs['tpms']) / len(diffs['tpms']) if diffs['tpms'] else None
        avg_diff_r_score = sum(diffs['combined']) / len(diffs['combined']) if diffs['combined'] else None
        avg_diff_expertise = sum(diffs['expertise']) / len(diffs['expertise']) if diffs['expertise'] else None
        avg_diff_confidence = sum(diffs['confidence']) / len(diffs['confidence']) if diffs['confidence'] else None
        avg_diff_overall = sum(diffs['overall']) / len(diffs['overall']) if diffs['overall'] else None
        
        computed_stats[email] = {
            'name': stats['name'],
            'reviews_count': stats['reviews_count'],
            'avg_tpms': avg_tpms,
            'avg_r_score': avg_r_score,
            'avg_expertise': avg_expertise,
            'avg_confidence': avg_confidence,
            'avg_overall': avg_overall,
            'diff_tpms': avg_diff_tpms,
            'diff_r_score': avg_diff_r_score,
            'diff_expertise': avg_diff_expertise,
            'diff_confidence': avg_diff_confidence,
            'diff_overall': avg_diff_overall
        }

    def compute_ranks(stats_dict, key):
        values = [v[key] for v in stats_dict.values() if v[key] is not None]
        if not values:
            return {}
        
        unique_vals = sorted(list(set(values)))
        M = len(unique_vals)
        
        val_to_rank = {}
        for i, val in enumerate(unique_vals):
            if M > 1:
                rank = int(round(1 + 99 * i / (M - 1)))
            else:
                rank = 100
            val_to_rank[val] = rank
            
        return val_to_rank

    rank_tpms = compute_ranks(computed_stats, 'avg_tpms')
    rank_r_score = compute_ranks(computed_stats, 'avg_r_score')
    rank_expertise = compute_ranks(computed_stats, 'avg_expertise')
    rank_confidence = compute_ranks(computed_stats, 'avg_confidence')
    rank_overall = compute_ranks(computed_stats, 'avg_overall')

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'email', 'reviewername', 'reviews_completed', 
            'avg_tpms', 'rank_tpms', 'diff_tpms',
            'avg_r_score', 'rank_r_score', 'diff_r_score',
            'avg_expertise', 'rank_expertise', 'diff_expertise',
            'avg_confidence', 'rank_confidence', 'diff_confidence',
            'avg_overall', 'rank_overall', 'diff_overall'
        ])
        
        for email, stats in computed_stats.items():
            tpms = stats['avg_tpms']
            r_score = stats['avg_r_score']
            expertise = stats['avg_expertise']
            confidence = stats['avg_confidence']
            overall = stats['avg_overall']
            
            row = [
                email, stats['name'], stats['reviews_count'],
                f"{tpms:.2f}" if tpms is not None else '',
                rank_tpms.get(tpms, '') if tpms is not None else '',
                f"{stats['diff_tpms']:.2f}" if stats['diff_tpms'] is not None else '',
                f"{r_score:.2f}" if r_score is not None else '',
                rank_r_score.get(r_score, '') if r_score is not None else '',
                f"{stats['diff_r_score']:.2f}" if stats['diff_r_score'] is not None else '',
                f"{expertise:.2f}" if expertise is not None else '',
                rank_expertise.get(expertise, '') if expertise is not None else '',
                f"{stats['diff_expertise']:.2f}" if stats['diff_expertise'] is not None else '',
                f"{confidence:.2f}" if confidence is not None else '',
                rank_confidence.get(confidence, '') if confidence is not None else '',
                f"{stats['diff_confidence']:.2f}" if stats['diff_confidence'] is not None else '',
                f"{overall:.2f}" if overall is not None else '',
                rank_overall.get(overall, '') if overall is not None else '',
                f"{stats['diff_overall']:.2f}" if stats['diff_overall'] is not None else ''
            ]
            writer.writerow(row)
            
    print(f"Successfully wrote reviewer stats to {output_file}")

    # Compute and print histograms
    pc_counts = defaultdict(int)
    erc_counts = defaultdict(int)
    
    # Get full list of reviewers (assigned or completed)
    all_reviewers = assigned_emails.union(set(computed_stats.keys()))
    
    for email in all_reviewers:
        role = reviewer_roles.get(email)
        stats = computed_stats.get(email)
        count = stats['reviews_count'] if stats else 0
        
        if role == 'pc-full':
            pc_counts[count] += 1
        elif role == 'erc':
            erc_counts[count] += 1

    def print_histogram(name, counts):
        print(f"\nHistogram for {name}:")
        if not counts:
            print("  No data")
            return
            
        N = sum(counts.values())
        max_count = max(counts.keys()) if counts else 0
        
        # Calculate total missing reviews
        total_missing = sum(freq * (max_count - i) for i, freq in counts.items())
        
        print(f"  {'Reviews':<12} {'Count':<14} {'Cum %':<6} {'Miss %':<8}")
        
        cum_rev = 0
        cum_miss = 0
        for i in range(max_count + 1):
            freq = counts.get(i, 0)
            cum_rev += freq
            cum_miss += freq * (max_count - i)
            
            cum_rev_pct = int(round(cum_rev / N * 100)) if N > 0 else 0
            cum_miss_pct = int(round(cum_miss / total_missing * 100)) if total_missing > 0 else 100
            
            bar = '*' * freq
            print(f"  {i:2d} reviews:  {freq:3d} reviewers {cum_rev_pct:4d}% {cum_miss_pct:6d}%  {bar}")

    print_histogram("pc-full", pc_counts)
    print_histogram("erc", erc_counts)

if __name__ == '__main__':
    main()
