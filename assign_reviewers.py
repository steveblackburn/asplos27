import argparse
import csv
import os
from ortools.linear_solver import pywraplp
import yaml

def main():
    parser = argparse.ArgumentParser(description="Assign reviewers to papers using OR-Tools.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix")
    parser.add_argument("--scores", default="data/paper-reviewer-combined-scores.csv", help="Combined scores CSV")
    parser.add_argument("--stats-file", default="data/paper-stats-pc.csv", help="PC paper stats CSV (scores list)")
    parser.add_argument("--stats-file-vc", default="data/paper-stats-vc.csv", help="VC paper stats CSV (scores list)")
    parser.add_argument("--constraints", default="constraints.yaml", help="Constraints YAML file")
    parser.add_argument("--demographics", default="data/pc-demographics.csv", help="PC demographics CSV")
    parser.add_argument("--pcinfo", default="data/from-hotcrp/asplos27-apr-pcinfo.csv", help="PC info CSV")
    parser.add_argument("--output", default="data/pc-assignments.csv", help="Output CSV file")
    parser.add_argument("--tpms-scores", default="data/from-tpms/tpms-mock.csv", help="TPMS scores CSV (no header)")
    parser.add_argument("--topic-scores", default="data/paper-reviewer-topic-scores.csv", help="Topic scores CSV")
    parser.add_argument("--objective", default="max_relative", choices=["max_total", "max_relative"], help="Objective function: max_total (maximize total score), max_relative (maximize fraction of optimal unconstrained score)")
    parser.add_argument("--hotcrp-output", default="data/to-hotcrp/asplos27-apr-pc-assignments.csv", help="HotCRP assignments CSV output file")
    parser.add_argument("--hotcrp-vc-output", default="data/to-hotcrp/asplos27-apr-vc-assignments.csv", help="HotCRP VC assignments CSV output file")
    parser.add_argument("--hotcrp-pref-output", default="data/to-hotcrp/asplos27-apr-preferences.csv", help="HotCRP preferences CSV output file")
    parser.add_argument("--hotcrp-tags-output", default="data/to-hotcrp/asplos27-apr-papertags.csv", help="HotCRP paper tags CSV output file")
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
    try:
        with open(pcinfo_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                if 'pc-full' in tags:
                    full_reviewers.add(email)
                elif 'erc' in tags:
                    erc_reviewers.add(email)
                
                if 'vc' in tags:
                    vc_reviewers.add(email)
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
                if len(row) >= 3:
                    email = row[0]
                    seniority = row[2]
                    if seniority == 'S':
                        senior_reviewers.add(email)
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

    # d. Reviewer load bounds
    # Full: 8-9, ERC: 2-3
    # Except if listed in reviewer_limits
    for reviewer in reviewers:
        if reviewer in full_reviewers:
            min_l = 8
            max_l = 9
        elif reviewer in erc_reviewers:
            min_l = 2
            max_l = 3
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
        # Write context file
        context_file = os.path.join(os.path.dirname(output_file), "pc-assignment-context.csv")
        print(f"Writing assignment context to {context_file}")
        context_rows = []
        for paper in papers:
            for reviewer in reviewers:
                assigned = "yes" if (paper, reviewer) in x and x[(paper, reviewer)].solution_value() > 0.5 else "no"
                comb_score = scores.get((paper, reviewer), 0.0)
                tpms_score = tpms_scores_dict.get((paper, reviewer), 0.0)
                topic_score = topic_scores_dict.get((paper, reviewer), 0.0)
                
                context_rows.append([paper, reviewer, assigned, comb_score, tpms_score, topic_score])
                
        # Sort by paper number and then by combined score descending
        context_rows.sort(key=lambda x: (int(x[0]), -x[3]))
        
        with open(context_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'reviewer', 'assigned', 'combined_score', 'tpms_score', 'topic_score'])
            for row in context_rows:
                writer.writerow(row)

        # Write stats
        stats_file = os.path.join(os.path.dirname(output_file), "pc-assignment-stats.csv")
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
            
            stats_rows.append([paper, actual_score, optimal_score, fraction])
            
        # Sort by actual score ascending (worst to best)
        stats_rows.sort(key=lambda x: x[1])
        
        # Generate paper tags based on deciles of assignment quality
        tag_rows = []
        num_papers = len(stats_rows)
        for i, row in enumerate(stats_rows):
            paper = row[0]
            decile = int(i * 10 / num_papers) + 1
            tag_rows.append([paper, 'tag', 'aq', decile])
        
        # Calculate average relative score
        avg_relative_score = sum(row[3] for row in stats_rows) / len(stats_rows) if stats_rows else 0
        print(f"Average relative score: {avg_relative_score:.4f}")
        
        with open(stats_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'actual_score', 'optimal_score', 'fraction'])
            for row in stats_rows:
                writer.writerow([row[0], f"{row[1]:.2f}", f"{row[2]:.2f}", f"{row[3]:.4f}"])
        
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
    else:
        print(f"Error: VC Solver failed with status {status_vc}")


if __name__ == "__main__":
    main()
