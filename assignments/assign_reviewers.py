import argparse
import collections
import csv
import os
from ortools.linear_solver import pywraplp
import yaml

def main():
    parser = argparse.ArgumentParser(description="Assign reviewers to papers using OR-Tools.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix")
    parser.add_argument("--scores", default="data/paper-reviewer-combined-scores.csv", help="Combined scores CSV")
    parser.add_argument("--stats-file", default="data/analysis/paper-stats-pc.csv", help="PC paper stats CSV (scores list)")
    parser.add_argument("--stats-file-vc", default="data/analysis/paper-stats-vc.csv", help="VC paper stats CSV (scores list)")
    parser.add_argument("--constraints", default="constraints.yaml", help="Constraints YAML file")
    parser.add_argument("--demographics", default="data/from-sheets/pc-demographics.csv", help="PC demographics CSV")
    parser.add_argument("--pcinfo", default="data/from-hotcrp/asplos27-apr-pcinfo.csv", help="PC info CSV")
    parser.add_argument("--output", default="data/pc-assignments.csv", help="Output CSV file")
    parser.add_argument("--tpms-scores", default="data/paper-reviewer-scaled-tpms.csv", help="TPMS scores CSV file")
    parser.add_argument("--topic-scores", default="data/paper-reviewer-scaled-topic.csv", help="Topic scores CSV file")
    parser.add_argument("--objective", default="max_relative", choices=["max_total", "max_relative"], help="Objective function: max_total (maximize total score), max_relative (maximize fraction of optimal unconstrained score)")
    parser.add_argument("--hotcrp-output", default="data/to-hotcrp/asplos27-apr-pc-assignments.csv", help="HotCRP assignments CSV output file")
    parser.add_argument("--hotcrp-vc-output", default="data/to-hotcrp/asplos27-apr-vc-assignments.csv", help="HotCRP VC assignments CSV output file")
    parser.add_argument("--hotcrp-pref-output", default="data/to-hotcrp/asplos27-apr-preferences.csv", help="HotCRP preferences CSV output file")
    parser.add_argument("--hotcrp-tags-output", default="data/to-hotcrp/asplos27-apr-papertags.csv", help="HotCRP paper tags CSV output file")
    parser.add_argument("--min-relative-score", type=float, default=0.0, help="Minimum relative score fraction for each paper (e.g., 0.5)")
    args = parser.parse_args()

    prefix = args.prefix
    scores_file = args.scores
    constraints_file = args.constraints
    demographics_file = args.demographics
    pcinfo_file = args.pcinfo
    output_file = args.output
    tpms_scores_file = args.tpms_scores
    topic_scores_file = args.topic_scores

    # 1. Read constraints
    print(f"Reading constraints from {constraints_file}")
    try:
        with open(constraints_file, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Constraints file not found: {constraints_file}")
        return

    reviews_per_paper = config.get('reviews_per_paper', 22)
    max_erc_reviews_per_paper = config.get('max_erc_reviews_per_paper', 7)
    min_senior_reviewers_per_paper = config.get('min_senior_reviewers_per_paper', 1)
    vice_chairs_per_paper = config.get('vice_chairs_per_paper', 1)
    reviewer_limits = config.get('reviewer_limits', {})
    erc_load_factor = config.get('erc_load_factor', 0.333)
    
    # Read paper stats for optimal scores
    stats_file = args.stats_file
    stats_file_vc = args.stats_file_vc
    paper_pc_scores_list = {}
    paper_vc_scores_list = {}
    
    print(f"Reading PC paper stats from {stats_file}")
    try:
        with open(stats_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                paper = row[0]
                scores_list = [float(s) for s in row[1:]]
                paper_pc_scores_list[paper] = scores_list
    except FileNotFoundError:
        print(f"Warning: Stats file not found: {stats_file}. Will compute from assignment scores.")

    print(f"Reading VC paper stats from {stats_file_vc}")
    try:
        with open(stats_file_vc, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                paper = row[0]
                scores_list = [float(s) for s in row[1:]]
                paper_vc_scores_list[paper] = scores_list
    except FileNotFoundError:
        print(f"Warning: Stats file not found: {stats_file_vc}. Will compute from assignment scores.")

    # 2. Read pcinfo for tags
    print(f"Reading PC info from {pcinfo_file}")
    full_reviewers = set()
    erc_reviewers = set()
    vc_reviewers = set()
    email_to_info = {}
    try:
        with open(pcinfo_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                given_name = row.get('given_name', '')
                family_name = row.get('family_name', '')
                
                role = ''
                if 'pc-full' in tags:
                    full_reviewers.add(email)
                    role = 'p'
                elif 'erc' in tags:
                    erc_reviewers.add(email)
                    role = 'e'
                
                if 'vc' in tags:
                    vc_reviewers.add(email)
                    role = 'v'
                    
                if email:
                    email_to_info[email] = {
                        'name': f"{given_name} {family_name}".strip(),
                        'role': role
                    }
    except FileNotFoundError:
        print(f"Error: PC info file not found: {pcinfo_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in PC info file: {e}")
        return

    # 3. Read demographics for seniority
    print(f"Reading demographics from {demographics_file}")
    senior_reviewers = set()
    try:
        with open(demographics_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 7:
                    email = row[2].strip()
                    field_val = row[5].strip().lower()
                    field = ''
                    if 'acad' in field_val:
                        field = 'A'
                    elif 'ind' in field_val:
                        field = 'I'
                    elif 'gov' in field_val:
                        field = 'G'
                    elif field_val:
                        field = field_val[0].upper()
                        
                    seniority = row[6].strip()
                    
                    if seniority == 'S':
                        senior_reviewers.add(email)
                        
                    if email in email_to_info:
                        email_to_info[email]['seniority'] = seniority
                        email_to_info[email]['field'] = field
    except FileNotFoundError:
        print(f"Error: Demographics file not found: {demographics_file}")
        return

    # 4. Read scores and identify valid pairs
    print(f"Reading scores from {scores_file}")
    scores = {}
    all_scores = {}
    papers = set()
    reviewers = set()
    valid_pairs = set()

    try:
        with open(scores_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score = float(row['score'])

                papers.add(paper)
                reviewers.add(reviewer)
                all_scores[(paper, reviewer)] = score

                # Consider full, erc, and vc reviewers
                if reviewer in full_reviewers or reviewer in erc_reviewers or reviewer in vc_reviewers:
                    if score > 0: # Exclude conflicts
                        scores[(paper, reviewer)] = score
                        valid_pairs.add((paper, reviewer))
    except FileNotFoundError:
        print(f"Error: Scores file not found: {scores_file}")
        return
    except KeyError as e:
        print(f"Error: Missing expected column in scores file: {e}")
        return

    print(f"Found {len(papers)} papers and {len(reviewers)} total reviewers in scores file.")
    print(f"Eligible reviewers: Full={len(full_reviewers)}, ERC={len(erc_reviewers)}")

    # Read TPMS scores (no header)
    tpms_scores_dict = {}
    try:
        print(f"Reading TPMS scores from {tpms_scores_file}")
        with open(tpms_scores_file, 'r', newline='', encoding='utf-8') as f:
            sample = f.read(1024)
            f.seek(0)
            if sample.startswith('paper,reviewer'):
                reader = csv.DictReader(f)
                for row in reader:
                    tpms_scores_dict[(row['paper'], row['reviewer'])] = float(row['score'])
            else:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        tpms_scores_dict[(row[0], row[1])] = float(row[2])
    except FileNotFoundError:
        print(f"Warning: TPMS scores file not found: {tpms_scores_file}")

    # Read topic scores (with header)
    topic_scores_dict = {}
    try:
        print(f"Reading topic scores from {topic_scores_file}")
        with open(topic_scores_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic_scores_dict[(row['paper'], row['reviewer'])] = float(row['score'])
    except FileNotFoundError:
        print(f"Warning: Topic scores file not found: {topic_scores_file}")
        
    # Pre-compute all TPMS and Topic scores per paper for stats
    paper_all_tpms = collections.defaultdict(list)
    try:
        with open('data/paper-reviewer-scaled-tpms.csv', 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_all_tpms[row['paper']].append(float(row['score']))
    except FileNotFoundError:
        print("Warning: Scaled TPMS scores file not found: data/paper-reviewer-scaled-tpms.csv")
        
    paper_all_topic = collections.defaultdict(list)
    try:
        with open('data/paper-reviewer-scaled-topic.csv', 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper_all_topic[row['paper']].append(float(row['score']))
    except FileNotFoundError:
        print("Warning: Scaled Topic scores file not found: data/paper-reviewer-scaled-topic.csv")
        
    print(f"Valid pairs: {len(valid_pairs)} (after filtering for eligible reviewers and non-zero scores)")

    # Calculate unconstrained optimal scores for all papers
    optimal_scores = {}
    for paper in papers:
        scores_list = paper_pc_scores_list.get(paper, [])
        if scores_list:
            top_n_scores = scores_list[:reviews_per_paper]
            optimal_scores[paper] = sum(top_n_scores) if top_n_scores else 1.0
        else:
            all_paper_scores = [scores.get((paper, r), 0.0) for r in reviewers if (paper, r) in valid_pairs]
            all_paper_scores.sort(reverse=True)
            top_n_scores = all_paper_scores[:reviews_per_paper]
            optimal_scores[paper] = sum(top_n_scores) if top_n_scores else 1.0
            
        if optimal_scores[paper] == 0:
            optimal_scores[paper] = 1.0

    # 5. Setup Solver
    # Use SCIP as it is a good general purpose MIP solver included in OR-Tools
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Error: SCIP solver not available.")
        return

    # Variables
    x = {}
    for paper in papers:
        for reviewer in reviewers:
            if (paper, reviewer) in valid_pairs and (reviewer in full_reviewers or reviewer in erc_reviewers):
                x[(paper, reviewer)] = solver.BoolVar(f'x_{paper}_{reviewer}')

    # Objective
    objective = solver.Objective()
    if args.objective == "max_relative":
        print("Objective: Maximize relative score (fraction of optimal)")
        for (paper, reviewer), var in x.items():
            coeff = scores[(paper, reviewer)] / optimal_scores[paper]
            objective.SetCoefficient(var, coeff)
    else:
        print("Objective: Maximize total score")
        for (paper, reviewer), var in x.items():
            objective.SetCoefficient(var, scores[(paper, reviewer)])
    objective.SetMaximization()

    # Constraints
    # a. Reviews per paper
    for paper in papers:
        constraint = solver.Constraint(reviews_per_paper, reviews_per_paper)
        for reviewer in reviewers:
            if (paper, reviewer) in x:
                constraint.SetCoefficient(x[(paper, reviewer)], 1)

    # b. Max ERC per paper
    for paper in papers:
        constraint = solver.Constraint(0, max_erc_reviews_per_paper)
        for reviewer in erc_reviewers:
            if (paper, reviewer) in x:
                constraint.SetCoefficient(x[(paper, reviewer)], 1)

    # c. Min Senior per paper
    for paper in papers:
        constraint = solver.Constraint(min_senior_reviewers_per_paper, solver.infinity())
        for reviewer in senior_reviewers:
            if (paper, reviewer) in x:
                constraint.SetCoefficient(x[(paper, reviewer)], 1)

    # d. Minimum quality per paper
    if args.min_relative_score > 0:
        print(f"Adding minimum quality constraint: fraction >= {args.min_relative_score}")
        for paper in papers:
            # sum(x[p,r] * scores[p,r]) >= min_relative_score * optimal_scores[p]
            min_score = args.min_relative_score * optimal_scores[paper]
            constraint = solver.Constraint(min_score, solver.infinity())
            for r in reviewers:
                if (paper, r) in x:
                    constraint.SetCoefficient(x[(paper, r)], scores[(paper, r)])

    # d. Reviewer load bounds
    num_papers = len(papers)
    num_full = len(full_reviewers)
    num_erc = len(erc_reviewers)

    total_reviews = num_papers * reviews_per_paper
    max_erc_possible = num_papers * max_erc_reviews_per_paper

    # Solve for target loads
    target_full_load = total_reviews / (num_full + erc_load_factor * num_erc) if (num_full + erc_load_factor * num_erc) > 0 else 0
    target_erc_load = erc_load_factor * target_full_load

    # Cap ERC load if it exceeds max possible
    if num_erc * target_erc_load > max_erc_possible:
        target_erc_load = max_erc_possible / num_erc if num_erc > 0 else 0
        target_full_load = (total_reviews - num_erc * target_erc_load) / num_full if num_full > 0 else 0

    full_min_l = int(target_full_load)
    full_max_l = full_min_l + 1

    erc_min_l = int(target_erc_load)
    erc_max_l = erc_min_l + 1

    print(f"Calculated Load limits:")
    print(f"  Full PC: {full_min_l} to {full_max_l}")
    print(f"  ERC: {erc_min_l} to {erc_max_l}")

    for reviewer in reviewers:
        if reviewer in full_reviewers:
            min_l = full_min_l
            max_l = full_max_l
        elif reviewer in erc_reviewers:
            min_l = erc_min_l
            max_l = erc_max_l
        else:
            continue # Skip reviewers not in either list (they won't have valid pairs anyway)

        # Apply ad hoc limits
        if reviewer in reviewer_limits:
            limit = reviewer_limits[reviewer]
            max_l = min(max_l, limit)
            # If limit is less than min_l, we reduce min_l too
            min_l = min(min_l, max_l)

        constraint = solver.Constraint(min_l, max_l)
        for paper in papers:
            if (paper, reviewer) in x:
                constraint.SetCoefficient(x[(paper, reviewer)], 1)

    # Solve
    print("Solving...")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        status_str = "OPTIMAL" if status == pywraplp.Solver.OPTIMAL else "FEASIBLE"
        print(f"Solution found! Status: {status_str}")
        print(f"Total score: {solver.Objective().Value()}")

        # Write output
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        print(f"Writing assignments to {output_file}")
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'reviewer'])
            # Sort papers numerically
            sorted_papers = sorted(list(papers), key=int)
            for paper in sorted_papers:
                # Sort reviewers by email for consistency
                for reviewer in sorted(list(reviewers)):
                    if (paper, reviewer) in x:
                        if x[(paper, reviewer)].solution_value() > 0.5:
                            writer.writerow([paper, reviewer])

        # Write HotCRP formatted assignments
        hotcrp_output_file = args.hotcrp_output
        hotcrp_output_dir = os.path.dirname(hotcrp_output_file)
        if hotcrp_output_dir and not os.path.exists(hotcrp_output_dir):
            os.makedirs(hotcrp_output_dir, exist_ok=True)
            
        print(f"Writing HotCRP assignments to {hotcrp_output_file}")
        with open(hotcrp_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'action', 'email', 'round'])
            writer.writerow(['all', 'clearreview', 'all', 'RR'])
            for paper in sorted_papers:
                for reviewer in sorted(list(reviewers)):
                    if (paper, reviewer) in x:
                        if x[(paper, reviewer)].solution_value() > 0.5:
                            writer.writerow([paper, 'primary', reviewer, 'RR'])

        # Write HotCRP preferences
        pref_output_file = args.hotcrp_pref_output
        pref_output_dir = os.path.dirname(pref_output_file)
        if pref_output_dir and not os.path.exists(pref_output_dir):
            os.makedirs(pref_output_dir, exist_ok=True)
            
        print(f"Writing HotCRP preferences to {pref_output_file}")
        with open(pref_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'action', 'email', 'preference'])
            for paper in sorted_papers:
                for reviewer in sorted(list(reviewers)):
                    score = all_scores.get((paper, reviewer), 0.0)
                    if score > 0:
                        writer.writerow([paper, 'pref', reviewer, int(score)])
                    else:
                        writer.writerow([paper, 'pref', reviewer, -100])


        # Write stats
        stats_file = "data/analysis/pc-assignment-stats.csv"
        print(f"Writing assignment stats to {stats_file}")
        stats_rows = []
        for paper in sorted_papers:
            scores_list = paper_pc_scores_list.get(paper, [])
            if scores_list:
                top_n_scores = scores_list[:reviews_per_paper]
                optimal_score = sum(top_n_scores) / len(top_n_scores) if top_n_scores else 0
            else:
                all_paper_scores = [scores[(paper, r)] for r in reviewers if (paper, r) in valid_pairs]
                all_paper_scores.sort(reverse=True)
                top_n_scores = all_paper_scores[:reviews_per_paper]
                optimal_score = sum(top_n_scores) / len(top_n_scores) if top_n_scores else 0
            
            assigned_scores = []
            for reviewer in reviewers:
                if (paper, reviewer) in x:
                    if x[(paper, reviewer)].solution_value() > 0.5:
                        assigned_scores.append(scores[(paper, reviewer)])
            
            actual_score = sum(assigned_scores) / len(assigned_scores) if assigned_scores else 0
            
            fraction = actual_score / optimal_score if optimal_score > 0 else 0
            
            # Get 3rd best TPMS and Topic scores
            tpms_vals = sorted(paper_all_tpms.get(paper, []), reverse=True)
            topic_vals = sorted(paper_all_topic.get(paper, []), reverse=True)
            
            tpms_3rd = tpms_vals[2] if len(tpms_vals) >= 3 else 0.0
            topic_3rd = topic_vals[2] if len(topic_vals) >= 3 else 0.0
            
            stats_rows.append([paper, actual_score, optimal_score, fraction, tpms_3rd, topic_3rd])
            
        # Sort by actual score ascending (worst to best)
        stats_rows.sort(key=lambda x: x[1])
        
        # Generate paper tags based on deciles of assignment quality
        tag_rows = []
        num_papers = len(stats_rows)
        for i, row in enumerate(stats_rows):
            paper = row[0]
            decile = int(i * 10 / num_papers) + 1
            tag_rows.append([paper, 'tag', 'aq', decile])
            
            tpms_val = row[4]
            tpms_tag_value = max(1, round(tpms_val * 100))
            tag_rows.append([paper, 'tag', 'tpms', tpms_tag_value])
        
        # Calculate average relative score
        avg_relative_score = sum(row[3] for row in stats_rows) / len(stats_rows) if stats_rows else 0
        print(f"Average relative score: {avg_relative_score:.4f}")
        
        with open(stats_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'actual_score', 'optimal_score', 'fraction', 'tpms_3rd', 'topic_3rd'])
            for row in stats_rows:
                writer.writerow([row[0], f"{row[1]:.2f}", f"{row[2]:.2f}", f"{row[3]:.3f}", f"{row[4]:.3f}", f"{row[5]:.3f}"])
        
        # Write HotCRP paper tags
        tags_output_file = args.hotcrp_tags_output
        tags_output_dir = os.path.dirname(tags_output_file)
        if tags_output_dir and not os.path.exists(tags_output_dir):
            os.makedirs(tags_output_dir, exist_ok=True)
            
        print(f"Writing HotCRP paper tags to {tags_output_file}")
        with open(tags_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'action', 'tag', 'tag_value'])
            for row in tag_rows:
                writer.writerow(row)
                
        print("Done.")
    else:
        print(f"Error: Solver failed with status {status}")
    # --- Vice Chair Assignment ---
    print("\n--- Vice Chair Assignment ---")
    solver_vc = pywraplp.Solver.CreateSolver('SCIP')
    if not solver_vc:
        print("Error: SCIP solver not available for VC assignment.")
        return

    # Variables for VCs
    y = {}
    for paper in papers:
        for reviewer in vc_reviewers:
            if (paper, reviewer) in valid_pairs:
                y[(paper, reviewer)] = solver_vc.BoolVar(f'y_{paper}_{reviewer}')

    print(f"Created {len(y)} variables for VC assignment.")

    # Load VC optimal scores
    optimal_vc_scores = {}
    for paper in papers:
        scores_list = paper_vc_scores_list.get(paper, [])
        if scores_list:
            top_n_scores = scores_list[:vice_chairs_per_paper]
            optimal_vc_scores[paper] = sum(top_n_scores) if top_n_scores else 1.0
        else:
            # Fallback
            all_paper_scores = [scores.get((paper, r), 0.0) for r in vc_reviewers if (paper, r) in valid_pairs]
            all_paper_scores.sort(reverse=True)
            top_n_scores = all_paper_scores[:vice_chairs_per_paper]
            optimal_vc_scores[paper] = sum(top_n_scores) if top_n_scores else 1.0
            
        if optimal_vc_scores[paper] == 0:
            optimal_vc_scores[paper] = 1.0

    # Objective for VCs
    objective_vc = solver_vc.Objective()
    if args.objective == "max_relative":
        print("VC Objective: Maximize relative score")
        for (paper, reviewer), var in y.items():
            coeff = scores[(paper, reviewer)] / optimal_vc_scores[paper]
            objective_vc.SetCoefficient(var, coeff)
    else:
        print("VC Objective: Maximize total score")
        for (paper, reviewer), var in y.items():
            objective_vc.SetCoefficient(var, scores[(paper, reviewer)])
    objective_vc.SetMaximization()

    # Constraints for VCs
    # 1. Reviews per paper = vice_chairs_per_paper
    for paper in papers:
        constraint = solver_vc.Constraint(vice_chairs_per_paper, vice_chairs_per_paper)
        for reviewer in vc_reviewers:
            if (paper, reviewer) in y:
                constraint.SetCoefficient(y[(paper, reviewer)], 1)

    # 2. Even distribution of load among VCs
    num_papers = len(papers)
    num_vcs = len(vc_reviewers)
    if num_vcs > 0:
        target_reviews = (num_papers * vice_chairs_per_paper) / num_vcs
        lower_bound = int(target_reviews)
        upper_bound = lower_bound + 1
        print(f"VC Load limits: {lower_bound} to {upper_bound}")
        
        for reviewer in vc_reviewers:
            constraint = solver_vc.Constraint(lower_bound, upper_bound)
            for paper in papers:
                if (paper, reviewer) in y:
                    constraint.SetCoefficient(y[(paper, reviewer)], 1)

    # Solve VC assignment
    print("Solving VC assignment...")
    status_vc = solver_vc.Solve()

    meta_assignments = set()
    if status_vc == pywraplp.Solver.OPTIMAL or status_vc == pywraplp.Solver.FEASIBLE:
        status_str = "OPTIMAL" if status_vc == pywraplp.Solver.OPTIMAL else "FEASIBLE"
        print(f"VC Solution found! Status: {status_str}")
        print(f"VC Total score: {solver_vc.Objective().Value()}")

        # Write VC assignments to HotCRP format
        hotcrp_vc_output_file = args.hotcrp_vc_output
        vc_output_dir = os.path.dirname(hotcrp_vc_output_file)
        if vc_output_dir and not os.path.exists(vc_output_dir):
            os.makedirs(vc_output_dir, exist_ok=True)

        print(f"Writing VC assignments to {hotcrp_vc_output_file}")
        with open(hotcrp_vc_output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'action', 'email'])
            for paper in sorted(list(papers), key=int):
                for reviewer in vc_reviewers:
                    if (paper, reviewer) in y:
                        if y[(paper, reviewer)].solution_value() > 0.5:
                            writer.writerow([paper, 'meta', reviewer])
                            meta_assignments.add((paper, reviewer))
    else:
        print(f"Error: VC Solver failed with status {status_vc}")

    # Write context file
    context_file = "data/analysis/pc-assignment-context.csv"
    print(f"Writing assignment context to {context_file}")
    context_rows = []
    for paper in papers:
        for reviewer in reviewers:
            assigned = "O" if (paper, reviewer) in x and x[(paper, reviewer)].solution_value() > 0.5 else "X"
            comb_score = scores.get((paper, reviewer), 0.0)
            tpms_val = tpms_scores_dict.get((paper, reviewer), "")
            tpms_score = f"{tpms_val:.2f}" if tpms_val != "" else ""
            topic_score = f"{topic_scores_dict.get((paper, reviewer), 0.0):.2f}"
            
            info = email_to_info.get(reviewer, {'name': '', 'role': '', 'seniority': 'J', 'field': ''})
            name = info['name']
            role = info['role']
            seniority = info.get('seniority', 'J')
            field = info.get('field', '')
            
            # Check for meta assignment
            if (paper, reviewer) in meta_assignments and role == 'v':
                assigned = "M"
                
            context_rows.append([paper, assigned, role, comb_score, tpms_score, topic_score, seniority, field, name, reviewer])
            
    # Sort by paper number and then by combined score descending
    context_rows.sort(key=lambda x: (int(x[0]), -x[3]))
    
    headers = ['paper', 'assigned', 'role', 'combined_score', 'tpms_score', 'topic_score', 'seniority', 'field', 'name', 'reviewer']
    
    # Calculate max width for each column (excluding header)
    widths = [max(len(str(row[i])) for row in context_rows) for i in range(len(headers))]
    
    with open(context_file, 'w', newline='', encoding='utf-8') as f:
        # Write header (first column and last two columns unpadded)
        header_strings = [headers[0]] + [f"{headers[i]:<{widths[i]}}" for i in range(1, 8)] + [headers[8], headers[9]]
        f.write(",".join(header_strings) + "\n")
        # Write rows (first column and last two columns unpadded)
        for row in context_rows:
            row_strings = [str(row[0])] + [f"{str(row[i]):<{widths[i]}}" for i in range(1, 8)] + [str(row[8]), str(row[9])]
            f.write(",".join(row_strings) + "\n")


if __name__ == "__main__":
    main()
