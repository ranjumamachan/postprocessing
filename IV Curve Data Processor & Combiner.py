import pandas as pd
import re
import os
from pathlib import Path

def get_csv_files():
    """
    Get multiple CSV files from user with validation
    """
    files = []
    print("Please enter the paths to the CSV files you want to process and combine.")
    print("Enter 'done' when finished.\n")
    
    while True:
        file_path = input(f"Enter path to CSV file #{len(files) + 1} (or 'done' to finish): ").strip().strip('"')
        
        if file_path.lower() == 'done':
            if len(files) < 1:
                print("Please enter at least 1 file to process.")
                continue
            break
        
        # Check if file exists and is CSV file
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            continue
        
        if not file_path.lower().endswith('.csv'):
            print(f"Error: '{file_path}' is not a CSV file.")
            continue
        
        files.append(file_path)
        print(f"Added: {file_path}")
    
    return files

def parse_iv_curve_file(filename):
    """
    Parse an IV curve file and extract metadata for all samples
    """
    samples = []
    current_sample = None
    
    # Read the entire file and remove BOM
    with open(filename, 'r', encoding='utf-8-sig') as file:
        content = file.read()
    
    # Process line by line
    lines = content.split('\n')
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Detect new sample
        if ('"Sample No."' in line and line.split(',')[0].endswith('"Sample No."')) or \
           (line.startswith('"Sample No."') or line.startswith('\ufeff"Sample No."') or \
            line.startswith('ï»¿"Sample No."')):
            
            # Save the current sample if it exists
            if current_sample is not None:
                samples.append(current_sample)
            
            # Start new sample
            current_sample = {
                'metadata': {},
                'data': [],
                'source_file': os.path.basename(filename)
            }
            
            # Clean the line from any BOM characters
            clean_line = line.replace('\ufeff', '').replace('ï»¿', '').strip()
            parts = clean_line.split(',')
            if len(parts) >= 2:
                sample_no = parts[1].strip('"')
                current_sample['metadata']['Sample No.'] = sample_no
            
        elif current_sample is not None:
            # Check if this is the data header line (skip data parsing since we only need metadata)
            if line == '"V (V)","I (A)","P (W)"':
                continue
            
            # Parse metadata lines (key-value pairs)
            if line.startswith('"') and ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key = parts[0].strip('"')
                    value = parts[1].strip('"')
                    # Handle missing values
                    if value == '-------':
                        value = None
                    current_sample['metadata'][key] = value

    # Add the final sample
    if current_sample is not None:
        samples.append(current_sample)
    
    return samples

def process_multiple_csv_files(csv_files, output_filename="combined_iv_curve_summary.xlsx"):
    """
    Process multiple CSV files and create a single combined Excel file
    """
    if not csv_files:
        raise ValueError("No CSV files provided")
    
    # Get the directory of the first file for output
    output_dir = os.path.dirname(csv_files[0])
    output_filepath = os.path.join(output_dir, output_filename)
    
    # Prepare data for each sheet across all files
    vopen_data = []
    vmax_data = []
    imax_data = []
    pmax_data = []
    
    total_samples = 0
    
    # Process each CSV file
    for file_idx, csv_file in enumerate(csv_files, 1):
        print(f"Processing file {file_idx}/{len(csv_files)}: {os.path.basename(csv_file)}")
        
        try:
            # Parse the CSV file
            samples = parse_iv_curve_file(csv_file)
            total_samples += len(samples)
            
            print(f"  Found {len(samples)} samples in this file")
            
            # Extract data for each sample
            for sample in samples:
                metadata = sample['metadata']
                source_file = sample['source_file']
                sample_no = metadata.get('Sample No.', f'Unknown_{total_samples}')
                date_time = metadata.get('Date & Time', 'Unknown')
                
                # Vopen sheet data
                vopen_value = metadata.get('Vopen (V)', None)
                if vopen_value and vopen_value != '-------':
                    vopen_data.append({
                        'Source File': source_file,
                        'Sample No.': sample_no,
                        'Date & Time': date_time,
                        'Vopen (V)': float(vopen_value) if vopen_value else None
                    })
                
                # Vmax sheet data
                vmax_value = metadata.get('Vmaxp (V)', None)
                if vmax_value and vmax_value != '-------':
                    vmax_data.append({
                        'Source File': source_file,
                        'Sample No.': sample_no,
                        'Date & Time': date_time,
                        'Vmax (V)': float(vmax_value) if vmax_value else None
                    })
                
                # Imax sheet data
                imax_value = metadata.get('Imaxp (A)', None)
                if imax_value and imax_value != '-------':
                    imax_data.append({
                        'Source File': source_file,
                        'Sample No.': sample_no,
                        'Date & Time': date_time,
                        'Imax (A)': float(imax_value) if imax_value else None
                    })
                
                # Pmax sheet data
                pmax_value = metadata.get('Pmax (W)', None)
                if pmax_value and pmax_value != '-------':
                    pmax_data.append({
                        'Source File': source_file,
                        'Sample No.': sample_no,
                        'Date & Time': date_time,
                        'Pmax (W)': float(pmax_value) if pmax_value else None
                    })
                    
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            continue
    
    # Create DataFrames
    df_vopen = pd.DataFrame(vopen_data)
    df_vmax = pd.DataFrame(vmax_data)
    df_imax = pd.DataFrame(imax_data)
    df_pmax = pd.DataFrame(pmax_data)
    
    # Create Excel writer
    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        # Write each DataFrame to a different sheet
        if not df_vopen.empty:
            df_vopen.to_excel(writer, sheet_name='Vopen', index=False)
        if not df_vmax.empty:
            df_vmax.to_excel(writer, sheet_name='Vmax', index=False)
        if not df_imax.empty:
            df_imax.to_excel(writer, sheet_name='Imax', index=False)
        if not df_pmax.empty:
            df_pmax.to_excel(writer, sheet_name='Pmax', index=False)
        
        # Auto-adjust column widths for all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return output_filepath, total_samples, len(df_vopen), len(df_vmax), len(df_imax), len(df_pmax)

def verify_output_file(output_filepath, total_samples, vopen_count, vmax_count, imax_count, pmax_count):
    """
    Verify the output file and show summary
    """
    if not os.path.exists(output_filepath):
        print("Error: Output file was not created successfully.")
        return
    
    print(f"\n{'='*60}")
    print("COMBINED EXCEL FILE CREATED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"File saved as: {output_filepath}")
    print(f"File size: {os.path.getsize(output_filepath)} bytes")
    
    # Show summary
    print(f"\nOverall Summary:")
    print(f"  Total CSV files processed: {len(csv_files)}")
    print(f"  Total samples found: {total_samples}")
    print(f"  Vopen measurements: {vopen_count}")
    print(f"  Vmax measurements: {vmax_count}")
    print(f"  Imax measurements: {imax_count}")
    print(f"  Pmax measurements: {pmax_count}")
    
    # Show sheet details
    try:
        excel_file = pd.ExcelFile(output_filepath)
        print(f"\nSheets in output file: {excel_file.sheet_names}")
        
        for sheet in excel_file.sheet_names:
            df = pd.read_excel(output_filepath, sheet_name=sheet)
            print(f"\n{sheet} sheet:")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Source files: {df['Source File'].nunique()} unique files")
            
            if 'Sample No.' in df.columns:
                print(f"  Unique samples: {df['Sample No.'].nunique()}")
            
            if len(df) > 0:
                print(f"  First few entries:")
                print(df.head(3).to_string(index=False))
                
    except Exception as e:
        print(f"Error reading output file: {e}")

# Main execution
if __name__ == "__main__":
    try:
        print("IV Curve Data Processor and Combiner")
        print("=" * 50)
        print("This will process multiple IV curve CSV files and create")
        print("a single Excel file with four sheets:")
        print("1. Vopen - Open Circuit Voltage")
        print("2. Vmax - Voltage at Maximum Power")
        print("3. Imax - Current at Maximum Power")
        print("4. Pmax - Maximum Power")
        print("=" * 50)
        
        # Get CSV files from user
        csv_files = get_csv_files()
        
        print(f"\nFiles to process:")
        for i, file_path in enumerate(csv_files, 1):
            print(f"{i}. {file_path}")
        
        # Process all CSV files and create combined Excel
        print(f"\nProcessing {len(csv_files)} CSV files...")
        output_file, total_samples, vopen_count, vmax_count, imax_count, pmax_count = process_multiple_csv_files(csv_files)
        
        # Verify and show summary
        verify_output_file(output_file, total_samples, vopen_count, vmax_count, imax_count, pmax_count)
        
        # Show the directory where the file was saved
        output_dir = os.path.dirname(output_file)
        print(f"\nOutput directory: {output_dir}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # This will ensure the window stays open
        print("\nProcessing complete! Press Enter to exit...")
        input()
