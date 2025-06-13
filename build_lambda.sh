#!/bin/bash

# Create an optimized deployment package for AWS Lambda
echo "Creating optimized Lambda deployment package for vendor-statements..."

# Echo step information and exit on error
set -e

echo "====================================="
echo "STEP 1: Preparing environment"
echo "====================================="

# Clean up previous builds
echo "Cleaning up previous builds..."
rm -rf lambda_layer lambda_package vendor-statements-layer.zip vendor-statements-lambda.zip

# Record start time for tracking
START_TIME=$(date +%s)

# Part 1: Create Lambda Layer for large dependencies
echo "====================================="
echo "STEP 2: Creating Lambda Layer"
echo "====================================="
mkdir -p lambda_layer/python

# Install core Lambda layer dependencies
echo "Installing core dependencies in the Lambda layer..."
pip install openai python-dotenv requests pandas openpyxl xlrd pdfplumber -t ./lambda_layer/python --no-cache-dir

# Check if PDF processing is needed based on project code
if grep -q "import pytesseract\|import pdf2image" *.py; then
    echo "OCR processing imports detected in code. Installing OCR dependencies..."
    echo "NOTE: These are large dependencies that will increase layer size."
    
    # Ask if we should include OCR dependencies (with 10 second timeout for CI environments)
    read -t 10 -p "Include OCR libraries (pytesseract, pdf2image)? [Y/n]: " include_ocr || include_ocr="Y"
    include_ocr=${include_ocr:-Y}
    
    if [[ $include_ocr == "Y" || $include_ocr == "y" ]]; then
        echo "Installing OCR dependencies in the Lambda layer..."
        pip install pytesseract pdf2image -t ./lambda_layer/python --no-cache-dir
        echo "OCR dependencies installed successfully."
    else
        echo "Skipping OCR dependencies. Note that some functionality may be limited."
    fi
fi

# Separately handle docling which is particularly large
if grep -q "from docling" *.py; then
    echo "Docling import detected in code. This is a VERY large dependency."
    
    # Ask if we should include docling with timeout for CI environments
    read -t 10 -p "Include docling library? This will significantly increase package size [y/N]: " include_docling || include_docling="N"
    include_docling=${include_docling:-N}
    
    if [[ $include_docling == "Y" || $include_docling == "y" ]]; then
        echo "Installing docling in the Lambda layer..."
        pip install docling -t ./lambda_layer/python --no-cache-dir
        
        # Perform additional cleanup on docling to minimize size
        echo "Cleaning up unnecessary docling components..."
        rm -rf lambda_layer/python/docling/models 2>/dev/null || true
        rm -rf lambda_layer/python/docling_ibm_models/tableformer/checkpoints 2>/dev/null || true
        rm -rf lambda_layer/python/docling_ibm_models/code_formula_model/weights 2>/dev/null || true
        echo "Docling installed with optimizations."
    else
        echo "Skipping docling. PDF table processing functionality will be limited."
        
        # Create a minimal docling stub for imports to work but fail gracefully
        mkdir -p lambda_layer/python/docling
        cat > lambda_layer/python/docling/__init__.py << 'EOF'
# Stub for docling package - not fully installed due to size constraints
class DocumentConverter:
    def __init__(self, *args, **kwargs):
        raise ImportError("The docling package was not included in this Lambda deployment due to size constraints")
EOF
    fi
fi

# Clean up unnecessary files in the lambda layer
echo "Cleaning up unnecessary files in lambda layer..."
find lambda_layer -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type d -name "benchmarks" -exec rm -rf {} + 2>/dev/null || true
find lambda_layer -type f -name "*.pyc" -delete
find lambda_layer -type f -name "*.pyo" -delete
find lambda_layer -type f -name "*.md" -delete
find lambda_layer -type f -name "*.txt" -not -name "requirements.txt" -delete
find lambda_layer -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Remove heavy machine learning dependencies if not absolutely needed
echo "Removing heavy machine learning dependencies..."
rm -rf lambda_layer/python/torch* 2>/dev/null || true
rm -rf lambda_layer/python/transformers 2>/dev/null || true
rm -rf lambda_layer/python/scipy 2>/dev/null || true
rm -rf lambda_layer/python/cv2 2>/dev/null || true
rm -rf lambda_layer/python/skimage 2>/dev/null || true
rm -rf lambda_layer/python/rich 2>/dev/null || true
rm -rf lambda_layer/python/sympy 2>/dev/null || true
rm -rf lambda_layer/python/shapely 2>/dev/null || true

# Create Lambda Layer ZIP
echo "Creating Lambda Layer ZIP..."
cd lambda_layer
zip -r9 ../vendor-statements-layer.zip . -x "*.git*" "*.pyc" "*.pyo" "__pycache__/*" "tests/*" "test/*"
cd ..

# Calculate and display layer size
LAYER_SIZE=$(du -h vendor-statements-layer.zip | cut -f1)
LAYER_SIZE_BYTES=$(du -b vendor-statements-layer.zip | cut -f1)
echo "Lambda Layer size: $LAYER_SIZE ($LAYER_SIZE_BYTES bytes)"

# Part 2: Create minimal Lambda function package
echo "====================================="
echo "STEP 3: Creating Lambda function package"
echo "====================================="
mkdir -p lambda_package

# Install only Flask and serverless-wsgi (minimal dependencies)
echo "Installing minimal Flask dependencies..."
pip install Flask serverless-wsgi -t ./lambda_package --no-cache-dir

# Handle the python-magic dependency specially for Lambda
echo "Installing python-magic with Lambda compatibility..."
pip install python-magic -t ./lambda_package --no-cache-dir
# Try to install python-magic-bin-linux (specific for AWS Lambda's Linux environment)
pip install python-magic-bin-linux -t ./lambda_package --no-cache-dir || echo "Could not install python-magic-bin-linux, will use fallback method"

# Create directory structure for libmagic files
echo "Setting up libmagic fallback strategy..."
mkdir -p ./lambda_package/libmagic_fallback

# Clean up unnecessary files to reduce size
echo "Cleaning up unnecessary files..."
find lambda_package -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find lambda_package -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find lambda_package -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find lambda_package -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true
find lambda_package -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true
find lambda_package -type d -name "benchmarks" -exec rm -rf {} + 2>/dev/null || true
find lambda_package -type f -name "*.pyc" -delete
find lambda_package -type f -name "*.pyo" -delete
find lambda_package -type f -name "*.md" -delete
find lambda_package -type f -name "*.txt" -not -name "requirements.txt" -delete
find lambda_package -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Remove unnecessary files from popular packages
echo "Removing unnecessary components of packages..."
# DO NOT remove flask/json/tag.py as it's needed for proper Flask operation
rm -rf lambda_package/werkzeug/debug 2>/dev/null || true
rm -rf lambda_package/jinja2/tests 2>/dev/null || true
rm -rf lambda_package/jinja2/debug.py 2>/dev/null || true

# Remove temp_check directory if it exists
rm -rf ./temp_check

# Copy all essential project files
echo "Copying essential project files..."
ESSENTIAL_FILES=(
    lambda_function.py
    app.py
    azure_openai_client.py
    chatbot_service.py
    data_validator.py
    file_parser.py
    header_mapper.py
    pdftocsv.py
    field_definitions.json
    magic_fallback.py
)

for file in "${ESSENTIAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Copying $file to Lambda package..."
        cp "$file" ./lambda_package/
    else
        echo "Warning: $file not found, skipping"
    fi
done

# Create essential directories
echo "Creating essential directories..."
for dir in routes learned_preferences_storage templates_storage uploads; do
    mkdir -p "lambda_package/$dir"
    
    # Copy Python files in these directories if they exist
    if [ -d "$dir" ]; then
        # Copy __init__.py if it exists
        if [ -f "$dir/__init__.py" ]; then
            cp "$dir/__init__.py" "lambda_package/$dir/"
        else
            # Create empty __init__.py if needed
            touch "lambda_package/$dir/__init__.py"
        fi
        
        # Copy any .py files in the directory
        for py_file in "$dir"/*.py; do
            if [ -f "$py_file" ]; then
                cp "$py_file" "lambda_package/$dir/"
            fi
        done
    fi
done

# Create the ZIP file with maximum compression
echo "Creating ZIP file with maximum compression..."
cd lambda_package
# Be very precise about what we include to avoid including anything unnecessary
find . -type f -not -path "*/\.*" | zip -9 ../vendor-statements-lambda.zip -@
cd ..

# Calculate and display package size
FUNCTION_SIZE=$(du -h vendor-statements-lambda.zip | cut -f1)
FUNCTION_SIZE_BYTES=$(du -b vendor-statements-lambda.zip | cut -f1)
echo "Function package size: $FUNCTION_SIZE ($FUNCTION_SIZE_BYTES bytes)"

# Calculate total size
TOTAL_SIZE_BYTES=$((LAYER_SIZE_BYTES + FUNCTION_SIZE_BYTES))
TOTAL_SIZE_MB=$(awk "BEGIN {printf \"%.2f\", $TOTAL_SIZE_BYTES/1024/1024}")

# Display size warning if needed
if [ $TOTAL_SIZE_BYTES -gt 73400320 ]; then # ~70MB in bytes
    echo "WARNING: Total size exceeds AWS Lambda's direct upload limit of 70MB!"
    echo "You will need to use S3 upload method described in LAMBDA_DEPLOYMENT.md"
else
    echo "Total size is within AWS Lambda's direct upload limit of 70MB."
fi

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
echo "Build completed in $ELAPSED seconds"

# Clean up any leftover unnecessary directories
rm -rf __pycache__
rm -rf temp_packages

# Clean up the temporary directories
rm -rf lambda_package lambda_layer

echo "====================================="
echo "DEPLOYMENT ASSETS CREATED:"
echo "====================================="
echo "Lambda layer:    vendor-statements-layer.zip ($LAYER_SIZE)"
echo "Lambda function: vendor-statements-lambda.zip ($FUNCTION_SIZE)"
echo "Total size:      $TOTAL_SIZE_MB MB"
echo ""
echo "DEPLOYMENT INSTRUCTIONS:"
echo "1. First upload vendor-statements-layer.zip as a Lambda Layer"
echo "2. Then update your Lambda function with vendor-statements-lambda.zip"
echo "3. Make sure to configure your Lambda to use the layer you created"
echo ""
echo "For detailed instructions, see LAMBDA_DEPLOYMENT.md"
echo "====================================="
