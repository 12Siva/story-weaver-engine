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
    """
    Triggered by a PDF upload to S3. Extracts text from the PDF and saves it
    as a .txt file to a destination S3 bucket.
    """
    # 1. Get the bucket and key (filename) from the S3 event notification
    source_bucket = event['Records'][0]['s3']['bucket']['name']
    source_key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    logger.info(f"New PDF detected: {source_key} from bucket {source_bucket}")
    
    try:
        # 2. Get the PDF file content from S3
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        pdf_file_content = response['Body'].read()
        
        # 3. Use pypdf to extract text from the in-memory file
        pdf_file_in_memory = io.BytesIO(pdf_file_content)
        reader = pypdf.PdfReader(pdf_file_in_memory)
        
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
            
        if not text.strip():
            logger.warning(f"Could not extract any text from {source_key}.")
            return
            
        # 4. Save the extracted text to the destination bucket
        destination_key = os.path.splitext(source_key)[0] + '.txt'
        
        s3.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=destination_key,
            Body=text.encode('utf-8')
        )
        
        logger.info(f"Successfully extracted text and saved to s3://{DESTINATION_BUCKET}/{destination_key}")
        
    except Exception as e:
        logger.error(f"Error processing {source_key}: {str(e)}")
        raise e
