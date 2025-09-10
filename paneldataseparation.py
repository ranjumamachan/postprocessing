import pandas as pd
from pathlib import Path
import re
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

def parse_iv_file(file_path):
    """Parse IV curve file with metadata and multiple samples"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # More flexible sample pattern matching
    sample_pattern = re.compile(r'Sample No\.\s*[\t,]\s*\d+', re.IGNORECASE)
    sample_starts = [m.start() for m in sample_pattern.finditer(content)]
    
    if not sample_starts:
        # Alternative pattern if the first one didn't match
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
    """Parse a single sample's content into metadata and IV data"""
    lines = [line.strip() for line in sample_content.split('\n') if line.strip()]
    metadata = {}
    data_lines = []
    headers = None
    
    for line in lines:
        # Handle both tab and comma separated values
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
    
    # Create DataFrame for IV data
    if headers and data_lines:
        df = pd.DataFrame(data_lines, columns=headers)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except ValueError:
                pass
        
        # Calculate power if not present
        if 'P (W)' not in df.columns and 'V (V)' in df.columns and 'I (A)' in df.columns:
            df['P (W)'] = df['V (V)'] * df['I (A)']
    else:
        df = pd.DataFrame()
    
    return {'metadata': metadata, 'data': df}

def extract_key_parameters(samples):
    """Extract VOC, ISC, PMAX from samples"""
    results = []
    for sample in samples:
        metadata = sample['metadata']
        data = sample['data']
        
        # Get timestamp
        timestamp_str = metadata.get('Date & Time', '')
        try:
            timestamp = datetime.strptime(timestamp_str, '%d-%m-%Y %H:%M')
        except ValueError:
            timestamp = None
        
        # Extract VOC (Open Circuit Voltage)
        voc = None
        if 'Vopen (V)' in metadata:
            try:
                voc = float(metadata['Vopen (V)'].replace('-------', 'NaN'))
            except (ValueError, AttributeError):
                pass
        elif not data.empty and 'V (V)' in data.columns:
            voc = data['V (V)'].max()
        
        # Extract ISC (Short Circuit Current)
        isc = None
        if 'Ishort (A)' in metadata:
            try:
                isc = float(metadata['Ishort (A)'].replace('-------', 'NaN'))
            except (ValueError, AttributeError):
                pass
        elif not data.empty and 'I (A)' in data.columns:
            isc = data.loc[data['V (V)'].abs().idxmin(), 'I (A)']
        
        # Extract PMAX (Maximum Power)
        pmax = None
        if 'Pmax (W)' in metadata:
            try:
                pmax = float(metadata['Pmax (W)'].replace('-------', 'NaN'))
            except (ValueError, AttributeError):
                pass
        elif not data.empty and 'P (W)' in data.columns:
            pmax = data['P (W)'].max()
        
        results.append({
            'timestamp': timestamp,
            'Sample No': metadata.get('Sample No.', ''),
            'VOC': voc,
            'ISC': isc,
            'PMAX': pmax,
            'FF': (pmax/(voc*isc)) if (voc and isc and pmax) else None  # Fill Factor
        })
    
    return pd.DataFrame(results)

def plot_parameters(df, title_suffix=""):
    """Plot VOC, ISC, PMAX and FF against time"""
    if df.empty:
        print("No data available for plotting")
        return
    
    fig, axes = plt.subplots(4, 1, figsize=(12, 16), sharex=True)
    plt.suptitle(f'Solar Cell Parameters {title_suffix}', y=1.02)
    
    # Plot VOC
    axes[0].plot(df['timestamp'], df['VOC'], 'bo-', markerfacecolor='none')
    axes[0].set_ylabel('VOC (V)')
    axes[0].grid(True)
    axes[0].set_title('Open Circuit Voltage')
    
    # Plot ISC
    axes[1].plot(df['timestamp'], df['ISC'], 'ro-', markerfacecolor='none')
    axes[1].set_ylabel('ISC (A)')
    axes[1].grid(True)
    axes[1].set_title('Short Circuit Current')
    
    # Plot PMAX
    axes[2].plot(df['timestamp'], df['PMAX'], 'go-', markerfacecolor='none')
    axes[2].set_ylabel('PMAX (W)')
    axes[2].grid(True)
    axes[2].set_title('Maximum Power')
    
    # Plot Fill Factor
    axes[3].plot(df['timestamp'], df['FF'], 'mo-', markerfacecolor='none')
    axes[3].set_ylabel('Fill Factor')
    axes[3].grid(True)
    axes[3].set_title('Fill Factor')
    axes[3].set_xlabel('Time')
    
    plt.tight_layout()
    plt.show()

def write_sample(file, sample):
    """Write a sample to file with proper Excel-compatible CSV formatting"""
    # Write metadata with comma separation
    for key, value in sample['metadata'].items():
        file.write(f'"{key}","{value}"\n')
    
    # Write data with comma separation
    if not sample['data'].empty:
        # Write headers
        file.write(','.join(f'"{h}"' for h in sample['data'].columns) + '\n')
        # Write data rows
        for _, row in sample['data'].iterrows():
            file.write(','.join(f'"{v}"' if isinstance(v, str) else str(v) for v in row) + '\n')
    file.write("\n")  # Separate samples with blank line

def get_sample_selection(prompt, max_samples):
    """Get sample selection from user with validation"""
    while True:
        sample_input = input(prompt).strip()
        if not sample_input:
            print("Please enter at least one sample number.")
            continue
        
        try:
            selected = set()
            for part in sample_input.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    selected.update(range(start, end + 1))
                else:
                    selected.add(int(part))
            selected_samples = [s for s in selected if 1 <= s <= max_samples]
            if not selected_samples:
                print(f"No valid samples selected (1-{max_samples}). Please try again.")
                continue
            return selected_samples
        except ValueError:
            print("Invalid input format. Please use numbers like '1,3,5-10'.")

def process_samples():
    print("IV Curve Data Processor with Graphical Analysis")
    print("---------------------------------------------")
    
    # Get file path
    while True:
        file_path = input('Enter path to your IV curve data file: ').strip('"')
        if not file_path:
            print("Please enter a valid file path.")
            continue
        
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            continue
        break
    
    # Parse samples
    try:
        samples = parse_iv_file(file_path)
        if not samples:
            print("\nError: No samples found in the file. Please check the file format.")
            print("Make sure your file contains 'Sample No.' headers and proper IV curve data.")
            return
        
        # Extract key parameters
        params_df = extract_key_parameters(samples)
        print("\nExtracted Parameters:")
        print(params_df.to_string(index=False))
        
    except Exception as e:
        print(f"\nError reading file: {e}")
        return
    
    # Show available samples
    print(f"\nFound {len(samples)} samples:")
    for i, sample in enumerate(samples, 1):
        sample_no = sample['metadata'].get('Sample No.', f'#{i}')
        date_time = sample['metadata'].get('Date & Time', '')
        print(f"{i}. Sample {sample_no} - {date_time}")
    
    # Get Modified samples selection
    modified_samples = get_sample_selection(
        '\nEnter sample numbers for MODIFIED samples (comma/range format, e.g., 1,3,5-10): ',
        len(samples)
    )
    
    # Get Unmodified samples selection
    unmodified_samples = get_sample_selection(
        '\nEnter sample numbers for UNMODIFIED samples (comma/range format, e.g., 2,4,6-8): ',
        len(samples)
    )
    
    # Check for overlapping selections
    overlap = set(modified_samples) & set(unmodified_samples)
    if overlap:
        print(f"\nWarning: Samples {sorted(overlap)} appear in both selections!")
        proceed = input("Continue anyway? (y/n): ").lower()
        if proceed != 'y':
            print("Processing cancelled.")
            return
    
    # Prepare output paths
    base_name = file_path.stem
    output_dir = file_path.parent
    
    # Create output files
    modified_path = output_dir / f"{base_name}_Modified.csv"
    unmodified_path = output_dir / f"{base_name}_Unmodified.csv"
    
    # Add counter if files exist
    counter = 1
    while modified_path.exists() or unmodified_path.exists():
        modified_path = output_dir / f"{base_name}_Modified_{counter}.csv"
        unmodified_path = output_dir / f"{base_name}_Unmodified_{counter}.csv"
        counter += 1
    
    # Write output files
    try:
        with open(modified_path, 'w', encoding='utf-8') as mod_file, \
             open(unmodified_path, 'w', encoding='utf-8') as unmod_file:
            
            # Write UTF-8 BOM for Excel compatibility
            mod_file.write('\ufeff')
            unmod_file.write('\ufeff')
            
            for i, sample in enumerate(samples, 1):
                if i in modified_samples:
                    write_sample(mod_file, sample)
                elif i in unmodified_samples:
                    write_sample(unmod_file, sample)
        
        print("\nProcessing successful!")
        print(f"Modified samples saved to: {modified_path}")
        print(f"Unmodified samples saved to: {unmodified_path}")
        
        # Generate plots for each category
        modified_params = params_df.iloc[[i-1 for i in modified_samples]]
        unmodified_params = params_df.iloc[[i-1 for i in unmodified_samples]]
        
        if not modified_params.empty:
            print("\nPlotting Modified Samples...")
            plot_parameters(modified_params, "(Modified Samples)")
        if not unmodified_params.empty:
            print("\nPlotting Unmodified Samples...")
            plot_parameters(unmodified_params, "(Unmodified Samples)")
        
    except PermissionError:
        print(f"\nError: Could not write to output files. Please check permissions for:")
        print(f"- {modified_path}")
        print(f"- {unmodified_path}")
    except Exception as e:
        print(f"\nError during file writing: {e}")

if __name__ == "__main__":
    process_samples()
