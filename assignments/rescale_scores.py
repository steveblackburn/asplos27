import collections
import csv
import os

def rescale_file(input_file, output_file, has_header):
    print(f"Rescaling {input_file} to {output_file}...")
    
    # Read data
    entries = []
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as f:
            if has_header:
                reader = csv.DictReader(f)
                for row in reader:
                    entries.append({'paper': row['paper'], 'reviewer': row['reviewer'], 'score': float(row['score'])})
            else:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        entries.append({'paper': row[0], 'reviewer': row[1], 'score': float(row[2])})
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}")
        return
                    
    # Sort by score ascending
    entries.sort(key=lambda x: x['score'])
    
    total = len(entries)
    if total == 0:
        print("No entries found.")
        return
        
    print(f"Found {total} entries. Calculating median ranks...")
        
    # Find ties and assign median rank
    score_groups = collections.defaultdict(list)
    for i, entry in enumerate(entries):
        score_groups[entry['score']].append(i)
        
    # Assign scores
    for score, indices in score_groups.items():
        min_pos = indices[0] + 1
        max_pos = indices[-1] + 1
        median_rank = (min_pos + max_pos) / 2.0
        scaled_score = median_rank / total
        
        for i in indices:
            entries[i]['scaled_score'] = scaled_score
            
    # Sort by paper number (numeric) and then by score (descending)
    entries.sort(key=lambda x: (int(x['paper']), -x['scaled_score']))
            
    # Write output
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['paper', 'reviewer', 'score'])
        for entry in entries:
            writer.writerow([entry['paper'], entry['reviewer'], f"{entry['scaled_score']:.6f}"])
            
    print(f"Successfully wrote {output_file}")

def main():
    # TPMS
    rescale_file('data/from-tpms/asplos27_scores.csv', 'data/paper-reviewer-scaled-tpms.csv', has_header=False)
    # Topic
    rescale_file('data/paper-reviewer-topic-scores.csv', 'data/paper-reviewer-scaled-topic.csv', has_header=True)
    print("All done.")

if __name__ == "__main__":
    main()
