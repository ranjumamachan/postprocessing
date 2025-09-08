import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import numpy as np

def get_file_path(prompt):
    """
    Prompt user for file path with validation
    """
    while True:
        file_path = input(prompt).strip().strip('"')
        
        # Check if file exists
        if os.path.exists(file_path):
            return file_path
        else:
            print(f"Error: File '{file_path}' not found.")
            print("Please make sure you enter the full path including the file extension.\n")

def parse_mixed_date(date_str):
    """
    Handle mixed date formats: DD-MM-YYYY and YYYY-MM-DD
    """
    if pd.isna(date_str):
        return pd.NaT
    
    # Convert to string if it's not already
    date_str = str(date_str)
    
    # Try different date formats
    date_formats = [
        '%d-%m-%Y %H:%M',    # DD-MM-YYYY HH:MM
        '%Y-%m-%d %H:%M:%S', # YYYY-MM-DD HH:MM:SS
        '%d-%m-%Y',          # DD-MM-YYYY
        '%Y-%m-%d',          # YYYY-MM-DD
        '%m/%d/%Y %H:%M',    # MM/DD/YYYY HH:MM
        '%Y/%m/%d %H:%M:%S', # YYYY/MM/DD HH:MM:SS
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, return NaT
    return pd.NaT

def load_sheet_data(file_path, sheet_name, panel_name):
    """
    Load data from a specific sheet and handle mixed date formats
    """
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"Loaded {sheet_name} sheet: {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        print(f"First few date values: {df.iloc[:, 1].head().tolist()}")
        
        # Find the parameter column (usually the third column)
        param_col = None
        if len(df.columns) >= 3:
            param_col = df.columns[2]
            print(f"Using parameter column: '{param_col}'")
        
        # Find date column (usually the second column)
        date_col = None
        if len(df.columns) >= 2:
            date_col = df.columns[1]
            print(f"Using date column: '{date_col}'")
        
        if param_col and date_col:
            # Create clean dataframe
            clean_df = df[[date_col, param_col]].copy()
            clean_df.columns = ['Date & Time', 'Value']
            clean_df['Panel'] = panel_name
            clean_df['Parameter'] = sheet_name
            
            # Handle mixed date formats
            print("Converting dates...")
            clean_df['Date & Time'] = clean_df['Date & Time'].apply(parse_mixed_date)
            
            # Remove rows where either date or parameter value is missing
            initial_count = len(clean_df)
            clean_df = clean_df.dropna(subset=['Date & Time', 'Value'])
            final_count = len(clean_df)
            
            print(f"  Clean data points: {final_count} (removed {initial_count - final_count} rows with missing data)")
            
            if not clean_df.empty:
                print(f"  Date range: {clean_df['Date & Time'].min()} to {clean_df['Date & Time'].max()}")
                print(f"  Value range: {clean_df['Value'].min():.3f} to {clean_df['Value'].max():.3f}")
            
            return clean_df
        else:
            print(f"  Not enough columns for {sheet_name}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error loading {sheet_name} sheet: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def load_all_data(file_path, panel_name):
    """
    Load data from all sheets in the Excel file
    """
    data = {}
    
    # First, get all sheet names
    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        print(f"\nSheets found in {panel_name}: {sheet_names}")
    except Exception as e:
        print(f"Error reading sheet names: {e}")
        sheet_names = ['Vopen', 'Vmax', 'Imax', 'Pmax']
    
    for sheet_name in sheet_names:
        print(f"\nProcessing {sheet_name} sheet...")
        df = load_sheet_data(file_path, sheet_name, panel_name)
        if not df.empty:
            data[sheet_name] = df
    
    return data

def create_comparative_plots(panel1_data, panel2_data, output_folder, panel1_name, panel2_name):
    """
    Create comparative plots for all four parameters
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # Create a figure with 4 subplots (2x2 grid)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Panel Performance Comparison', fontsize=16, fontweight='bold')
    
    parameters = ['Vopen', 'Vmax', 'Imax', 'Pmax']
    units = {'Vopen': 'V', 'Vmax': 'V', 'Imax': 'A', 'Pmax': 'W'}
    titles = {
        'Vopen': 'Open Circuit Voltage (Vopen)',
        'Vmax': 'Voltage at Maximum Power (Vmax)',
        'Imax': 'Current at Maximum Power (Imax)',
        'Pmax': 'Maximum Power (Pmax)'
    }
    
    for i, param in enumerate(parameters):
        ax = axes[i//2, i%2]  # Get the appropriate subplot
        
        has_data = False
        
        # Plot Panel 1 data
        if param in panel1_data and not panel1_data[param].empty:
            df1 = panel1_data[param]
            ax.plot(df1['Date & Time'], df1['Value'], 
                   marker='o', linestyle='-', linewidth=2, markersize=6,
                   label=panel1_name, color='blue', alpha=0.8)
            has_data = True
            print(f"Panel 1 {param}: {len(df1)} data points")
        
        # Plot Panel 2 data
        if param in panel2_data and not panel2_data[param].empty:
            df2 = panel2_data[param]
            ax.plot(df2['Date & Time'], df2['Value'], 
                   marker='s', linestyle='--', linewidth=2, markersize=6,
                   label=panel2_name, color='red', alpha=0.8)
            has_data = True
            print(f"Panel 2 {param}: {len(df2)} data points")
        
        if has_data:
            # Customize the subplot
            ax.set_title(titles[param], fontsize=12, fontweight='bold')
            ax.set_xlabel('Date & Time', fontsize=10)
            ax.set_ylabel(f'{param} ({units[param]})', fontsize=10)
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels for better readability
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            # Format y-axis to show 2 decimal places
            ax.yaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
            
            # Set better x-axis limits if we have data
            all_dates = []
            if param in panel1_data:
                all_dates.extend(panel1_data[param]['Date & Time'].tolist())
            if param in panel2_data:
                all_dates.extend(panel2_data[param]['Date & Time'].tolist())
            
            if all_dates:
                min_date = min(all_dates)
                max_date = max(all_dates)
                date_range = (max_date - min_date).total_seconds()
                if date_range > 0:  # Only set limits if we have a valid date range
                    ax.set_xlim(min_date, max_date)
        else:
            ax.text(0.5, 0.5, f'No data for {param}', 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(titles[param], fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    # Save the figure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_folder, f'panel_comparison_{timestamp}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()
    
    return output_path

def main():
    print("Panel Performance Comparison Tool")
    print("=" * 50)
    print("This tool will create comparative graphs for two panels")
    print("Parameters: Vopen, Vmax, Imax, Pmax vs Date & Time")
    print("=" * 50)
    
    # Get file paths
    file1_path = get_file_path("Enter path to first panel's Excel file: ")
    file2_path = get_file_path("Enter path to second panel's Excel file: ")
    
    # Get panel names
    panel1_name = input("Enter name for first panel (e.g., 'Panel A'): ").strip() or "Panel 1"
    panel2_name = input("Enter name for second panel (e.g., 'Panel B'): ").strip() or "Panel 2"
    
    # Output folder
    output_folder = input("Enter output folder path (press Enter for current directory): ").strip()
    if not output_folder:
        output_folder = "comparison_results"
    
    print("\nLoading data...")
    
    try:
        # Load data from both files
        panel1_data = load_all_data(file1_path, panel1_name)
        panel2_data = load_all_data(file2_path, panel2_name)
        
        print("\nData loaded successfully!")
        print(f"Panel 1 data summary:")
        for param, df in panel1_data.items():
            print(f"  {param}: {len(df)} data points")
        
        print(f"Panel 2 data summary:")
        for param, df in panel2_data.items():
            print(f"  {param}: {len(df)} data points")
        
        # Create comparative plots
        print("\nCreating comparative graphs...")
        plot_path = create_comparative_plots(panel1_data, panel2_data, output_folder, panel1_name, panel2_name)
        print(f"Comparative graphs saved to: {plot_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nComparison complete! Press Enter to exit...")
    input()

if __name__ == "__main__":
    main()
