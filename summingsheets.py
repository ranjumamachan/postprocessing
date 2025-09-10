import pandas as pd
import re
import os

def get_file_path():
    """
    Prompt user for file path with validation
    """
    while True:
        file_path = input("Please enter the full path to your CSV file: ").strip().strip('"')
        
        # Check if file exists
        if os.path.exists(file_path):
            return file_path
        else:
            print(f"Error: File '{file_path}' not found.")
            print("Please make sure you enter the full path including the file extension.")
            print("Example: C:\\Users\\YourName\\Documents\\day 1 first part_Modified.csv")
            print("Or drag and drop the file into the terminal window.\n")

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
                'data': []
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

def create_excel_summary(samples, input_file_path, output_filename="iv_curve_summary.xlsx"):
    """
    Create Excel file with four sheets: Vopen, Vmax, Imax, Pmax
    Save in the same folder as the input file
    """
    # Get the directory of the input file
    input_dir = os.path.dirname(input_file_path)
    output_filepath = os.path.join(input_dir, output_filename)
    
    # Prepare data for each sheet
    vopen_data = []
    vmax_data = []
    imax_data = []
    pmax_data = []
    
    for sample in samples:
        metadata = sample['metadata']
        sample_no = metadata.get('Sample No.', 'Unknown')
        date_time = metadata.get('Date & Time', 'Unknown')
        
        # Vopen sheet data
        vopen_value = metadata.get('Vopen (V)', None)
        if vopen_value and vopen_value != '-------':
            vopen_data.append({
                'Sample No.': sample_no,
                'Date & Time': date_time,
                'Vopen (V)': float(vopen_value) if vopen_value else None
            })
        
        # Vmax sheet data
        vmax_value = metadata.get('Vmaxp (V)', None)
        if vmax_value and vmax_value != '-------':
            vmax_data.append({
                'Sample No.': sample_no,
                'Date & Time': date_time,
                'Vmax (V)': float(vmax_value) if vmax_value else None
            })
        
        # Imax sheet data
        imax_value = metadata.get('Imaxp (A)', None)
        if imax_value and imax_value != '-------':
            imax_data.append({
                'Sample No.': sample_no,
                'Date & Time': date_time,
                'Imax (A)': float(imax_value) if imax_value else None
            })
        
        # Pmax sheet data
        pmax_value = metadata.get('Pmax (W)', None)
        if pmax_value and pmax_value != '-------':
            pmax_data.append({
                'Sample No.': sample_no,
                'Date & Time': date_time,
                'Pmax (W)': float(pmax_value) if pmax_value else None
            })
    
    # Create DataFrames
    df_vopen = pd.DataFrame(vopen_data)
    df_vmax = pd.DataFrame(vmax_data)
    df_imax = pd.DataFrame(imax_data)
    df_pmax = pd.DataFrame(pmax_data)
    
    # Create Excel writer
    with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
        # Write each DataFrame to a different sheet
        df_vopen.to_excel(writer, sheet_name='Vopen', index=False)
        df_vmax.to_excel(writer, sheet_name='Vmax', index=False)
        df_imax.to_excel(writer, sheet_name='Imax', index=False)
        df_pmax.to_excel(writer, sheet_name='Pmax', index=False)
        
        # Auto-adjust column widths
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
    
    return output_filepath

# Main execution
if __name__ == "__main__":
    print("IV Curve Data Summary Generator")
    print("=" * 50)
    print("This will create an Excel file with four sheets:")
    print("1. Vopen - Open Circuit Voltage")
    print("2. Vmax - Voltage at Maximum Power")
    print("3. Imax - Current at Maximum Power")
    print("4. Pmax - Maximum Power")
    print("=" * 50)
    
    # Get file path from user
    input_file_path = get_file_path()
    
    print(f"\nReading file: {input_file_path}")
    
    try:
        # Read the file first to count lines
        with open(input_file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        print(f"File has {len(lines)} lines")
        
        # Parse the file
        print("\nParsing file and extracting metadata...")
        samples = parse_iv_curve_file(input_file_path)
        
        print(f"Found {len(samples)} samples")
        
        if samples:
            # Create Excel summary in the same folder as input file
            excel_file = create_excel_summary(samples, input_file_path, "iv_curve_summary.xlsx")
            
            # Show summary of what was extracted
            print(f"\n{'='*60}")
            print("EXCEL FILE CREATED SUCCESSFULLY!")
            print(f"{'='*60}")
            print(f"File saved as: {excel_file}")
            print(f"File size: {os.path.getsize(excel_file)} bytes")
            
            # Show sample count for each sheet
            print(f"\nSample counts per sheet:")
            df_vopen = pd.read_excel(excel_file, sheet_name='Vopen')
            df_vmax = pd.read_excel(excel_file, sheet_name='Vmax')
            df_imax = pd.read_excel(excel_file, sheet_name='Imax')
            df_pmax = pd.read_excel(excel_file, sheet_name='Pmax')
            
            print(f"  Vopen sheet: {len(df_vopen)} samples")
            print(f"  Vmax sheet: {len(df_vmax)} samples")
            print(f"  Imax sheet: {len(df_imax)} samples")
            print(f"  Pmax sheet: {len(df_pmax)} samples")
            
            # Show first few rows of each sheet
            print(f"\nFirst few rows of Vopen sheet:")
            print(df_vopen.head().to_string(index=False))
            
            print(f"\nExcel file structure:")
            print("Each sheet has:")
            print("  - Column 1: Sample No.")
            print("  - Column 2: Date & Time")
            print("  - Column 3: Measurement value (Vopen, Vmax, Imax, or Pmax)")
            
            # Show the directory where the file was saved
            output_dir = os.path.dirname(excel_file)
            print(f"\nOutput directory: {output_dir}")
            
        else:
            print("No samples found in the file!")
            
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nProcessing complete! The Excel file has been created.")
    print("Press Enter to exit...")
    input()
