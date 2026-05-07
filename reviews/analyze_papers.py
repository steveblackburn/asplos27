import csv
from collections import defaultdict
import os

def main():
    combined_file = "../assignments/data/paper-reviewer-combined-scores.csv"
    reviews_file = "data/from-hotcrp/asplos27-apr-reviews.csv"
    output_file = "data/analysis/paper-stats.csv"

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

    # Load PC info to identify Vice Chairs
    pcinfo_file = "../assignments/data/from-hotcrp/asplos27-apr-pcinfo.csv"
    vc_emails = set()
    if os.path.exists(pcinfo_file):
        with open(pcinfo_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                if 'vc' in tags:
                    vc_emails.add(email)
    else:
        print(f"Warning: PC info file not found at {pcinfo_file}")

    # Accumulate stats by paper
    paper_stats = defaultdict(lambda: {
        'reviews_count': 0,
        'non_vc_reviews_count': 0,
        'combined_scores': [],
        'expertise_scores': [],
        'confidence_scores': [],
        'overall_data': [], # Store tuples (score, weight)
        'architecture_data': [],
        'pl_data': [],
        'os_data': [],
        'new_area_data': [],
        'asplos_data': [] # Store tuples (reviewer_avg, weight)
    })

    with open(reviews_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper = row['paper']
            email = row['email']
            
            stats = paper_stats[paper]
            stats['reviews_count'] += 1
            if email and email not in vc_emails:
                stats['non_vc_reviews_count'] += 1
            
            # Combined Score (Weight)
            r_score = combined_scores.get((paper, email))
            if r_score is not None:
                stats['combined_scores'].append(r_score)
            
            # Expertise
            expertise = row.get('Reviewer expertise')
            if expertise:
                try:
                    stats['expertise_scores'].append(int(expertise))
                except ValueError:
                    pass
                
            # Confidence
            confidence = row.get('Confidence')
            if confidence:
                try:
                    stats['confidence_scores'].append(int(confidence))
                except ValueError:
                    pass
                
            # Overall
            overall = row.get('Overall Strong ASPLOS paper')
            if overall:
                try:
                    val = int(overall)
                    stats['overall_data'].append((val, r_score))
                except ValueError:
                    pass
                
            # Advancement scores for ASPLOS calculation
            adv_scores = []
            
            # Advances computer architecture research
            arch = row.get('Advances computer architecture research')
            if arch:
                try:
                    val = int(arch)
                    stats['architecture_data'].append((val, r_score))
                    adv_scores.append(val)
                except ValueError:
                    pass
                
            # Advances programming languages research
            pl = row.get('Advances programming languages research')
            if pl:
                try:
                    val = int(pl)
                    stats['pl_data'].append((val, r_score))
                    adv_scores.append(val)
                except ValueError:
                    pass
                
            # Advances operating systems research
            os_score = row.get('Advances operating systems research')
            if os_score:
                try:
                    val = int(os_score)
                    stats['os_data'].append((val, r_score))
                    adv_scores.append(val)
                except ValueError:
                    pass
                
            # Introduces new area
            new_area = row.get('Introduces new area')
            if new_area:
                try:
                    val = int(new_area)
                    stats['new_area_data'].append((val, r_score))
                    adv_scores.append(val)
                except ValueError:
                    pass
                    
            # Calculate reviewer ASPLOS score (average of best two)
            if adv_scores:
                best_two = sorted(adv_scores, reverse=True)[:2]
                reviewer_asplos = sum(best_two) / len(best_two)
                stats['asplos_data'].append((reviewer_asplos, r_score))

    def compute_weighted_avg(data):
        # data is a list of tuples (score, weight)
        # filter out None weights
        valid_data = [(s, w) for s, w in data if w is not None]
        if not valid_data:
            return None
        total_weight = sum(w for s, w in valid_data)
        if total_weight == 0:
            return None
        return sum(s * w for s, w in valid_data) / total_weight

    def compute_avg(data):
        # data is a list of tuples (score, weight) or just scores
        # if tuples, extract scores
        if not data:
            return None
        if isinstance(data[0], tuple):
            scores = [s for s, w in data]
        else:
            scores = data
        return sum(scores) / len(scores) if scores else None

    # Compute averages for all papers first
    computed_stats = {}
    for paper in sorted(paper_stats.keys(), key=int):
        stats = paper_stats[paper]
        
        avg_combined = sum(stats['combined_scores']) / len(stats['combined_scores']) if stats['combined_scores'] else None
        avg_expertise = sum(stats['expertise_scores']) / len(stats['expertise_scores']) if stats['expertise_scores'] else None
        avg_confidence = sum(stats['confidence_scores']) / len(stats['confidence_scores']) if stats['confidence_scores'] else None
        
        avg_overall = compute_avg(stats['overall_data'])
        wavg_overall = compute_weighted_avg(stats['overall_data'])
        
        avg_arch = compute_avg(stats['architecture_data'])
        wavg_arch = compute_weighted_avg(stats['architecture_data'])
        
        avg_pl = compute_avg(stats['pl_data'])
        wavg_pl = compute_weighted_avg(stats['pl_data'])
        
        avg_os = compute_avg(stats['os_data'])
        wavg_os = compute_weighted_avg(stats['os_data'])
        
        avg_new_area = compute_avg(stats['new_area_data'])
        wavg_new_area = compute_weighted_avg(stats['new_area_data'])
        
        avg_asplos = compute_avg(stats['asplos_data'])
        wavg_asplos = compute_weighted_avg(stats['asplos_data'])
        
        computed_stats[paper] = {
            'reviews_count': stats['reviews_count'],
            'non_vc_reviews_count': stats['non_vc_reviews_count'],
            'avg_combined': avg_combined,
            'avg_expertise': avg_expertise,
            'avg_confidence': avg_confidence,
            'avg_overall': avg_overall,
            'wavg_overall': wavg_overall,
            'avg_arch': avg_arch,
            'wavg_arch': wavg_arch,
            'avg_pl': avg_pl,
            'wavg_pl': wavg_pl,
            'avg_os': avg_os,
            'wavg_os': wavg_os,
            'avg_new_area': avg_new_area,
            'wavg_new_area': wavg_new_area,
            'avg_asplos': avg_asplos,
            'wavg_asplos': wavg_asplos
        }

    def compute_percentiles(stats_dict, key):
        values = [v[key] for v in stats_dict.values() if v[key] is not None]
        if not values:
            return {}
        
        total_papers = len(values)
        val_to_pct = {}
        
        for val in set(values):
            # Count how many papers have value < current val, and how many are equal
            count_lt = sum(1 for v in values if v < val)
            count_eq = sum(1 for v in values if v == val)
            midpoint = count_lt + (count_eq + 1) / 2
            pct = int(round(midpoint / total_papers * 100))
            if pct == 0:
                pct = 1
            val_to_pct[val] = pct
            
        return val_to_pct

    rank_overall = compute_percentiles(computed_stats, 'wavg_overall')
    rank_asplos = compute_percentiles(computed_stats, 'wavg_asplos')

    # Compute pct for all papers
    for paper, stats in computed_stats.items():
        w_overall = stats['wavg_overall']
        w_asplos = stats['wavg_asplos']
        
        r_overall = rank_overall.get(w_overall) if w_overall is not None else None
        r_asplos = rank_asplos.get(w_asplos) if w_asplos is not None else None
        
        pct = None
        if r_overall is not None and r_asplos is not None:
            pct = (2/3) * r_overall + (1/3) * r_asplos
        
        stats['pct'] = pct

    # Compute rank based on pct
    rank_by_pct = compute_percentiles(computed_stats, 'pct')

    # Build mapping from rank to scores
    rank_to_scores = defaultdict(list)
    for pct_val, rank in rank_by_pct.items():
        rank_to_scores[rank].append(pct_val)

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'paper', 'pct', 'rank', 'reviews_completed', 'avg_reviewer_score', 
            'avg_expertise', 'avg_confidence', 
            'avg_overall', 'wavg_overall', 'rank_overall',
            'avg_architecture', 'wavg_architecture',
            'avg_pl', 'wavg_pl',
            'avg_os', 'wavg_os',
            'avg_new_area', 'wavg_new_area',
            'avg_asplos', 'wavg_asplos', 'rank_asplos'
        ])
        
        for paper in sorted(computed_stats.keys(), key=int):
            stats = computed_stats[paper]
            
            pct = stats['pct']
            w_overall = stats['wavg_overall']
            w_asplos = stats['wavg_asplos']
            
            r_overall = rank_overall.get(w_overall) if w_overall is not None else ''
            r_asplos = rank_asplos.get(w_asplos) if w_asplos is not None else ''
            
            final_rank = rank_by_pct.get(pct, '') if pct is not None else ''
            
            row_data = [
                paper,
                f"{pct:.2f}" if pct is not None else '',
                final_rank,
                stats['reviews_count'],
                f"{stats['avg_combined']:.2f}" if stats['avg_combined'] is not None else '',
                f"{stats['avg_expertise']:.2f}" if stats['avg_expertise'] is not None else '',
                f"{stats['avg_confidence']:.2f}" if stats['avg_confidence'] is not None else '',
                f"{stats['avg_overall']:.2f}" if stats['avg_overall'] is not None else '',
                f"{stats['wavg_overall']:.2f}" if stats['wavg_overall'] is not None else '',
                r_overall,
                f"{stats['avg_arch']:.2f}" if stats['avg_arch'] is not None else '',
                f"{stats['wavg_arch']:.2f}" if stats['wavg_arch'] is not None else '',
                f"{stats['avg_pl']:.2f}" if stats['avg_pl'] is not None else '',
                f"{stats['wavg_pl']:.2f}" if stats['wavg_pl'] is not None else '',
                f"{stats['avg_os']:.2f}" if stats['avg_os'] is not None else '',
                f"{stats['wavg_os']:.2f}" if stats['wavg_os'] is not None else '',
                f"{stats['avg_new_area']:.2f}" if stats['avg_new_area'] is not None else '',
                f"{stats['wavg_new_area']:.2f}" if stats['wavg_new_area'] is not None else '',
                f"{stats['avg_asplos']:.2f}" if stats['avg_asplos'] is not None else '',
                f"{stats['wavg_asplos']:.2f}" if stats['wavg_asplos'] is not None else '',
                r_asplos
            ]
            writer.writerow(row_data)
            
    print(f"Successfully wrote paper stats to {output_file}")

    # Write HotCRP tags file
    ranks_output_file = "data/to-hotcrp/asplos27-apr-paperranks.csv"
    os.makedirs(os.path.dirname(ranks_output_file), exist_ok=True)
    print(f"Writing paper ranks tags to {ranks_output_file}")
    
    bucket_counts = defaultdict(int)
    rank_distribution = defaultdict(int)
    total_papers = 0
    
    with open(ranks_output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['paper', 'action', 'tag', 'tag_value'])
        writer.writerow(['all', 'cleartag', 'sc_reject', ''])
        writer.writerow(['all', 'cleartag', 'sc_advance', ''])
        writer.writerow(['all', 'cleartag', 'sc_adjudicate', ''])
        writer.writerow(['all', 'cleartag', '~~blue', ''])
        writer.writerow(['all', 'cleartag', '~~yellow', ''])
        writer.writerow(['all', 'cleartag', '~~gray', ''])
        writer.writerow(['all', 'cleartag', '~~:thinking:', ''])
        
        for paper in sorted(computed_stats.keys(), key=int):
            stats = computed_stats[paper]
            pct = stats['pct']
            
            if stats['reviews_count'] == 0:
                continue
                
            final_rank = rank_by_pct.get(pct) if pct is not None else None
            if final_rank is not None:
                total_papers += 1
                rank_distribution[final_rank] += 1
                
                # Write pctl tag
                writer.writerow([paper, 'tag', 'pctl', final_rank])
                
                # Determine bucket tag
                if final_rank >= 81:
                    bucket_tag = 'sc_advance'
                elif final_rank >= 61:
                    bucket_tag = 'sc_adjudicate'
                else:
                    bucket_tag = 'sc_reject'
                    

                bucket_counts[bucket_tag] += 1
                writer.writerow([paper, 'tag', bucket_tag, ''])
                
                # Add color tags for papers with >= 3 non-VC reviews
                if stats['non_vc_reviews_count'] >= 3:
                    if bucket_tag == 'sc_advance':
                        color_tag = '~~blue'
                    elif bucket_tag == 'sc_adjudicate':
                        color_tag = '~~yellow'
                    else:
                        color_tag = '~~gray'
                    writer.writerow([paper, 'tag', color_tag, ''])
                
                # Check for large score difference
                overall_scores = [s for s, w in paper_stats[paper]['overall_data']]
                if overall_scores:
                    max_score = max(overall_scores)
                    min_score = min(overall_scores)
                    if max_score - min_score >= 3:
                        writer.writerow([paper, 'tag', '~~:thinking:', ''])
                
    print(f"Successfully wrote paper ranks tags to {ranks_output_file}")

    # Output summary statistics
    print("\nSummary Statistics:")
    print(f"Total papers scored: {total_papers}")
    for bucket in ['sc_advance', 'sc_adjudicate', 'sc_reject']:
        count = bucket_counts[bucket]
        pct_val = (count / total_papers * 100) if total_papers > 0 else 0
        print(f"  {bucket:<15}: {count:3d} papers ({pct_val:.1f}%)")

    def print_range_histogram(title, start, end, distribution, rank_to_scores):
        print(f"\nHistogram for {title} (range {start}-{end}):")
        for r in range(start, end + 1):
            count = distribution.get(r, 0)
            scores = rank_to_scores.get(r, [])
            score_str = ""
            if scores:
                min_score = min(scores)
                max_score = max(scores)
                if min_score == max_score:
                    score_str = f"(Score {min_score:.2f})"
                else:
                    score_str = f"(Score {min_score:.2f}-{max_score:.2f})"
            bar = '*' * count
            print(f"  Rank {r:2d} {score_str:<20}: {count:3d} papers {bar}")

    print_range_histogram("Boundary 60", 55, 65, rank_distribution, rank_to_scores)
    print_range_histogram("Boundary 80", 75, 85, rank_distribution, rank_to_scores)

if __name__ == '__main__':
    main()
