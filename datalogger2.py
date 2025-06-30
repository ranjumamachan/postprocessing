import pandas as pd
import matplotlib.pyplot as plt
import os
from fnmatch import fnmatch
from matplotlib.dates import DateFormatter

# Configuration
INPUT_DIR = r"D:\\PhD\\similarity\\temperatures\\day 2"
FILE_PATTERN = "day 2 *.xlsx"
LOWER_THRESHOLD = 30
UPPER_THRESHOLD = 85
OUTPUT_DIR = r"D:\PhD\similarity\processed"

def process_file(filepath):
    """Process a single Excel file and return cleaned DataFrame"""
    df = pd.read_excel(filepath)
    
    # Create proper datetime column
    try:
        df['DateTime'] = pd.to_datetime(df['Date:'].astype(str) + ' ' + df['Time:'].astype(str))
    except:
        print(f"Could not parse timestamps in {filepath}")
        return None
    
    # Clean temperature data
    for i in list(range(1, 6)) + list(range(11, 16)):
        channel = f"Channel - {i}"
        if channel in df.columns:
            df[channel] = pd.to_numeric(df[channel], errors='coerce')
            df[channel] = df[channel].where((df[channel] >= LOWER_THRESHOLD) & 
                                          (df[channel] <= UPPER_THRESHOLD))
    return df

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Find and process all files
    file_paths = [os.path.join(INPUT_DIR, f) 
                 for f in os.listdir(INPUT_DIR) 
                 if fnmatch(f.lower(), FILE_PATTERN.lower())]
    
    if not file_paths:
        print(f"No files found matching: {FILE_PATTERN}")
        return
    
    # Process all files and combine
    df_list = []
    for filepath in sorted(file_paths):
        df = process_file(filepath)
        if df is not None:
            df_list.append(df)
    
    if not df_list:
        print("No valid data found in any files")
        return
    
    combined_df = pd.concat(df_list).sort_values('DateTime')
    
    # Create time-only strings for x-axis labels
    combined_df['TimeLabel'] = combined_df['DateTime'].dt.strftime('%H:%M:%S')
    
    # Plotting
    plt.figure(figsize=(18, 10))
    
    # Panel 1
    plt.subplot(2, 1, 1)
    for i in range(1, 6):
        channel = f"Channel - {i}"
        if channel in combined_df.columns:
            plt.plot(combined_df['DateTime'], 
                    combined_df[channel],
                    label=channel, linewidth=1.5)
    plt.title('Panel 1 - Temperature Data')
    plt.ylabel('Temperature (°C)')
    plt.ylim(LOWER_THRESHOLD-5, UPPER_THRESHOLD+5)
    
    # Format x-axis to show time only
    plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
    plt.gcf().autofmt_xdate()  # Rotate labels
    
    plt.legend()
    plt.grid(True)
    
    # Panel 2
    plt.subplot(2, 1, 2)
    for i in range(11, 16):
        channel = f"Channel - {i}"
        if channel in combined_df.columns:
            plt.plot(combined_df['DateTime'], 
                    combined_df[channel],
                    label=channel, linewidth=1.5)
    plt.title('Panel 2 - Temperature Data')
    plt.xlabel('Time (HH:MM:SS)')
    plt.ylabel('Temperature (°C)')
    plt.ylim(LOWER_THRESHOLD-5, UPPER_THRESHOLD+5)
    
    # Same x-axis formatting
    plt.gca().xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
    plt.gcf().autofmt_xdate()  # Rotate labels
    
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # Save plot
    plot_path = os.path.join(OUTPUT_DIR, "time_plot.png")
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.show()
    print(f"Time plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
