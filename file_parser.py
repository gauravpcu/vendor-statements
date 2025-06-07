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

def extract_data(file_path, file_type, finalized_mappings):
    """
    Reads data from a file, filters, and renames columns based on finalized mappings.
    Returns a list of dictionaries, where each dictionary is a row.
    """
    try:
        if file_type == "CSV":
            df = pd.read_csv(file_path)
        elif file_type in ["XLSX", "XLS"]:
            # For Excel, read_excel is used. Default engine handles xlsx.
            # For .xls, xlrd might be needed if openpyxl doesn't cover it.
            # pandas usually selects the right engine based on extension.
            df = pd.read_excel(file_path, sheet_name=0)
        elif file_type == "PDF":
             return {"error": "Data extraction from PDF files is not supported by this function."}
        else:
            return {"error": f"Unsupported file type for data extraction: {file_type}"}

        if df.empty:
            return [] # Return empty list if the file is empty or contains no data

        columns_to_rename = {}
        # original_headers_in_file actually present in the DataFrame
        original_headers_in_file = set(df.columns.tolist())

        mapped_original_headers = []

        for mapping in finalized_mappings:
            original_header = mapping.get('original_header')
            mapped_field = mapping.get('mapped_field')

            if original_header in original_headers_in_file and mapped_field and mapped_field != "N/A":
                columns_to_rename[original_header] = mapped_field
                mapped_original_headers.append(original_header)
            elif original_header not in original_headers_in_file and mapped_field and mapped_field != "N/A":
                # Log or handle cases where a mapped header isn't actually in the file
                # This might indicate an issue if mappings were generated from a different version
                # or if there's a case sensitivity mismatch not handled by pandas by default.
                print(f"Warning: Mapped original header '{original_header}' not found in the actual file columns.")


        if not mapped_original_headers:
             return {"error": "No valid mappings resulted in columns to process. Either no headers were mapped or mapped headers were not found in the file."}

        # Filter DataFrame to keep only the columns that were successfully mapped
        # and are present in the original file.
        df_filtered = df[mapped_original_headers]

        # Rename columns to their standard field names
        df_renamed = df_filtered.rename(columns=columns_to_rename)

        # Convert to list of dictionaries
        data = df_renamed.to_dict(orient='records')
        return data

    except FileNotFoundError:
        return {"error": f"File not found: {file_path}"}
    except pd.errors.EmptyDataError:
        return {"error": "The file is empty or contains no data to parse."}
    except Exception as e:
        # More specific pandas errors could be caught here if needed
        return {"error": f"Error processing file {file_path} for data extraction: {str(e)}"}
