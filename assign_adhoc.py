import csv
import sys
from collections import defaultdict
import os
from ortools.linear_solver import pywraplp

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Ad-hoc reviewer assignment')
    parser.add_argument('--mode', choices=['add', 'replace'], default='add', help='Assignment mode')
    parser.add_argument('num_reviews', type=int, help='Number of reviews to assign per reviewer')
    parser.add_argument('reviewers', nargs='+', help='Reviewer emails')
    
    args = parser.parse_args()
    num_reviews = args.num_reviews
    target_reviewers = args.reviewers
    mode = args.mode

    assignments_file = "data/to-hotcrp/asplos27-apr-pc-assignments.csv"
    scores_file = "data/paper-reviewer-combined-scores.csv"
    output_file = "data/to-hotcrp/asplos27-apr-pc-assignments-adhoc.csv"

    # Read existing assignments
    existing_assignments = set()
    paper_to_existing_reviewers = defaultdict(list)
    reviewer_to_original_counts = defaultdict(int)
    try:
        print(f"Reading existing assignments from {assignments_file}")
        with open(assignments_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['paper'] == 'all':
                    continue
                paper = row['paper']
                reviewer = row['email']
                existing_assignments.add((paper, reviewer))
                paper_to_existing_reviewers[paper].append(reviewer)
                reviewer_to_original_counts[reviewer] += 1
    except FileNotFoundError:
        print(f"Warning: Existing assignments file not found: {assignments_file}")

    # Read scores
    scores = {}
    papers = set()
    try:
        print(f"Reading scores from {scores_file}")
        with open(scores_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                reviewer = row['reviewer']
                score = float(row['score'])
                papers.add(paper)
                scores[(paper, reviewer)] = score
    except FileNotFoundError:
        print(f"Error: Scores file not found: {scores_file}")
        sys.exit(1)

    # Solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver failed to initialize")
        sys.exit(1)

    x = {}
    for p in papers:
        for r in target_reviewers:
            if (p, r) in scores and scores[(p, r)] > 0 and (p, r) not in existing_assignments:
                x[(p, r)] = solver.BoolVar(f'x_{p}_{r}')

    y = {}
    if mode == 'replace':
        for p in papers:
            for R in paper_to_existing_reviewers.get(p, []):
                if (p, R) in scores:
                    y[(p, R)] = solver.BoolVar(f'y_{p}_{R}')

    print(f"Created {len(x)} addition variables and {len(y)} removal variables.")

    # Constraints
    # 1. Each target reviewer gets num_reviews
    for r in target_reviewers:
        vars_for_rev = [x[(p, r)] for p in papers if (p, r) in x]
        if len(vars_for_rev) < num_reviews:
            print(f"Warning: Reviewer {r} only has {len(vars_for_rev)} valid papers available, but requested {num_reviews}.")
            solver.Add(sum(vars_for_rev) == len(vars_for_rev))
        else:
            solver.Add(sum(vars_for_rev) == num_reviews)

    # 2. Each paper gets at most 1 target reviewer
    for p in papers:
        vars_for_paper = [x[(p, r)] for r in target_reviewers if (p, r) in x]
        solver.Add(sum(vars_for_paper) <= 1)

    # 3. Replace mode constraints
    if mode == 'replace':
        for p in papers:
            vars_add = [x[(p, r)] for r in target_reviewers if (p, r) in x]
            vars_rem = [y[(p, R)] for R in paper_to_existing_reviewers.get(p, []) if (p, R) in y]
            solver.Add(sum(vars_rem) == sum(vars_add))
            
        all_existing_reviewers = set()
        for revs in paper_to_existing_reviewers.values():
            all_existing_reviewers.update(revs)
            
        for R in all_existing_reviewers:
            vars_rem_for_R = [y[(p, R)] for p in papers if (p, R) in y]
            if reviewer_to_original_counts.get(R, 0) <= num_reviews:
                solver.Add(sum(vars_rem_for_R) == 0)
            else:
                solver.Add(sum(vars_rem_for_R) <= 1)

    # Objective
    objective = solver.Objective()
    for (p, r), var in x.items():
        objective.SetCoefficient(var, scores[(p, r)])
        
    if mode == 'replace':
        for (p, R), var in y.items():
            objective.SetCoefficient(var, -scores[(p, R)])
            
    objective.SetMaximization()

    print("Solving...")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print("Solution found!")
        print(f"Total objective score: {objective.Value()}")
        
        # Write output (incremental assignments)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        print(f"Writing ad-hoc assignments to {output_file}")
        reviewer_to_new_counts = reviewer_to_original_counts.copy()
        affected_reviewers_set = set()
        reviewer_to_affected_papers = defaultdict(set)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'action', 'email', 'round'])
            
            if mode == 'replace':
                for (p, R), var in y.items():
                    if var.solution_value() > 0.5:
                        writer.writerow([p, 'clearreview', R, 'RR'])
                        print(f"Removed reviewer {R} from paper {p} (Score: {scores.get((p, R), 0.0)})")
                        reviewer_to_new_counts[R] -= 1
                        affected_reviewers_set.add(R)
                        reviewer_to_affected_papers[R].add(p)
                        
            for (p, r), var in x.items():
                if var.solution_value() > 0.5:
                    writer.writerow([p, 'primary', r, 'RR'])
                    new_score = scores.get((p, r), 0.0)
                    existing_revs = paper_to_existing_reviewers.get(p, [])
                    prior_scores = [scores.get((p, er), 0.0) for er in existing_revs if (p, er) in scores]
                    prior_scores.sort(reverse=True)
                    
                    new_scores = list(prior_scores)
                    if mode == 'replace':
                        for er in existing_revs:
                            if (p, er) in y and y[(p, er)].solution_value() > 0.5:
                                new_scores.remove(scores.get((p, er), 0.0))
                                break
                                
                    new_scores.append(new_score)
                    new_scores.sort(reverse=True)
                    
                    print(f"Assigned paper {p} to {r} (Score: {new_score})")
                    print(f"  Prior scores: {prior_scores}")
                    print(f"  New scores:   {new_scores}")
                    
                    reviewer_to_new_counts[r] += 1
                    affected_reviewers_set.add(r)
                    reviewer_to_affected_papers[r].add(p)
        print("Done.")

        print("\nAffected Reviewers Report:")
        for rev in sorted(affected_reviewers_set):
            prior = reviewer_to_original_counts.get(rev, 0)
            after = reviewer_to_new_counts.get(rev, 0)
            papers_list = sorted(list(reviewer_to_affected_papers[rev]))
            print(f"Reviewer: {rev}")
            print(f"  Prior assignments: {prior}")
            print(f"  After assignments: {after}")
            print(f"  Affected papers:   {papers_list}")
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    main()
