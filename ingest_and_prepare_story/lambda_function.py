import boto3
import pypdf
import io
import os
import urllib.parse
import logging

# Initialize clients outside the handler for reuse
s3 = boto3.client('s3')

# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variables
DESTINATION_BUCKET = os.environ['DESTINATION_BUCKET']

def lambda_handler(event, context):
    source_bucket = event['Records'][0]['s3']['bucket']['name']
    source_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    logger.info(f"New PDF detected: {source_key} from bucket {source_bucket}")
    
    try:
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        pdf_file_content = response['Body'].read()
        
        pdf_file_in_memory = io.BytesIO(pdf_file_content)
        reader = pypdf.PdfReader(pdf_file_in_memory)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            
        if not text.strip():
            logger.warning(f"Could not extract any text from {source_key}.")
            return
            
        destination_key = os.path.splitext(source_key)[0] + '.txt'
        
        s3.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=destination_key,
            Body=text.encode('utf-8')
        )
        
        logger.info(f"Successfully extracted text and saved to s3://{DESTINATION_BUCKET}/{destination_key}")

    except Exception as e:
        logger.error(f"An unexpected error occurred while processing {source_key}: {str(e)}")
        raise e