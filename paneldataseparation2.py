import os
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Windows cp1252 fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

SEP  = "=" * 62
SEP2 = "-" * 62

# =============================================================================
# 1. ROBUST CSV PARSER (UNCHANGED)
# =============================================================================

def parse_iv_csv(filepath):
    """
    Parse IV tracer CSV files in either quoted or unquoted format.
    Strips surrounding quotes and trailing whitespace.
    Returns list of sample dicts (metadata only).
    """
    samples = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    current = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        cols = [c.strip().strip('"') for c in line.split(',')]
        if not cols:
            continue

        key = cols[0]

        if key == 'Sample No.':
            if current is not None:
                samples.append(_finalise(current))
            current = {'_src': os.path.basename(filepath), '_meta': {}}
            if len(cols) > 1:
                current['_meta']['Sample No.'] = cols[1]
            continue

        if current is None:
            continue

        # Stop reading metadata once the numeric IV table begins
        if key == 'V (V)':
            continue

        if len(cols) > 1:
            value = cols[1]
            current['_meta'][key] = None if value == '-------' else value

    if current is not None:
        samples.append(_finalise(current))

    return samples


def _finalise(raw):
    """Convert raw metadata dict into a clean record."""
    m = raw['_meta']

    def fv(key):
        v = m.get(key)
        if v is None:
            return np.nan
        try:
            return float(v)
        except (ValueError, TypeError):
            return np.nan

    Vmpp = fv('Vmaxp (V)')
    Impp = fv('Imaxp (A)')
    Pmax = fv('Pmax (W)')
    if np.isnan(Pmax) and not (np.isnan(Vmpp) or np.isnan(Impp)):
        Pmax = Vmpp * Impp

    return {
        'source_file': raw['_src'],
        'sample_no':   str(m.get('Sample No.', '?')),
        'date_time':   m.get('Date & Time', ''),
        'Voc':         fv('Vopen (V)'),
        'Vmpp':        Vmpp,
        'Impp':        Impp,
        'Pmax':        Pmax,
    }


def _fmt(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '---'
    return f"{v:.4f}"


# =============================================================================
# 2. DISPLAY & SELECTION HELPERS (UNCHANGED)
# =============================================================================

def display_samples_table(samples):
    """Pretty-print a table of all samples found in the file."""
    print(f"\n  Samples found in file:")
    print(f"  {'#':<5} {'Sample No.':<12} {'Date & Time':<22} "
          f"{'Voc (V)':<10} {'Vmpp (V)':<10} {'Impp (A)':<10} "
          f"{'Pmax (W)':<10} {'File'}")
    print(f"  {'-'*105}")
    for i, s in enumerate(samples):
        print(f"  {i+1:<5} {s['sample_no']:<12} {s['date_time']:<22} "
              f"{_fmt(s['Voc']):<10} {_fmt(s['Vmpp']):<10} "
              f"{_fmt(s['Impp']):<10} {_fmt(s['Pmax']):<10} "
              f"{s['source_file']}")


def parse_number_list(raw_input, max_num):
    """Parse user input like '1,2,5-10' or 'all' into a list of 0-based indices."""
    raw = raw_input.strip()
    if raw.lower() == 'all':
        return list(range(max_num))

    indices = set()
    parts = raw.replace(';', ',').split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                for num in range(max(1, start), min(max_num, end) + 1):
                    indices.add(num - 1)
            except ValueError:
                pass
        else:
            try:
                num = int(part)
                if 1 <= num <= max_num:
                    indices.add(num - 1)
            except ValueError:
                pass
    return sorted(indices)


def select_panel_samples(samples, panel_label):
    """Ask the user to select sample numbers for a given panel."""
    max_num = len(samples)
    print(f"\n  Enter sample numbers for {panel_label} (e.g. 1,3,5-10 or 'all'):")
    while True:
        raw = input("  Your selection: ").strip()
        if not raw:
            print("  [!] Please enter at least one number.")
            continue

        indices = parse_number_list(raw, max_num)
        if not indices:
            print(f"  [!] No valid samples found. Available: 1 to {max_num}")
            continue

        selected = [samples[i] for i in indices]
        print(f"  [OK] Selected {len(selected)} sample(s) for {panel_label}: "
              f"{[s['sample_no'] for s in selected]}")
        return selected


# =============================================================================
# 3. UPDATED: IRRADIANCE ENTRY (NOW TAKES 3 VALUES AND AVERAGES THEM)
# =============================================================================

def ask_irradiance_for_samples(selected_samples, panel_label):
    """
    For each selected sample, ask for THREE irradiance values (W/m2),
    average them, and store ONLY the average in 'irradiance'.
    If user presses Enter on the first prompt, the sample is kept but irradiance is None (blank).
    """
    print(f"\n  Enter irradiance (W/m²) for each sample in {panel_label}.")
    print("  Input THREE values separated by commas, e.g.  850, 860, 855")
    print("  (Press Enter at the prompt to leave the sample entirely blank)")

    enriched = []
    for s in selected_samples:
        label = (f"    Sample {s['sample_no']} | {s['date_time']} "
                 f"| Pmax={_fmt(s['Pmax'])} W")
        while True:
            raw = input(f"{label}  ->  3 W/m² values: ").strip()
            
            new_s = dict(s)
            # If user presses Enter, skip ONLY the irradiance, keep the sample
            if raw == '':
                new_s['irradiance'] = None
                enriched.append(new_s)
                print(f"    [--] Left blank for Sample {s['sample_no']}.")
                break
            
            # Parse comma separated values
            parts = [p.strip() for p in raw.split(',') if p.strip()]
            if len(parts) != 3:
                print("    [!] Please enter exactly THREE numbers separated by commas.")
                continue
            
            try:
                vals = [float(p) for p in parts]
                avg = sum(vals) / 3.0
                new_s['irradiance'] = avg
                enriched.append(new_s)
                print(f"    [OK] Average = {avg:.2f} W/m²")
                break
            except ValueError:
                print("    [!] Invalid number detected. Please enter numeric values.")
                continue
    return enriched


# =============================================================================
# 4. SAVE OUTPUT (UNCHANGED)
# =============================================================================

def save_combined_output(panel1_records, panel2_records, output_dir):
    """Save the accumulated records to two Excel/CSV files."""
    if not panel1_records and not panel2_records:
        print("\n  [!] No records accumulated. Nothing to save.")
        return

    def save_single(records, label):
        if not records:
            print(f"  [!] No records for {label}, skipping.")
            return

        df = pd.DataFrame(records)

        columns_order = ['sample_no', 'date_time', 'source_file',
                         'Voc', 'Vmpp', 'Impp', 'Pmax', 'irradiance']
        existing_cols = [col for col in columns_order if col in df.columns]
        df = df[existing_cols]

        # Format floats nicely, leaving None/NaN as blank
        for col in ['Voc', 'Vmpp', 'Impp', 'Pmax', 'irradiance']:
            if col in df.columns:
                df[col] = df[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else '')

        # Determine output path
        out_path = os.path.join(output_dir, f"Combined_{label}.xlsx")
        
        # Add a counter if the file already exists (to avoid overwriting previous runs)
        base, ext = os.path.splitext(out_path)
        counter = 1
        while os.path.exists(out_path):
            out_path = f"{base}_{counter}{ext}"
            counter += 1

        if OPENPYXL_OK and out_path.endswith('.xlsx'):
            try:
                with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=label, index=False)
                print(f"  [OK] {label} saved to: {out_path}")
                return
            except Exception as e:
                print(f"  [!] Excel write failed ({e}), falling back to CSV.")

        # Fallback to CSV
        csv_path = out_path.replace('.xlsx', '.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"  [OK] {label} saved as CSV: {csv_path}")

    save_single(panel1_records, "Panel1")
    save_single(panel2_records, "Panel2")


# =============================================================================
# 5. MAIN (UNCHANGED - BATCH LOOP)
# =============================================================================

def main():
    print(f"\n{SEP}")
    print("  IV Curve Panel Splitter - BATCH PROCESSING (3-Value Averaging)")
    print(f"{SEP}")
    print("""
  How this works:
  1. Load a .csv file, select Panel 1 & 2 samples.
  2. For EACH sample, enter THREE irradiance readings (W/m²), separated by commas.
     The code automatically averages them and stores ONLY the average.
  3. Press Enter at the prompt to leave the irradiance blank (sample still kept).
  4. When done, you will be asked if you want to load ANOTHER file.
  5. ALL samples from ALL files are accumulated.
  6. At the very end, TWO combined Excel files are created:
     - Combined_Panel1.xlsx
     - Combined_Panel2.xlsx
""")

    all_panel1_records = []
    all_panel2_records = []
    first_file_dir = None
    file_counter = 0

    while True:
        file_counter += 1
        print(f"\n{SEP}")
        print(f"  FILE #{file_counter}")
        print(f"{SEP}")

        # ---- Get file path ----
        while True:
            raw_path = input("  Enter path to your IV curve .csv file: ").strip()
            if (raw_path.startswith('"') and raw_path.endswith('"')) or \
               (raw_path.startswith("'") and raw_path.endswith("'")):
                raw_path = raw_path[1:-1].strip()

            if not raw_path:
                print("  [!] Please enter a valid path.")
                continue
            if not os.path.isfile(raw_path):
                print(f"  [!] File not found: {raw_path}")
                print("      Tip: drag the file into this window.")
                continue
            if not raw_path.lower().endswith('.csv'):
                print(f"  [!] Not a .csv file: {raw_path}")
                continue
            break

        # Store the directory of the first file to save outputs there later
        if first_file_dir is None:
            first_file_dir = os.path.dirname(raw_path) or os.getcwd()

        # ---- Parse ----
        print(f"\n  Parsing {os.path.basename(raw_path)}...")
        try:
            all_samples = parse_iv_csv(raw_path)
        except Exception as e:
            print(f"  [!] Fatal error reading file: {e}")
            cont = input("  Skip this file and continue? (y/n): ").strip().lower()
            if cont != 'y':
                print("  Exiting.")
                return
            continue

        if not all_samples:
            print("  [!] No samples found. Skipping this file.")
            continue

        print(f"  [OK] Found {len(all_samples)} sample(s).")
        display_samples_table(all_samples)

        # ---- Select panels ----
        panel1_samples = select_panel_samples(all_samples, "Panel 1")
        panel2_samples = select_panel_samples(all_samples, "Panel 2")

        # Check overlap
        p1_nos = {s['sample_no'] for s in panel1_samples}
        p2_nos = {s['sample_no'] for s in panel2_samples}
        overlap = p1_nos & p2_nos
        if overlap:
            print(f"\n  [!] WARNING: Sample numbers {sorted(overlap)} appear in BOTH panels!")
            proceed = input("  Continue anyway? (y/n): ").strip().lower()
            if proceed != 'y':
                print("  Skipping this file.")
                continue

        # ---- Enter irradiance (NOW ASKS FOR 3 VALUES AND AVERAGES) ----
        print(f"\n{SEP}")
        print("  IRRADIANCE ENTRY (3 values per sample)")
        print(f"{SEP}")

        enriched_p1 = ask_irradiance_for_samples(panel1_samples, "Panel 1")
        enriched_p2 = ask_irradiance_for_samples(panel2_samples, "Panel 2")

        # ---- Accumulate ----
        all_panel1_records.extend(enriched_p1)
        all_panel2_records.extend(enriched_p2)
        print(f"\n  [OK] Accumulated totals:")
        print(f"       Panel 1: {len(all_panel1_records)} samples")
        print(f"       Panel 2: {len(all_panel2_records)} samples")

        # ---- Ask to continue ----
        print(f"\n{SEP2}")
        cont = input("  Load another CSV file? (y/n): ").strip().lower()
        if cont != 'y':
            break

    # ---- End of batch loop: Save final combined outputs ----
    print(f"\n{SEP}")
    print("  SAVING FINAL COMBINED OUTPUTS")
    print(f"{SEP}")

    if first_file_dir is None:
        first_file_dir = os.getcwd()

    save_combined_output(all_panel1_records, all_panel2_records, first_file_dir)

    print(f"\n{SEP}")
    print("  Batch processing complete!")
    print(f"  Total Panel 1 samples processed: {len(all_panel1_records)}")
    print(f"  Total Panel 2 samples processed: {len(all_panel2_records)}")
    print(f"{SEP}")
    input("\n  Press Enter to exit...")


if __name__ == "__main__":
    main()
