# IV Curve Data Processor & Combiner

## 📊 Overview

**IV Curve Data Processor & Combiner** is a powerful Python tool designed to streamline the analysis of multiple IV curve measurement files. This tool automatically processes CSV files containing solar cell or semiconductor characterization data, extracts key performance parameters, and consolidates everything into a single, well-organized Excel file with multiple sheets for comprehensive analysis.

## 🚀 Key Features

- **Multi-File Processing**: Handle multiple CSV files simultaneously
- **Automated Data Extraction**: Parse IV curve metadata including Vopen, Vmax, Imax, and Pmax
- **Smart Organization**: Outputs a single Excel file with four organized sheets
- **Source Tracking**: Includes source file information for traceability
- **Auto-Formatting**: Intelligent column width adjustment and data validation
- **Error Resilience**: Robust error handling for corrupt or malformed files

## 📋 Output Structure

The tool generates an Excel file with four clearly organized sheets:

| Sheet Name | Measurement | Description |
|------------|-------------|-------------|
| **Vopen** | Open Circuit Voltage | Voltage when current is zero |
| **Vmax** | Voltage at Max Power | Voltage at maximum power point |
| **Imax** | Current at Max Power | Current at maximum power point |
| **Pmax** | Maximum Power | Highest power output value |

Each sheet includes:
- Source file name
- Sample identification number
- Date and time of measurement
- Corresponding measurement value

## 🛠️ Technical Details

### Requirements
```bash
pip install pandas openpyxl
```

### Supported Input Format
- CSV files with IV curve measurement data
- Standard IV curve instrument output format
- Handles BOM characters and various encoding issues

### Error Handling
- Gracefully handles missing values (`-------`)
- Skips corrupt files while processing others
- Provides detailed error reporting

## 📈 Use Cases

- **Solar Cell Research**: Analyze multiple PV device measurements
- **Quality Control**: Batch process production line test data
- **Academic Research**: Consolidate experimental results from multiple sessions
- **Data Analysis**: Prepare clean datasets for statistical analysis

## 🎯 Benefits

- **Time Savings**: Process hundreds of files in minutes instead of hours
- **Data Integrity**: Maintain original data structure with source tracking
- **Analysis Ready**: Output formatted for immediate use in Excel, Python, or other tools
- **User Friendly**: Simple command-line interface with guided prompts

## 📊 Sample Output

```
Combined Excel File: combined_iv_curve_summary.xlsx
├── Vopen Sheet (150 rows)
├── Vmax Sheet (150 rows) 
├── Imax Sheet (150 rows)
└── Pmax Sheet (150 rows)

Total processed: 3 CSV files, 45 samples
```

## 🔧 Installation & Usage

1. Install requirements: `pip install pandas openpyxl`
2. Run the script: `python iv_curve_processor.py`
3. Follow the prompts to select CSV files
4. Get your combined Excel file automatically!

---

*Perfect for researchers, engineers, and students working with electrical characterization data!*
