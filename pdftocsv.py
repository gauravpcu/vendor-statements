import logging
import time
from pathlib import Path
import pandas as pd
import io
import sys

from docling.document_converter import DocumentConverter
_log = logging.getLogger(__name__)


def extract_tables_from_file(input_doc_path_str: str, output_csv_path_str: str | None = None): # Added output_csv_path_str
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path(input_doc_path_str)

    if not input_doc_path.is_file():
        _log.error(f"Input file not found: {input_doc_path}")
        return

    # Determine output path
    if output_csv_path_str:
        print(f"Output path provided: {output_csv_path_str}")
        output_csv_path = Path(output_csv_path_str)
        output_dir = output_csv_path.parent
        doc_filename_for_output = output_csv_path.stem # Use this if specific name is given
    else:
        print(f"No output path provided. Using default output path in 'scratch' directory for {input_doc_path.name}.")
        # If no output path is provided, use the 'scratch' directory
        # Default behavior: use 'scratch' directory and input filename
        output_dir = Path("scratch")
        doc_filename_for_output = input_doc_path.stem
        output_csv_path = output_dir / f"{doc_filename_for_output}-all_tables.csv"

    output_dir.mkdir(parents=True, exist_ok=True)

    doc_converter = DocumentConverter()

    start_time = time.time()

    conv_res = doc_converter.convert(input_doc_path)

    all_csv_parts = []

    # Function to sanitize DataFrame cells
    def sanitize_df_for_csv(df):
        # Trim whitespace from string cells
        df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

        # Prevent CSV injection
        def prevent_csv_injection(val):
            if isinstance(val, str) and val.startswith(('.', '=', '+', '-', '@')):  # Added '.' to the list
                return "'" + val  # Prepend a single quote
            return val

        df = df.applymap(prevent_csv_injection)
        return df

    # Export tables
    for table_ix, table in enumerate(conv_res.document.tables):
        table_df: pd.DataFrame = table.export_to_dataframe()
        #print(f"## Table {table_ix}")
        #print(table_df.to_markdown())

        # Convert table to CSV string via buffer
        csv_buffer = io.StringIO()
        current_table_df_for_csv = table_df.reset_index(drop=True)
        # Include header only for the first table
        current_table_df_for_csv.to_csv(csv_buffer, index=False, header=(table_ix == 0))
        all_csv_parts.append(csv_buffer.getvalue())
        csv_buffer.close()
        _log.info(f"Added table {table_ix + 1} to CSV parts.")

    # Save combined CSV file
    if all_csv_parts:
        combined_csv_content = "".join(all_csv_parts)
        # Use the determined output_csv_path
        _log.info(f"Saving all CSV tables to {output_csv_path}")
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(combined_csv_content)
    else:
        _log.info("No tables found to create a combined CSV file.")

    end_time = time.time() - start_time

    _log.info(f"Document converted and tables exported in {end_time:.2f} seconds.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path_arg = sys.argv[1]
        output_path_arg = None
        if len(sys.argv) > 2:
            output_path_arg = sys.argv[2]
        extract_tables_from_file(file_path_arg, output_path_arg)
    else:
        _log.warning("No input file provided. Running with default input and output.")
        default_input = "/Users/gaurav/Desktop/Code/docling/NHCA.xlsx"
        default_output = f"scratch/{Path(default_input).stem}-all_tables.csv"
        extract_tables_from_file(default_input, default_output)