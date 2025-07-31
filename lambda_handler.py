from fastapi_app import app
from mangum import Mangum

# Create the handler for AWS Lambda
handler = Mangum(app, lifespan="off")
