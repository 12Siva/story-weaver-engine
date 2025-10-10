# Story Weaver Engine

Story Weaver Engine is a serverless application built on AWS that uses a two-step AI reasoning process to analyze and creatively rewrite stories. Originally a proof-of-concept in a Google Colab notebook, the project has been re-architected into a scalable, event-driven system capable of handling complex dependencies and user-driven creative prompts.

## Features

-   **Serverless Architecture:** Deployed on AWS using Lambda, API Gateway, and S3 for a cost-effective, scalable, and fully managed backend.
-   **Two-Step AI Reasoning:**
    1.  **Analysis:** The engine first analyzes an input story to generate a structured flowchart (JSON), deconstructing the narrative into its core plot points.
    2.  **Synthesis:** It then uses this structural understanding, along with a user's "what if" prompt, to creatively rewrite the story.
-   **Container-Based Deployment:** Uses Docker and Amazon ECR to package and deploy Lambda functions, ensuring that complex dependencies (like `pypdf` and `cryptography`) are handled correctly and consistently.
-   **API-Driven Workflow:** The entire process is initiated through a secure API, allowing for easy integration with web or mobile frontends.

## Architecture

The Story Weaver Engine is built on an event-driven architecture using the following AWS services:

-   **Amazon S3:** Used for storing uploaded PDFs, intermediary text files, and the final rewritten stories. Bucket versioning can be enabled for data protection.
-   **AWS Lambda:** Two container-based functions handle the core logic:
    1.  `ingest-story-processor`: Ingests and processes the initial PDF upload, extracts the text, and saves it to an S3 bucket.
    2.  `story-weaver-processor`: Triggered by an API call, this function performs the two-step AI analysis and rewrite, saving the final story.
-   **Amazon API Gateway:** Provides HTTP endpoints to initiate the workflow, such as generating a secure upload URL and submitting a rewrite prompt.
-   **Amazon ECR (Elastic Container Registry):** Stores the Docker container images for the Lambda functions.
-   **AWS IAM:** Manages the permissions and roles that allow the services to interact securely.
-   **AWS SSM Parameter Store:** Securely stores sensitive information like the Google Gemini API key.

## Recent Changes

-   **(2025-10-09)** Migrated the entire project from a Google Colab notebook to a fully serverless, event-driven architecture on AWS. Implemented a container-based deployment pipeline and a two-step AI reasoning process for story analysis and rewriting.

## Deployment

The application is deployed as a set of serverless components on AWS. The core Lambda functions are packaged as Docker container images.

1.  **Prerequisites:**
    * An AWS account
    * Docker Desktop installed and running
    * AWS CLI installed and configured (`aws configure`)

2.  **Build and Push the Container Images:**
    * For each function (`ingest-story-processor` and `story-weaver-processor`), navigate to its directory.
    * Build, tag, and push the Docker image to its respective Amazon ECR repository.

    ```bash
    # Example for the ingestor function
    docker build -t story-weaver-ingestor .
    docker tag story-weaver-ingestor:latest YOUR_AWS_[ID.dkr.ecr.us-east-2.amazonaws.com/story-weaver-ingestor:latest](https://ID.dkr.ecr.us-east-2.amazonaws.com/story-weaver-ingestor:latest)
    docker push YOUR_AWS_[ID.dkr.ecr.us-east-2.amazonaws.com/story-weaver-ingestor:latest](https://ID.dkr.ecr.us-east-2.amazonaws.com/story-weaver-ingestor:latest)
    ```

3.  **Deploy Lambda Functions:**
    * Create the Lambda functions in the AWS Console, selecting "Container image" as the source and pointing to the images in ECR.
    * Configure the necessary triggers (S3, API Gateway), environment variables, memory, and timeouts for each function.

## Usage

The application is used via its API endpoints.

1.  **Get a Secure Upload URL:** A frontend application first calls the `/generate-upload-url` endpoint to get a pre-signed URL to upload a PDF directly to S3.
2.  **Process and Rewrite the Story:** After the PDF is uploaded and processed into a text file, the frontend calls the `story-weaver-processor` endpoint with a JSON body containing the `sourceKey` of the text file and a `userPrompt`.

    **Example API Call:**
    `POST /rewrite-story`
    ```json
    {
      "sourceKey": "my-story.txt",
      "userPrompt": "What if the rabbit decided to befriend the grumpy fox instead of laughing at him?"
    }
    ```

## Contributing

-   Open issues for bugs or feature requests.
-   Pull requests are welcome—please follow the repo's coding style.
