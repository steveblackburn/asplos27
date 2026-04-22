import csv
import os
from collections import defaultdict
from ortools.linear_solver import pywraplp

def main():
    scores_file = "data/paper-reviewer-combined-scores.csv"
    output_file = "data/to-hotcrp/asplos27-apr-administrator-assignments.csv"

    admins = [
        'steveblackburn@google.com',
        'ada@cc.gatech.edu',
        'abhishek.bhattacharjee@yale.edu',
        'sylee0506@gatech.edu',
        'michael.wu.mw976@yale.edu'
    ]

    # Mapping for students to advisors
    advisor_mapping = {
        'sylee0506@gatech.edu': 'ada@cc.gatech.edu',
        'michael.wu.mw976@yale.edu': 'abhishek.bhattacharjee@yale.edu'
    }

    # Read scores
    scores = {}
    papers = set()
    try:
        print(f"Reading combined scores from {scores_file}")
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
        return

    print(f"Loaded scores for {len(papers)} papers.")

    # Solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        print("Solver failed to initialize")
        return

    gatech_chairs = ['ada@cc.gatech.edu', 'sylee0506@gatech.edu']
    yale_chairs = ['abhishek.bhattacharjee@yale.edu', 'michael.wu.mw976@yale.edu']

    x = {}
    for p in papers:
        for a in admins:
            # Ad hoc constraints
            if p in ['519', '941', '140', '1147'] and a in gatech_chairs:
                continue
            if p in ['2104', '469'] and a in yale_chairs:
                continue
                
            score_key = advisor_mapping.get(a, a)
            # Only create variable if score > 0 (assuming 0 means conflict)
            if scores.get((p, score_key), 0.0) > 0:
                x[(p, a)] = solver.BoolVar(f'x_{p}_{a}')

    print(f"Created {len(x)} variables.")

    # Constraints
    # 1. Each paper gets exactly 1 administrator
    for p in papers:
        vars_for_paper = [x[(p, a)] for a in admins if (p, a) in x]
        if not vars_for_paper:
            print(f"Warning: Paper {p} has no non-conflicted administrators!")
        solver.Add(sum(vars_for_paper) == 1)

    # 2. Load balance: Equal (+/- 1)
    total_papers = len(papers)
    min_load = total_papers // len(admins)
    max_load = min_load + (1 if total_papers % len(admins) != 0 else 0)

    print(f"Target load per admin: {min_load} to {max_load}")

    for a in admins:
        vars_for_admin = [x[(p, a)] for p in papers if (p, a) in x]
        solver.Add(sum(vars_for_admin) >= min_load)
        solver.Add(sum(vars_for_admin) <= max_load)

    # Objective: Maximize total score
    objective = solver.Objective()
    for (p, a), var in x.items():
        score_key = advisor_mapping.get(a, a)
        score = scores.get((p, score_key), 0.0)
        objective.SetCoefficient(var, score)
    objective.SetMaximization()

    print("Solving...")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print("Solution found!")
        print(f"Total objective score: {objective.Value()}")
        
        # Write output
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        print(f"Writing administrator assignments to {output_file}")
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['paper', 'action', 'email'])
            for (p, a), var in x.items():
                if var.solution_value() > 0.5:
                    writer.writerow([p, 'administrator', a])
                    
        # Print stats
        admin_counts = defaultdict(int)
        for (p, a), var in x.items():
            if var.solution_value() > 0.5:
                admin_counts[a] += 1
        
        print("\nAssignment Stats:")
        for a in admins:
            print(f"  {a}: {admin_counts[a]} papers")
    else:
        print("No optimal solution found. Problem may be infeasible due to conflicts or load constraints.")

if __name__ == "__main__":
    main()
