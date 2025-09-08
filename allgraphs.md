# Panel Performance Comparison Tool

This Python script provides a command-line tool for comparing the performance of two solar panels (or similar systems) based on their electrical parameter data stored in Excel files. It generates comparative plots for key parameters over time, helping users visually analyze and compare the operation of two panels.

## Features

- Loads data from Excel files, supporting multiple date formats.
- Handles missing or malformed data gracefully.
- Plots four parameters for both panels:  
  - Vopen: Open Circuit Voltage  
  - Vmax: Voltage at Maximum Power  
  - Imax: Current at Maximum Power  
  - Pmax: Maximum Power
- Generates a single image file containing all comparison graphs.
- User-friendly command-line interface with prompts and helpful messages.

## **Input**

- **Two Excel files** (one for each panel) containing measurement data.
  - Each Excel file can have multiple sheets, with each sheet representing a parameter (e.g., Vopen, Vmax, etc.).
  - Each sheet must contain at least three columns: an index, a date/time column, and a value column.
  - Date/time values can be in various formats (e.g., `DD-MM-YYYY` or `YYYY-MM-DD`).
- **Panel Names:** User-provided names for the two panels (used in plot legends).
- **Output Folder:** Optional user-defined folder for the results.

<img width="1088" height="699" alt="image" src="https://github.com/user-attachments/assets/a88269b4-6b83-46d8-88cd-2f00e2a01f75" />


## **Output**

- **A single PNG image file** with four comparative plots (one for each parameter) saved in the specified output folder.
- Command-line summary of data loaded and processed.
<img width="4770" height="3543" alt="image" src="https://github.com/user-attachments/assets/356c5c32-6c55-4f03-acb9-81d2ab3e9699" />

## **How to Use**

Run the script from the command line:
```bash
python allgraphs.py
```

You'll be prompted to enter:
1. File path to the first panel's Excel file.
2. File path to the second panel's Excel file.
3. Names for both panels (for labeling).
4. Output folder path (or press Enter to use the default).

After processing, the script saves and displays the comparison plot, and prints a completion message.

---

**Typical Use Case:**  
Compare the performance of two solar panels over time based on voltage and current measurements collected in the field.

---
