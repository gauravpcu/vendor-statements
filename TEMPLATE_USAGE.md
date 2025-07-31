# Using Templates with Vendor Statements App

Templates help you process files with headers that aren't in the first row and provide consistent field mappings for recurring vendor formats.

## When to Use Templates

Templates are useful when:
- Headers aren't in the first row (common with vendor statements)
- You process files from the same vendor regularly
- You want consistent field mappings across similar files
- You see errors like: `No headers found in file`

## How to Apply Templates

### Method 1: Automatic Application (Recommended)
1. **Upload Your File**
   - Name your file starting with the vendor name (e.g., `Basic_Statement_2024.xlsx`)
   - The app will automatically look for a matching template
   - If found, the template will be applied automatically during upload

### Method 2: Manual Application
1. **Upload Your File**
   - Upload your file normally
   - If headers aren't detected, you'll see an error or no headers

2. **Apply Template from Upload Page**
   - In the file processing area, find the "Template" dropdown
   - Select an appropriate template from the list
   - The file will be reprocessed with the template settings
   - Headers and field mappings will be updated automatically

### Method 3: Template Management Page
1. **Go to Manage Templates**
   - Click "Manage Saved Templates" from the main page
   - View all available templates
   - Create new templates or delete existing ones

## Creating Templates

### Option 1: Save from Upload Page (Recommended)
1. **Upload and Process a File**
   - Upload a file and manually adjust the skip rows if needed
   - Map the fields correctly using the dropdown menus
   - Click "Save as Template" button
   - Enter a template name and save

### Option 2: Create from Template Management Page
1. **Go to Manage Templates**
   - Click "Create New Template"
   - Enter template name and skip rows value
   - Add field mappings manually
   - Save the template

## Available Templates

Current templates in your system:
- **Basic**: Skips 10 rows, for Basic vendor statements
- **NHCA**: Uses first row headers, for NHCA format files
- **Alpha-Med**: Uses first row headers, for Alpha-Med format files

## Template Structure

Templates contain:
- **Template Name**: Display name for the template
- **Skip Rows**: Number of rows to skip before looking for headers
- **Field Mappings**: Mapping from original headers to standard fields
- **Creation Date**: When the template was created

Example template structure:
```json
{
    "template_name": "Basic",
    "filename": "Basic.json",
    "creation_timestamp": "2025-06-08T23:58:37.878534Z",
    "field_mappings": [
        {
            "original_header": "Purchase Order Number",
            "mapped_field": "PONumber"
        },
        {
            "original_header": "Inv Ref",
            "mapped_field": "InvoiceID"
        }
    ],
    "skip_rows": 10
}
```

## Troubleshooting

### "No headers found in file"
- Try increasing the skip rows value
- Check if your file has headers in a different location
- Create a custom template with the correct skip rows value

### Template not applying automatically
- Ensure your filename starts with the template name
- Check that the template exists in the system
- Verify the template filename matches the vendor name pattern

### Field mappings not working
- Verify the original headers in your template match exactly
- Check that the mapped fields are valid system fields
- Update the template if the vendor changed their format

## Best Practices

1. **Naming Convention**: Name templates after the vendor (e.g., "Acme", "BasicCorp")
2. **File Naming**: Start filenames with vendor name for auto-application
3. **Regular Updates**: Update templates when vendor formats change
4. **Test Templates**: Always verify template results before processing large batches
5. **Documentation**: Keep notes about what each template is for
