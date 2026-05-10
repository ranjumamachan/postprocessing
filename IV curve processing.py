import pandas as pd
import matplotlib.pyplot as plt
import os
import re
from pathlib import Path
from datetime import datetime
import numpy as np

# ----------------------------------------------------------------------
# 1. Parsing raw IV files (same as before)
# ----------------------------------------------------------------------
def parse_iv_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    sample_pattern = re.compile(r'Sample No\.\s*[\t,]\s*\d+', re.IGNORECASE)
    sample_starts = [m.start() for m in sample_pattern.finditer(content)]
    if not sample_starts:
        sample_pattern = re.compile(r'^\s*Sample[\s,:-]*\d+', re.IGNORECASE | re.MULTILINE)
        sample_starts = [m.start() for m in sample_pattern.finditer(content)]
    samples = []
    for i, start_pos in enumerate(sample_starts):
        end_pos = sample_starts[i+1] if i+1 < len(sample_starts) else len(content)
        sample_content = content[start_pos:end_pos].strip()
        if sample_content:
            samples.append(parse_single_sample(sample_content))
    return samples

def parse_single_sample(sample_content):
    lines = [line.strip() for line in sample_content.split('\n') if line.strip()]
    metadata = {}
    data_lines = []
    headers = None
    for line in lines:
        if '\t' in line:
            parts = [p.strip() for p in line.split('\t') if p.strip()]
        else:
            parts = [p.strip() for p in line.split(',') if p.strip()]
        if not parts:
            continue
        if len(parts) == 2 and not any(x in parts[0].lower() for x in ['v (v)', 'i (a)', 'p (w)']):
            metadata[parts[0]] = parts[1]
        elif parts[0].lower().startswith(('v (v)', 'v,')):
            headers = parts
        elif headers and len(parts) == len(headers):
            data_lines.append(parts)
    if headers and data_lines:
        df = pd.DataFrame(data_lines, columns=headers)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except ValueError:
                pass
        if 'P (W)' not in df.columns and 'V (V)' in df.columns and 'I (A)' in df.columns:
            df['P (W)'] = df['V (V)'] * df['I (A)']
    else:
        df = pd.DataFrame()
    return {'metadata': metadata, 'data': df}

def write_sample(file, sample):
    for key, value in sample['metadata'].items():
        file.write(f'"{key}","{value}"\n')
    if not sample['data'].empty:
        file.write(','.join(f'"{h}"' for h in sample['data'].columns) + '\n')
        for _, row in sample['data'].iterrows():
            file.write(','.join(f'"{v}"' if isinstance(v, str) else str(v) for v in row) + '\n')
    file.write("\n")

# ----------------------------------------------------------------------
# 2. Interactive sample selection (console)
# ----------------------------------------------------------------------
def parse_range_selection(prompt, max_samples):
    """Ask user for sample numbers (e.g., 1,3,5-10). Returns list of ints."""
    while True:
        inp = input(prompt).strip()
        if not inp:
            print("  Please enter at least one sample number.")
            continue
        try:
            selected = set()
            for part in inp.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    selected.update(range(start, end+1))
                else:
                    selected.add(int(part))
            selected = [s for s in selected if 1 <= s <= max_samples]
            if not selected:
                print(f"  No valid samples (1-{max_samples}). Try again.")
                continue
            return selected
        except ValueError:
            print("  Invalid format. Use numbers like 1,3,5-10")

def get_irradiation_values(selected_samples):
    """Ask for irradiation value for each selected sample; return dict."""
    irr = {}
    for s in selected_samples:
        val = input(f"  Irradiation for sample {s} (W/m²) [press Enter to skip]: ").strip()
        if val:
            try:
                irr[s] = float(val)
            except ValueError:
                print(f"    Invalid number, skipping irradiation for sample {s}.")
    return irr

def process_single_file(file_path):
    """Parse one raw CSV, ask for selections, write modified/unmodified CSVs."""
    print(f"\n=== Processing: {os.path.basename(file_path)} ===")
    samples = parse_iv_file(file_path)
    if not samples:
        print("  No samples found.")
        return None, None, {}

    # Show sample list
    print(f"  Found {len(samples)} samples:")
    for i, s in enumerate(samples, 1):
        meta = s['metadata']
        sample_no = meta.get('Sample No.', f'#{i}')
        date_time = meta.get('Date & Time', '')
        print(f"    {i}. Sample {sample_no} - {date_time}")

    # Select modified
    mod = parse_range_selection("  Enter MODIFIED sample numbers: ", len(samples))
    irr_mod = get_irradiation_values(mod)

    # Select unmodified
    unmod = parse_range_selection("  Enter UNMODIFIED sample numbers: ", len(samples))

    # Overlap check
    overlap = set(mod) & set(unmod)
    if overlap:
        print(f"  WARNING: Samples {sorted(overlap)} are in both groups.")
        proceed = input("  Continue anyway? (y/n): ").strip().lower()
        if proceed != 'y':
            print("  Skipping this file.")
            return None, None, {}

    # Write output files
    base = Path(file_path).stem
    out_dir = Path(file_path).parent
    mod_path = out_dir / f"{base}_Modified.csv"
    unmod_path = out_dir / f"{base}_Unmodified.csv"
    cnt = 1
    while mod_path.exists() or unmod_path.exists():
        mod_path = out_dir / f"{base}_Modified_{cnt}.csv"
        unmod_path = out_dir / f"{base}_Unmodified_{cnt}.csv"
        cnt += 1

    with open(mod_path, 'w', encoding='utf-8') as mf, \
         open(unmod_path, 'w', encoding='utf-8') as uf:
        mf.write('\ufeff')
        uf.write('\ufeff')
        for i, samp in enumerate(samples, 1):
            if i in mod:
                write_sample(mf, samp)
            elif i in unmod:
                write_sample(uf, samp)

    print(f"  Modified saved to: {mod_path}")
    print(f"  Unmodified saved to: {unmod_path}")
    return str(mod_path), str(unmod_path), irr_mod

# ----------------------------------------------------------------------
# 3. Aggregation into Excel summaries (same as before)
# ----------------------------------------------------------------------
def parse_iv_curve_file_metadata(filename):
    """Extract metadata from CSV files produced by write_sample."""
    samples = []
    current_sample = None
    with open(filename, 'r', encoding='utf-8-sig') as file:
        content = file.read()
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ('"Sample No."' in line and line.split(',')[0].endswith('"Sample No."')) or \
           (line.startswith('"Sample No."') or line.startswith('\ufeff"Sample No."') or \
            line.startswith('ï»¿"Sample No."')):
            if current_sample is not None:
                samples.append(current_sample)
            current_sample = {'metadata': {}}
            clean_line = line.replace('\ufeff', '').replace('ï»¿', '').strip()
            parts = clean_line.split(',')
            if len(parts) >= 2:
                current_sample['metadata']['Sample No.'] = parts[1].strip('"')
        elif current_sample is not None:
            if line == '"V (V)","I (A)","P (W)"':
                continue
            if line.startswith('"') and ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key = parts[0].strip('"')
                    value = parts[1].strip('"')
                    if value == '-------':
                        value = None
                    current_sample['metadata'][key] = value
    if current_sample is not None:
        samples.append(current_sample)
    return samples

def aggregate_csv_files(csv_files, irradiation_dict, output_excel):
    """Create summary Excel from list of CSV files and irradiation values."""
    vopen, vmax, imax, pmax = [], [], [], []
    for csvf in csv_files:
        samples = parse_iv_curve_file_metadata(csvf)
        for s in samples:
            meta = s['metadata']
            sample_no = meta.get('Sample No.', 'Unknown')
            date_time = meta.get('Date & Time', 'Unknown')
            vopen_val = meta.get('Vopen (V)')
            if vopen_val and vopen_val != '-------':
                vopen.append({'Sample No.': sample_no, 'Date & Time': date_time, 'Vopen (V)': float(vopen_val)})
            vmax_val = meta.get('Vmaxp (V)')
            if vmax_val and vmax_val != '-------':
                vmax.append({'Sample No.': sample_no, 'Date & Time': date_time, 'Vmax (V)': float(vmax_val)})
            imax_val = meta.get('Imaxp (A)')
            if imax_val and imax_val != '-------':
                imax.append({'Sample No.': sample_no, 'Date & Time': date_time, 'Imax (A)': float(imax_val)})
            pmax_val = meta.get('Pmax (W)')
            if pmax_val and pmax_val != '-------':
                pmax.append({'Sample No.': sample_no, 'Date & Time': date_time, 'Pmax (W)': float(pmax_val)})
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        if vopen: pd.DataFrame(vopen).to_excel(writer, sheet_name='Vopen', index=False)
        if vmax: pd.DataFrame(vmax).to_excel(writer, sheet_name='Vmax', index=False)
        if imax: pd.DataFrame(imax).to_excel(writer, sheet_name='Imax', index=False)
        if pmax: pd.DataFrame(pmax).to_excel(writer, sheet_name='Pmax', index=False)
        if irradiation_dict:
            irr_df = pd.DataFrame([{'Sample No.': k, 'Irradiation (W/m²)': v} for k,v in irradiation_dict.items()])
            irr_df.to_excel(writer, sheet_name='Irradiation', index=False)
        # Auto-fit columns
        for sheet in writer.sheets:
            ws = writer.sheets[sheet]
            for col in ws.columns:
                max_len = max((len(str(cell.value)) for cell in col), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_len+2, 50)
    print(f"  Created {output_excel}")

# ----------------------------------------------------------------------
# 4. Plotting (same as before, no GUI)
# ----------------------------------------------------------------------
def parse_mixed_date(date_str):
    if pd.isna(date_str):
        return pd.NaT
    date_str = str(date_str)
    fmts = ['%d-%m-%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%Y-%m-%d',
            '%m/%d/%Y %H:%M', '%Y/%m/%d %H:%M:%S']
    for fmt in fmts:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return pd.NaT

def load_sheet_data(excel_path, sheet_name, panel_name):
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
        if len(df.columns) < 3:
            return pd.DataFrame()
        date_col = df.columns[1]
        val_col = df.columns[2]
        out = df[[date_col, val_col]].copy()
        out.columns = ['Date & Time', 'Value']
        out['Panel'] = panel_name
        out['Parameter'] = sheet_name
        out['Date & Time'] = out['Date & Time'].apply(parse_mixed_date)
        out = out.dropna(subset=['Date & Time', 'Value'])
        return out
    except:
        return pd.DataFrame()

def create_comparative_plots(modified_excel, unmodified_excel, panel1_name, panel2_name, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    params = ['Vopen', 'Vmax', 'Imax', 'Pmax']
    units = {'Vopen':'V', 'Vmax':'V', 'Imax':'A', 'Pmax':'W'}
    titles = {'Vopen':'Open Circuit Voltage', 'Vmax':'Voltage at Max Power',
              'Imax':'Current at Max Power', 'Pmax':'Maximum Power'}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []

    for param in params:
        plt.figure(figsize=(10,6))
        has_data = False
        if os.path.exists(modified_excel):
            df_mod = load_sheet_data(modified_excel, param, panel1_name)
            if not df_mod.empty:
                plt.plot(df_mod['Date & Time'], df_mod['Value'], 'o-', label=panel1_name, color='blue')
                has_data = True
        if os.path.exists(unmodified_excel):
            df_unmod = load_sheet_data(unmodified_excel, param, panel2_name)
            if not df_unmod.empty:
                plt.plot(df_unmod['Date & Time'], df_unmod['Value'], 's--', label=panel2_name, color='red')
                has_data = True
        if has_data:
            plt.title(titles[param], fontsize=16)
            plt.ylabel(f'{param} ({units[param]})')
            plt.xlabel('Date & Time')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.gcf().autofmt_xdate()
        else:
            plt.text(0.5,0.5,f'No data for {param}', ha='center', va='center', transform=plt.gca().transAxes)
            plt.title(f'{titles[param]} (no data)')
        plt.tight_layout()
        out_path = os.path.join(output_folder, f'{param}_comparison_{ts}.png')
        plt.savefig(out_path, dpi=300)
        plt.close()
        saved.append(out_path)
    return saved

# ----------------------------------------------------------------------
# 5. Main console workflow
# ----------------------------------------------------------------------
def main():
    print("="*60)
    print("IV CURVE BATCH PROCESSOR (Console version)")
    print("="*60)

    # Step 1: locate raw CSV files
    folder = input("Folder containing raw IV curve CSV files: ").strip().strip('"')
    folder = Path(folder)
    if not folder.is_dir():
        print("Folder not found.")
        return
    raw_files = list(folder.glob("*.csv"))
    if not raw_files:
        print("No CSV files found in that folder.")
        return
    print(f"\nFound {len(raw_files)} CSV files.")

    # Step 2: process each file interactively
    all_modified_csvs = []
    all_unmodified_csvs = []
    all_irradiation = {}   # sample -> irradiation (from all files)
    for f in raw_files:
        mod_csv, unmod_csv, irr = process_single_file(str(f))
        if mod_csv:
            all_modified_csvs.append(mod_csv)
        if unmod_csv:
            all_unmodified_csvs.append(unmod_csv)
        all_irradiation.update(irr)

    if not all_modified_csvs and not all_unmodified_csvs:
        print("\nNo samples selected. Exiting.")
        return

    # Step 3: aggregate into Excel summaries
    out_folder = input("\nOutput folder for Excel summaries and plots: ").strip().strip('"')
    out_folder = Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)
    mod_excel = out_folder / "Modified_summary.xlsx"
    unmod_excel = out_folder / "Unmodified_summary.xlsx"

    if all_modified_csvs:
        aggregate_csv_files(all_modified_csvs, all_irradiation, mod_excel)
    if all_unmodified_csvs:
        aggregate_csv_files(all_unmodified_csvs, all_irradiation, unmod_excel)

    # Step 4: ask for panel names and create plots
    panel1 = input("\nName for MODIFIED panel (e.g., 'Treated'): ").strip() or "Modified"
    panel2 = input("Name for UNMODIFIED panel (e.g., 'Control'): ").strip() or "Unmodified"
    plot_dir = out_folder / "comparison_plots"
    plot_paths = create_comparative_plots(str(mod_excel), str(unmod_excel), panel1, panel2, str(plot_dir))

    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print(f"Modified summary: {mod_excel if all_modified_csvs else '(none)'}")
    print(f"Unmodified summary: {unmod_excel if all_unmodified_csvs else '(none)'}")
    print(f"Plots saved in: {plot_dir}")
    for p in plot_paths:
        print(f"  {os.path.basename(p)}")
    print("="*60)

if __name__ == "__main__":
    main()
