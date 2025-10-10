# Use the official AWS base image for Python 3.12
FROM public.ecr.aws/lambda/python:3.12

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Copy your function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set the command to run your handler
CMD [ "lambda_function.lambda_handler" ]