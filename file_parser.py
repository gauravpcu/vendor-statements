import pandas as pd

def get_headers_from_csv(file_path):
    """
    Reads a CSV file and returns its headers.
    """
    try:
        df = pd.read_csv(file_path, nrows=0) # Read only headers by getting 0 rows
        return df.columns.tolist()
    except pd.errors.EmptyDataError:
        return {"error": "The CSV file is empty."}
    except Exception as e:
        return {"error": f"Error parsing CSV: {str(e)}"}

def get_headers_from_excel(file_path):
    """
    Reads an Excel file (first sheet) and returns its headers.
    """
    try:
        # For Excel, pandas might need to read some data to find headers if they are not strictly on row 0.
        # Using nrows=0 might not always work as expected if the file has merged cells or specific formatting.
        # Reading the first row of data is generally safer for header detection.
        df = pd.read_excel(file_path, sheet_name=0, nrows=1) # Read first data row to get headers
        if df.empty and not pd.read_excel(file_path, sheet_name=0, header=None).empty:
             # If reading 1 row gives an empty df, but the sheet is not empty,
             # it might mean the first row is empty but headers are present.
             # Try to get headers without assuming data rows.
             df_header_only = pd.read_excel(file_path, sheet_name=0)
             return df_header_only.columns.tolist()
        return df.columns.tolist()
    except pd.errors.EmptyDataError: # Less common for Excel, but good to have
        return {"error": "The Excel sheet is empty or the first sheet has no data."}
    except Exception as e:
        # xlrd.biffh.XLRDError can happen for corrupted .xls files
        # zipfile.BadZipFile for corrupted .xlsx
        return {"error": f"Error parsing Excel: {str(e)}"}

def extract_headers(file_path, file_type):
    """
    Wrapper function to extract headers based on file type.
    """
    if file_type == "CSV":
        return get_headers_from_csv(file_path)
    elif file_type in ["XLSX", "XLS"]:
        return get_headers_from_excel(file_path)
    elif file_type == "PDF":
        return {"info": "Header extraction not supported for PDF files."}
    else:
        return {"error": f"Header extraction not supported for file type: {file_type}"}

if __name__ == '__main__':
    # Basic test cases (will only work if files exist at these paths)
    # Create dummy files for testing if needed
    # print(f"CSV Headers: {extract_headers('dummy.csv', 'CSV')}")
    # print(f"XLSX Headers: {extract_headers('dummy.xlsx', 'XLSX')}")
    # print(f"PDF Info: {extract_headers('dummy.pdf', 'PDF')}")
    pass
