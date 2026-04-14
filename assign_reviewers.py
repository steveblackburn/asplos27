import argparse
import csv
import os
from ortools.linear_solver import pywraplp
import yaml

def main():
    parser = argparse.ArgumentParser(description="Assign reviewers to papers using OR-Tools.")
    parser.add_argument("--prefix", default="asplos27-apr", help="Conference prefix")
    parser.add_argument("--scores", default="data/paper_reviewer_combined_scores.csv", help="Combined scores CSV")
    parser.add_argument("--constraints", default="constraints.yaml", help="Constraints YAML file")
    parser.add_argument("--demographics", default="data/pc_demographics.csv", help="PC demographics CSV")
    parser.add_argument("--pcinfo", default="data/from-hotcrp/asplos27-apr-pcinfo.csv", help="PC info CSV")
    parser.add_argument("--output", default="data/assignments.csv", help="Output CSV file")
    args = parser.parse_args()

    prefix = args.prefix
    scores_file = args.scores
    constraints_file = args.constraints
    demographics_file = args.demographics
    pcinfo_file = args.pcinfo
    output_file = args.output

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
    reviewer_limits = config.get('reviewer_limits', {})

    # 2. Read pcinfo for tags
    print(f"Reading PC info from {pcinfo_file}")
    full_reviewers = set()
    erc_reviewers = set()
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

                # Only consider full and erc reviewers
                if reviewer in full_reviewers or reviewer in erc_reviewers:
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
    print(f"Valid pairs: {len(valid_pairs)} (after filtering for eligible reviewers and non-zero scores)")

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
            if (paper, reviewer) in valid_pairs:
                x[(paper, reviewer)] = solver.BoolVar(f'x_{paper}_{reviewer}')

    # Objective: Maximize total score
    objective = solver.Objective()
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
        print(f"Solution found! Status: {status}")
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
        # Write stats
        stats_file = os.path.join(os.path.dirname(output_file), "assignment_stats.csv")
        print(f"Writing assignment stats to {stats_file}")
        stats_rows = []
        for paper in sorted_papers:
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
        
        with open(stats_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'actual_score', 'optimal_score', 'fraction'])
            for row in stats_rows:
                writer.writerow([row[0], f"{row[1]:.2f}", f"{row[2]:.2f}", f"{row[3]:.4f}"])
        
        print("Done.")
    else:
        print(f"Error: Solver failed with status {status}")

if __name__ == "__main__":
    main()
