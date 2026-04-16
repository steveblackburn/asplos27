import csv
import os
import sys
import yaml

constraints_path = "constraints.yaml"
authors_path = "data/from-hotcrp/asplos27-apr-authors.csv"


def load_constraints():
    if os.path.exists(constraints_path):
        with open(constraints_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def main():
    constraints = load_constraints()
    max_submissions = constraints.get("max_submissions_per_author", 5)

    if not os.path.exists(authors_path):
        print(f"Error: {authors_path} not found.")
        sys.exit(1)

    author_to_papers = {}
    email_to_name = {}

    with open(authors_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            is_contact = row.get("iscontact") or ""
            is_contact = is_contact.lower()
            if is_contact == "nonauthor":
                continue

            email = (row.get("email") or "").strip()
            paper = (row.get("paper") or "").strip()
            given_name = (row.get("given_name") or "").strip()
            family_name = (row.get("family_name") or "").strip()
            name = f"{given_name} {family_name}".strip()

            if not email or not paper:
                continue

            if email not in author_to_papers:
                author_to_papers[email] = set()
                email_to_name[email] = name
            author_to_papers[email].add(paper)

    violations = []
    distribution = {}

    for email, papers in author_to_papers.items():
        count = len(papers)
        distribution[count] = distribution.get(count, 0) + 1
        if count > max_submissions:
            violations.append((email, count))

    print("--- Author Submission Check ---")
    print(f"Maximum allowed submissions: {max_submissions}")
    print(f"Total authors found: {len(author_to_papers)}")

    if violations:
        print("\nViolations found:")
        for email, count in sorted(violations, key=lambda x: x[1], reverse=True):
            name = email_to_name.get(email, email)
            papers = author_to_papers.get(email, set())
            papers_str = ", ".join(sorted(list(papers), key=int))
            print(f"  {name} ({email}): {count} submissions (Papers: {papers_str})")
    else:
        print("\nNo violations found.")

    print("\n--- Submission Distribution ---")
    for count in sorted(distribution.keys()):
        print(f"  {count} paper(s): {distribution[count]} author(s)")


if __name__ == "__main__":
    main()
