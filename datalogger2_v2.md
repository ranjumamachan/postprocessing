# Data Logger v2 - Temperature Data Processing and Visualization

## Overview

`datalogger2_v2.py` is an enhanced version of the original data logger script that processes Excel files containing temperature sensor data from multiple channels across two panels. The script reads temperature data, validates it against predefined thresholds, calculates panel-wise averages, and generates comparison visualizations.

## What the Code Does

1. **Data Loading**: Reads Excel files matching a specific date pattern (dd-mm-yyyy format)
2. **Data Validation**: 
   - Parses and validates DateTime columns from Date and Time fields
   - Filters temperature readings based on lower (30°C) and upper (85°C) thresholds
   - Converts all temperature values to numeric format
3. **Data Aggregation**: 
   - Combines data from multiple Excel files
   - Calculates average temperature for Panel 1 (Channels 3, 4, 5, 7)
   - Calculates average temperature for Panel 2 (Channels 9, 10, 11, 12)
4. **Visualization**: 
   - Creates a single comparison plot showing both panel averages over time
   - Exports data to CSV format for further analysis

## Inputs

The script is interactive and prompts you for the following inputs:

### 1. **Date Format (dd-mm-yyyy)**
   - **Prompt**: "Enter the date of the Excel files (dd-mm-yyyy format):"
   - **Example**: `25-05-2026`
   - **Purpose**: Used to construct the file search pattern (e.g., "25-05-2026 *.xlsx")
   - **Validation**: Script validates the date format and rejects invalid entries

### 2. **Input Directory Path**
   - **Prompt**: "Enter the path to the folder containing Excel files:"
   - **Example**: `D:\PhD\similarity\temperatures\day 2` or `/home/user/data/temperatures`
   - **Purpose**: Location where Excel files matching the date pattern are stored
   - **Validation**: Script checks if the directory exists

### 3. **Output Directory Path**
   - **Prompt**: "Enter the path to the output folder (will be created if it doesn't exist):"
   - **Example**: `D:\PhD\similarity\processed` or `/home/user/output`
   - **Purpose**: Where processed plots and CSV files will be saved
   - **Note**: Directory is automatically created if it doesn't exist

### Excel File Format Requirements

Excel files should have the following structure:
- Column: `Record No.` - Sequential record numbers
- Column: `Date:` - Date in dd-mm-yyyy format
- Column: `Time:` - Time in HH:MM:SS format
- Columns: `Channel - 3`, `Channel - 4`, `Channel - 5`, `Channel - 7`, `Channel - 9`, `Channel - 10`, `Channel - 11`, `Channel - 12` - Temperature readings

## Outputs

The script generates the following outputs in the specified output directory:

### 1. **temperature_average_comparison.png**
   - **Type**: Line plot (PNG image, 300 DPI)
   - **Content**: 
     - X-axis: Time in HH:MM:SS format
     - Y-axis: Temperature in °C
     - Two lines: One for Panel 1 Average, one for Panel 2 Average
   - **Features**: 
     - Markers on data points (circles for Panel 1, squares for Panel 2)
     - Grid enabled for easy reading
     - Legend identifying each line
     - Temperature range: 25°C to 90°C (based on thresholds ±5°C)

### 2. **temperature_averages.csv**
   - **Type**: Comma-separated values file
   - **Content**: Three columns
     - `DateTime`: Full timestamp (YYYY-MM-DD HH:MM:SS)
     - `Panel_1_Avg`: Average temperature of Panel 1 channels at that instant
     - `Panel_2_Avg`: Average temperature of Panel 2 channels at that instant
   - **Use**: Can be imported into Excel, data analysis tools, or other applications

### Console Output

The script prints status messages to the console:
- Number of files found
- Name of each file being processed
- Location where outputs are saved

## Configuration Constants

- `LOWER_THRESHOLD = 30` - Minimum valid temperature (°C)
- `UPPER_THRESHOLD = 85` - Maximum valid temperature (°C)
- `CHANNELS = [3, 4, 5, 7, 9, 10, 11, 12]` - All sensor channels
- `PANEL_1_CHANNELS = [3, 4, 5, 7]` - Channels grouped in Panel 1
- `PANEL_2_CHANNELS = [9, 10, 11, 12]` - Channels grouped in Panel 2

## Error Handling

The script validates inputs and provides helpful error messages:
- Invalid date format: Prompts user to re-enter in correct format
- Invalid directory path: Asks user to provide a valid existing directory
- Missing Excel files: Alerts user if no files match the specified date pattern
- Corrupted data: Skips records with unparseable timestamps or invalid data

## Dependencies

- `pandas` - Data manipulation and Excel file reading
- `matplotlib` - Plotting and visualization
- `os` - File system operations
- `fnmatch` - Pattern matching for file names
- `datetime` - Date validation

## Usage Example

```bash
python datalogger2_v2.py
```

Then follow the interactive prompts:
```
Enter the date of the Excel files (dd-mm-yyyy format): 25-05-2026
Enter the path to the folder containing Excel files: D:\PhD\similarity\temperatures\day 2
Enter the path to the output folder (will be created if it doesn't exist): D:\PhD\similarity\processed
Found 5 file(s). Processing...
Processing: 25-05-2026 data1.xlsx
Processing: 25-05-2026 data2.xlsx
...
Temperature comparison plot saved to: D:\PhD\similarity\processed\temperature_average_comparison.png
Temperature averages data saved to: D:\PhD\similarity\processed\temperature_averages.csv
```

## Key Differences from v1

- Supports new Excel format with specific channel numbers (3, 4, 5, 7, 9, 10, 11, 12)
- Accepts user input for date, input directory, and output directory
- Calculates and plots panel averages instead of individual channels
- Single comparison plot showing both panels on same graph
- Exports averaged data to CSV file
- Improved error handling and user feedback
