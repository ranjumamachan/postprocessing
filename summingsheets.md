# IV Curve Data Summary Generator

This script processes IV curve data exported as CSV files, typically generated from photovoltaic or electronic measurement systems. It is designed to extract relevant metadata and summary statistics from one or more samples contained within a single file, and then create a structured Excel summary for easy review and further analysis.

## Input

- **Format:** The input must be a CSV file containing IV curve measurement data for one or more samples.  
- **Content:** Each sample in the file should have labeled metadata such as `"Sample No."`, `"Date & Time"`, `"Vopen (V)"`, `"Vmaxp (V)"`, `"Imaxp (A)"`, `"Pmax (W)"`, and potentially other key-value pairs. The data for each sample is typically separated by header-like lines indicating the beginning of a new sample.
- **Encoding:** UTF-8 with or without BOM is supported.
- **How to specify:** Upon running the script, you will be prompted to enter the full path to the CSV file. You can type or drag-and-drop the file path into the terminal.

## Output

- **Excel Workbook (.xlsx):**  
  The script creates a summary Excel file named `iv_curve_summary.xlsx` in the same directory as the input file.
- **Sheets:**  
  The output Excel contains four sheets, one for each major measurement:
  1. **Vopen:** Open-circuit voltage for each sample
  2. **Vmax:** Voltage at maximum power point for each sample
  3. **Imax:** Current at maximum power point for each sample
  4. **Pmax:** Maximum power for each sample
- **Sheet Structure:**  
  Each sheet includes:
  - Sample No.
  - Date & Time
  - The corresponding measurement value (Vopen, Vmax, Imax, or Pmax)
- **Formatting:**  
  Columns are auto-sized for readability.

## How It Works

1. **Prompt for Input:**  
   The script prompts the user to specify the CSV file location and validates its existence.
2. **Parse File:**  
   It reads the file, detects each sample section, and extracts relevant metadata. Missing or placeholder values (such as `-------`) are handled gracefully and replaced with `None`.
3. **Extract and Structure Data:**  
   For each sample, the script collects values for Vopen, Vmax, Imax, and Pmax, along with sample number and date/time.
4. **Write Output:**  
   All extracted data is written to an Excel file, with one sheet per measurement type.
5. **Summary:**  
   After processing, the script displays a summary in the terminal, including the count of samples per sheet and a preview of the output.

## Example Usage

- **Input:**  
  A CSV file with multiple samples, each starting with a header such as `"Sample No.",<number>`, followed by lines with key-value pairs and a data section.

- **Output:**  
  An Excel file with four sheets, each listing all samples and their respective measurement values, ready for further data analysis.

## Typical Workflow

1. Run the script in your terminal.
2. Enter or drag-and-drop the CSV file path when prompted.
3. Wait for the script to parse, process, and create the summary.
4. Open the `iv_curve_summary.xlsx` file in Excel (or another spreadsheet tool) for review.

## Use Cases

- Summarizing IV curve measurements from photovoltaic cell testing
- Quickly extracting key parameters from batch measurement exports
- Preparing clean datasets for reporting or further scientific analysis

---
**Note:** This script is designed for users who need to automate the extraction and summarization of IV curve data from instrument exports, reducing manual effort and errors.
