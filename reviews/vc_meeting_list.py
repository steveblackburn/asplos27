import csv
import os
from collections import defaultdict

def main():
    discuss_file = "data/from-hotcrp/asplos27-apr-data-vc-rr-discuss.csv"
    conflicts_file = "../assignments/data/from-hotcrp/asplos27-apr-pcconflicts.csv"
    pcinfo_file = "../assignments/data/from-hotcrp/asplos27-apr-pcinfo.csv"
    vc_assignments_file = "../assignments/data/to-hotcrp/asplos27-apr-vc-assignments.csv"

    # 1. Load VCs: email -> Full Name
    vc_names = {}
    if os.path.exists(pcinfo_file):
        with open(pcinfo_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email']
                tags = row.get('tags', '')
                if 'vc' in tags:
                    vc_names[email] = f"{row['given_name']} {row['family_name']}"
    else:
        print(f"Error: PC info file not found at {pcinfo_file}")
        return

    # 2. Load Conflicts: paper -> set of conflicted emails
    paper_conflicts = defaultdict(set)
    if os.path.exists(conflicts_file):
        with open(conflicts_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                paper = row['paper']
                email = row['email']
                paper_conflicts[paper].add(email)
    else:
        print(f"Error: Conflicts file not found at {conflicts_file}")
        return

    # 2.5 Load VC Assignments: paper -> vc_email
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

    # 3. Load Discuss Papers and Print Report
    if os.path.exists(discuss_file):
        with open(discuss_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            print(f"{'Paper':<6} {'Title':<50} {'Assigned VC':<25} {'Conflicted VCs'}")
            print("-" * 120)
            for row in reader:
                paper = row['ID']
                title = row['Title']
                
                assigned_vc_email = paper_to_vc.get(paper)
                assigned_vc_name = vc_names.get(assigned_vc_email, "None") if assigned_vc_email else "None"
                
                conflicted_emails = paper_conflicts.get(paper, set())
                conflicted_vcs = [vc_names[email] for email in conflicted_emails if email in vc_names]
                
                vc_str = ", ".join(conflicted_vcs) if conflicted_vcs else "None"
                
                # Truncate title if too long
                title_trunc = title[:47] + "..." if len(title) > 50 else title
                
                print(f"{paper:<6} {title_trunc:<50} {assigned_vc_name:<25} {vc_str}")
    else:
        print(f"Error: Discuss file not found at {discuss_file}")

if __name__ == '__main__':
    main()
