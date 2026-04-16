import csv
import os
import sys
import yaml

# Paths
constraints_path = "constraints.yaml"
pcinfo_path = "data/from-hotcrp/asplos27-apr-pcinfo.csv"
demographics_path = "data/from-sheets/pc-demographics.csv"
scores_path = "data/paper-reviewer-combined-scores.csv"
stats_pc_path = "data/paper-stats-pc.csv"
stats_vc_path = "data/paper-stats-vc.csv"
pc_assignments_path = "data/to-hotcrp/asplos27-apr-pc-assignments.csv"
vc_assignments_path = "data/to-hotcrp/asplos27-apr-vc-assignments.csv"


def load_constraints():
    if not os.path.exists(constraints_path):
        print(f"Error: {constraints_path} not found.")
        sys.exit(1)
    with open(constraints_path, "r") as f:
        return yaml.safe_load(f)


def load_pcinfo():
    full_reviewers = set()
    erc_reviewers = set()
    vc_reviewers = set()
    email_to_name = {}
    with open(pcinfo_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row["email"]
            tags = row.get("tags", "")
            given_name = row.get("given_name", "")
            family_name = row.get("family_name", "")
            name = f"{given_name} {family_name}".strip()
            
            if "pc-full" in tags:
                full_reviewers.add(email)
            if "erc" in tags:
                erc_reviewers.add(email)
            if "vc" in tags:
                vc_reviewers.add(email)
                
            if email:
                email_to_name[email] = name
    return full_reviewers, erc_reviewers, vc_reviewers, email_to_name


def load_demographics():
    senior_reviewers = set()
    with open(demographics_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 7:
                email = row[2]
                seniority = row[-1]
                if seniority == "S":
                    senior_reviewers.add(email)
    return senior_reviewers


def load_scores():
    scores = {}
    with open(scores_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scores[(row["paper"], row["reviewer"])] = float(row["score"])
    return scores


def load_optimal_scores(path):
    optimal_scores = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    paper = row[0]
                    scores_list = [float(s) for s in row[1:]]
                    optimal_scores[paper] = scores_list
    return optimal_scores


def get_deciles(values):
    if not values:
        return []
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    deciles = []
    for i in range(1, 11):
        idx = int(i * n / 10) - 1
        idx = max(0, min(idx, n - 1))
        deciles.append(sorted_vals[idx])
    return deciles


def main():
    constraints = load_constraints()
    reviews_per_paper = constraints.get("reviews_per_paper", 8)
    max_erc = constraints.get("max_erc_reviews_per_paper", 2)
    min_senior = constraints.get("min_senior_reviewers_per_paper", 1)
    vc_per_paper = constraints.get("vice_chairs_per_paper", 1)
    reviewer_limits = constraints.get("reviewer_limits", {})

    full_reviewers, erc_reviewers, vc_reviewers, email_to_name = load_pcinfo()
    senior_reviewers = load_demographics()
    scores = load_scores()
    optimal_scores_list = load_optimal_scores(stats_pc_path)
    optimal_vc_scores_list = load_optimal_scores(stats_vc_path)

    # Verify PC Assignments
    print("--- Verifying PC Assignments ---")
    paper_to_reviewers = {}
    reviewer_to_papers = {}

    if not os.path.exists(pc_assignments_path):
        print(f"Error: {pc_assignments_path} not found.")
        sys.exit(1)

    with open(pc_assignments_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper = row["paper"]
            email = row["email"]
            if paper not in paper_to_reviewers:
                paper_to_reviewers[paper] = []
            paper_to_reviewers[paper].append(email)

            if email not in reviewer_to_papers:
                reviewer_to_papers[email] = []
            reviewer_to_papers[email].append(paper)

    pc_constraints_met = True
    all_papers = set(paper_to_reviewers.keys())

    for paper in all_papers:
        assigned = paper_to_reviewers.get(paper, [])

        # 1. Reviews per paper
        if len(assigned) != reviews_per_paper:
            print(
                f"Warning: Paper {paper} has {len(assigned)} reviews (expected {reviews_per_paper})"
            )
            pc_constraints_met = False

        # 2. Max ERC
        erc_count = sum(1 for r in assigned if r in erc_reviewers)
        if erc_count > max_erc:
            print(
                f"Warning: Paper {paper} has {erc_count} ERC reviewers (max {max_erc})"
            )
            pc_constraints_met = False

        # 3. Min Senior
        senior_count = sum(1 for r in assigned if r in senior_reviewers)
        if senior_count < min_senior:
            print(
                f"Warning: Paper {paper} has {senior_count} senior reviewers (min {min_senior})"
            )
            pc_constraints_met = False

    # 4. Reviewer limits
    for email, papers_assigned in reviewer_to_papers.items():
        if email in reviewer_limits:
            limit = reviewer_limits[email]
            if len(papers_assigned) > limit:
                print(
                    f"Warning: Reviewer {email} assigned to {len(papers_assigned)} papers (limit {limit})"
                )
                pc_constraints_met = False

    if pc_constraints_met:
        print("File respects all stated PC constraints.")
    else:
        print("File DOES NOT respect all stated PC constraints.")

    # Report load distributions
    print("\n--- PC Load Distribution ---")
    full_pc_loads = {}
    erc_loads = {}
    exception_loads = {}
    other_loads = {}

    for email, papers_assigned in reviewer_to_papers.items():
        count = len(papers_assigned)
        if email in reviewer_limits:
            exception_loads[email] = count
        elif email in full_reviewers:
            full_pc_loads[count] = full_pc_loads.get(count, 0) + 1
        elif email in erc_reviewers:
            erc_loads[count] = erc_loads.get(count, 0) + 1
        else:
            other_loads[count] = other_loads.get(count, 0) + 1

    print("Full PC assignments (excluding exceptions):")
    for count in sorted(full_pc_loads.keys()):
        print(f"  {count} assignments: {full_pc_loads[count]} reviewers")

    print("ERC assignments (excluding exceptions):")
    for count in sorted(erc_loads.keys()):
        print(f"  {count} assignments: {erc_loads[count]} reviewers")

    if other_loads:
        print("Other assignments:")
        for count in sorted(other_loads.keys()):
            print(f"  {count} assignments: {other_loads[count]} reviewers")

    print("Exceptions:")
    for email in sorted(exception_loads.keys()):
        name = email_to_name.get(email, email)
        print(f"  {name}: {exception_loads[email]} assignments")

    # Verify VC Assignments
    print("\n--- Verifying VC Assignments ---")
    vc_paper_to_reviewers = {}
    if not os.path.exists(vc_assignments_path):
        print(f"Error: {vc_assignments_path} not found.")
        sys.exit(1)

    vc_reviewer_to_papers = {}
    with open(vc_assignments_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            paper = row["paper"]
            email = row["email"]
            if paper not in vc_paper_to_reviewers:
                vc_paper_to_reviewers[paper] = []
            vc_paper_to_reviewers[paper].append(email)
            
            if email not in vc_reviewer_to_papers:
                vc_reviewer_to_papers[email] = []
            vc_reviewer_to_papers[email].append(paper)

    vc_constraints_met = True
    for paper in all_papers:
        assigned = vc_paper_to_reviewers.get(paper, [])
        if len(assigned) != vc_per_paper:
            print(
                f"Warning: Paper {paper} has {len(assigned)} VC assignments (expected {vc_per_paper})"
            )
            vc_constraints_met = False

    if vc_constraints_met:
        print("File respects all stated VC constraints.")
    else:
        print("File DOES NOT respect all stated VC constraints.")

    # Report VC load distributions
    print("\n--- VC Load Distribution ---")
    vc_loads = {}
    vc_exception_loads = {}

    for email, papers_assigned in vc_reviewer_to_papers.items():
        count = len(papers_assigned)
        if email in reviewer_limits:
            vc_exception_loads[email] = count
        else:
            vc_loads[count] = vc_loads.get(count, 0) + 1

    print("VC assignments (excluding exceptions):")
    for count in sorted(vc_loads.keys()):
        print(f"  {count} assignments: {vc_loads[count]} reviewers")

    if vc_exception_loads:
        print("Exceptions:")
        for email in sorted(vc_exception_loads.keys()):
            name = email_to_name.get(email, email)
            print(f"  {name}: {vc_exception_loads[email]} assignments")

    # Summarization
    print(
        "\nThe following summaries capture the distribution of assignment quality among papers.\n"
        "Assignment quality is measured in terms of average reviewer scores per paper (/100),\n"
        "minimum reviewer scores per paper (/100), and the ratio between the assignment quality\n"
        "and the optimal assignment (assigning the best available reviewers, which could happen\n"
        "if reviewer loads were unbounded)."
    )
    print("\n--- Per-Paper PC Assignment Summary (distributions, in deciles) ---")

    avg_scores = []
    min_scores = []
    ratios = []

    for paper in all_papers:
        assigned = paper_to_reviewers.get(paper, [])
        assigned_scores = [scores.get((paper, r), 0.0) for r in assigned]

        if assigned_scores:
            avg_score = sum(assigned_scores) / len(assigned_scores)
            min_score = min(assigned_scores)
        else:
            avg_score = 0.0
            min_score = 0.0

        avg_scores.append(avg_score)
        min_scores.append(min_score)

        # Compute optimal score
        opt_list = optimal_scores_list.get(paper, [])
        if opt_list:
            top_n = sorted(opt_list, reverse=True)[:reviews_per_paper]
            optimal_score = sum(top_n) / len(top_n) if top_n else 1.0
        else:
            optimal_score = 1.0

        if optimal_score == 0:
            optimal_score = 1.0

        ratios.append(avg_score / optimal_score)

    deciles_avg = get_deciles(avg_scores)
    deciles_min = get_deciles(min_scores)
    deciles_ratio = get_deciles(ratios)

    print(
        "Average reviewer scores: " + " ".join(f"{x:.1f}" for x in deciles_avg)
    )
    print(
        "Minimum reviewer scores: " + " ".join(f"{x:.1f}" for x in deciles_min)
    )
    print(
        "Average/optimal ratios:  "
        + " ".join(f"{x:.2f}" for x in deciles_ratio)
    )
    # VC Score Summary
    print("\n--- Per-Paper VC Assignment Summary (distributions, in deciles) ---")
    vc_avg_scores = []
    vc_min_scores = []
    vc_ratios = []

    for paper in all_papers:
        assigned = vc_paper_to_reviewers.get(paper, [])
        assigned_scores = [scores.get((paper, r), 0.0) for r in assigned]

        if assigned_scores:
            avg_score = sum(assigned_scores) / len(assigned_scores)
            min_score = min(assigned_scores)
        else:
            avg_score = 0.0
            min_score = 0.0

        vc_avg_scores.append(avg_score)
        vc_min_scores.append(min_score)

        # Compute optimal score for VC
        opt_list = optimal_vc_scores_list.get(paper, [])
        if opt_list:
            top_n = sorted(opt_list, reverse=True)[:vc_per_paper]
            optimal_score = sum(top_n) / len(top_n) if top_n else 1.0
        else:
            optimal_score = 1.0

        if optimal_score == 0:
            optimal_score = 1.0

        vc_ratios.append(avg_score / optimal_score)

    deciles_vc_avg = get_deciles(vc_avg_scores)
    deciles_vc_min = get_deciles(vc_min_scores)
    deciles_vc_ratio = get_deciles(vc_ratios)

    print(
        "Average reviewer scores: "
        + " ".join(f"{x:.1f}" for x in deciles_vc_avg)
    )
    print(
        "Minimum reviewer scores: "
        + " ".join(f"{x:.1f}" for x in deciles_vc_min)
    )
    print(
        "Average/optimal ratios:  "
        + " ".join(f"{x:.2f}" for x in deciles_vc_ratio)
    )

    # --- Per Reviewer Analysis ---
    print(
        "\n\nThe following summaries capture the distribution of assignment quality among reviewers.\n"
        "Assignment quality is measured in terms of average reviewer scores per reviewer (/100),\n"
        "minimum reviewer scores per reviewer (/100), and the ratio between the assignment quality\n"
        "and the optimal assignment (assigning the papers they score highest on)."
    )

    # PC Reviewers
    reviewer_avg_scores = []
    reviewer_min_scores = []
    reviewer_ratios = []

    reviewer_to_all_scores = {}
    for (paper, reviewer), score in scores.items():
        if reviewer not in reviewer_to_all_scores:
            reviewer_to_all_scores[reviewer] = []
        reviewer_to_all_scores[reviewer].append(score)

    for reviewer, assigned_papers in reviewer_to_papers.items():
        if not assigned_papers:
            continue
        assigned_scores = [
            scores.get((paper, reviewer), 0.0) for paper in assigned_papers
        ]
        avg_score = sum(assigned_scores) / len(assigned_scores)
        min_score = min(assigned_scores)

        all_reviewer_scores = reviewer_to_all_scores.get(reviewer, [])
        top_n = sorted(all_reviewer_scores, reverse=True)[
            : len(assigned_papers)
        ]
        optimal_score = sum(top_n) / len(top_n) if top_n else 1.0

        if optimal_score == 0:
            optimal_score = 1.0

        reviewer_avg_scores.append(avg_score)
        reviewer_min_scores.append(min_score)
        reviewer_ratios.append(avg_score / optimal_score)

    deciles_rev_avg = get_deciles(reviewer_avg_scores)
    deciles_rev_min = get_deciles(reviewer_min_scores)
    deciles_rev_ratio = get_deciles(reviewer_ratios)

    print(
        "\n--- Per-Reviewer PC Assignment Summary (distributions, in deciles) ---"
    )
    print(
        "Average reviewer scores: "
        + " ".join(f"{x:.1f}" for x in deciles_rev_avg)
    )
    print(
        "Minimum reviewer scores: "
        + " ".join(f"{x:.1f}" for x in deciles_rev_min)
    )
    print(
        "Average/optimal ratios:  "
        + " ".join(f"{x:.2f}" for x in deciles_rev_ratio)
    )

    # VC Reviewers
    vc_reviewer_avg_scores = []
    vc_reviewer_min_scores = []
    vc_reviewer_ratios = []

    for reviewer, assigned_papers in vc_reviewer_to_papers.items():
        if not assigned_papers:
            continue
        assigned_scores = [
            scores.get((paper, reviewer), 0.0) for paper in assigned_papers
        ]
        avg_score = sum(assigned_scores) / len(assigned_scores)
        min_score = min(assigned_scores)

        all_reviewer_scores = reviewer_to_all_scores.get(reviewer, [])
        top_n = sorted(all_reviewer_scores, reverse=True)[
            : len(assigned_papers)
        ]
        optimal_score = sum(top_n) / len(top_n) if top_n else 1.0

        if optimal_score == 0:
            optimal_score = 1.0

        vc_reviewer_avg_scores.append(avg_score)
        vc_reviewer_min_scores.append(min_score)
        vc_reviewer_ratios.append(avg_score / optimal_score)

    deciles_vc_rev_avg = get_deciles(vc_reviewer_avg_scores)
    deciles_vc_rev_min = get_deciles(vc_reviewer_min_scores)
    deciles_vc_rev_ratio = get_deciles(vc_reviewer_ratios)

    print(
        "\n--- Per-Reviewer VC Assignment Summary (distributions, in deciles) ---"
    )
    print(
        "Average reviewer scores: "
        + " ".join(f"{x:.1f}" for x in deciles_vc_rev_avg)
    )
    print(
        "Minimum reviewer scores: "
        + " ".join(f"{x:.1f}" for x in deciles_vc_rev_min)
    )
    print(
        "Average/optimal ratios:  "
        + " ".join(f"{x:.2f}" for x in deciles_vc_rev_ratio)
    )


if __name__ == "__main__":
    main()
