"""
Smoke Test Script

Purpose:
    Verify that the application API and MinIO object storage are working
    correctly, including API authentication and file storage operations.

    This test verifies:
    1. API health endpoint availability.
    2. MinIO health endpoint availability.
    3. API authentication (unauthenticated vs authenticated requests).
    4. MinIO bucket availability and creation if necessary.
    5. MinIO file upload, download, content verification, and deletion.

    Note:
    This test does NOT call an LLM or perform any AI inference.
"""

"""
Understanding what this smoke test actually verifies
Your script performs several important integration checks:


Test	Operation	Expected result
Application health	GET /health	HTTP 200
MinIO health	GET /minio/health/ready	HTTP 200

API security	Request without token	HTTP 401
API authentication	Request with valid token	HTTP 404

Bucket availability	head_bucket()	Bucket exists
Bucket creation	create_bucket()	Bucket created if missing

Upload	put_object()	Successful write
Download	get_object()	Original content retrieved

Verification	Compare bytes	Contents match
Cleanup	delete_object()	Temporary object deleted


"""


"""
Integration testing: Testing communication between multiple services.


API authentication testing: Verifying that protected endpoints reject unauthorized requests.


Object storage testing: Testing MinIO through its S3-compatible API.


Environment-based configuration: Using environment variables instead of hardcoding credentials.


Resource cleanup: Removing temporary test objects even when a test fails.


CI/CD validation: Running automated checks before considering a deployment successful.

"""


# ============================================================
# 1. Import required libraries
# ============================================================

import os
import time
import urllib.error
import urllib.request
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


# ============================================================
# 2. HTTP utility function
# ============================================================

def http_status(url: str, token: str | None = None) -> int:
    """
    Send an HTTP GET request and return its HTTP status code.

    Args:
        url: Target API or service URL.
        token: Optional API access token used for authentication.

    Returns:
        HTTP status code, such as:
            200 = OK
            401 = Unauthorized
            404 = Not Found

    If a token is provided, it is included in the HTTP
    Authorization header using the Bearer authentication scheme.
    """

    # Prepare HTTP headers.
    # If a token exists, send it as a Bearer token.
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        # Create and send an HTTP GET request.
        # Timeout prevents the script from waiting indefinitely.
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=3
        ) as response:

            # Return the HTTP response status code.
            return response.status

    except urllib.error.HTTPError as exc:
        # HTTP errors such as 401 and 404 are valid HTTP responses.
        # Return their status codes instead of terminating the test.
        return exc.code


# ============================================================
# 3. Service health-check utility
# ============================================================

def wait_for_health(url: str, timeout: float = 90) -> None:
    """
    Wait until a service becomes healthy.

    Args:
        url: Health-check endpoint.
        timeout: Maximum number of seconds to wait.

    The function repeatedly sends HTTP requests every 2 seconds.
    It returns when the service responds with HTTP 200.

    If the service does not become healthy before the deadline,
    a RuntimeError is raised.
    """

    # Calculate the maximum waiting deadline.
    # monotonic() is preferred for measuring elapsed time.
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            # Check whether the service responds successfully.
            if http_status(url) == 200:
                return

        except (OSError, urllib.error.URLError):
            # Service may not have started yet.
            # Ignore temporary connection errors and retry.
            pass

        # Wait 2 seconds before trying again.
        time.sleep(2)

    # Raise an exception if the service never becomes healthy.
    raise RuntimeError(
        "Service did not become healthy before the smoke-test deadline"
    )


# ============================================================
# 4. Main smoke-test function
# ============================================================

def main() -> None:

    # --------------------------------------------------------
    # 4.1 Configure API and MinIO endpoints
    # --------------------------------------------------------

    # Application API endpoint.
    # localhost refers to the application container itself
    # because this script runs inside the app container.
    api_url = "http://localhost:8000"

    # Read MinIO security configuration from environment variables.
    # Default is HTTP (secure=False).
    secure = os.getenv("MINIO_SECURE", "false").lower() in {
        "1", "true", "yes", "on"
    }

    # Build the MinIO endpoint URL.
    # MINIO_ENDPOINT is supplied through environment variables.
    endpoint = f"{'https' if secure else 'http'}://{os.environ['MINIO_ENDPOINT']}"

    # --------------------------------------------------------
    # 4.2 Verify application API and MinIO health
    # --------------------------------------------------------

    # Wait until the application API health endpoint returns HTTP 200.
    wait_for_health(f"{api_url}/health")

    # Wait until MinIO reports that its storage service is ready.
    # MinIO readiness endpoint:
    # /minio/health/ready
    wait_for_health(f"{endpoint}/minio/health/ready")

    # --------------------------------------------------------
    # 4.3 Test API authentication
    # --------------------------------------------------------

    # Generate a unique proposal ID for this test.
    # uuid4() prevents conflicts with existing proposal records.
    proposal_url = f"{api_url}/business-proposals/smoke-{uuid4().hex}"

    # First test: Send a request WITHOUT an authentication token.
    # Expected result: HTTP 401 Unauthorized.
    if http_status(proposal_url) != 401:
        raise RuntimeError(
            "Proposal API did not reject an unauthenticated request"
        )

    # Second test: Send the same request WITH a valid API token.
    # Expected result: HTTP 404 Not Found.
    #
    # Why 404?
    # The request is authenticated successfully, but the randomly
    # generated proposal ID does not exist.
    #
    # This verifies both authentication and the expected API behavior.
    if http_status(proposal_url, os.environ["API_ACCESS_TOKEN"]) != 404:
        raise RuntimeError(
            "Authenticated proposal lookup did not return the expected 404"
        )

    # --------------------------------------------------------
    # 4.4 Configure MinIO / S3 client
    # --------------------------------------------------------

    # Get the MinIO region from environment variables.
    # Default region is us-east-1.
    region = os.getenv("MINIO_REGION", "us-east-1")

    # Get the target MinIO bucket name.
    # Use the default bucket name if not explicitly configured.
    bucket = os.getenv("MINIO_BUCKET_NAME", "business-plan-bucket")

    # Create a boto3 S3 client.
    #
    # boto3 is the AWS SDK for Python.
    # MinIO provides an S3-compatible API, allowing boto3
    # to communicate with MinIO.
    client = boto3.client(
        "s3",

        # MinIO server endpoint rather than AWS S3.
        endpoint_url=endpoint,

        # MinIO root credentials.
        aws_access_key_id=os.environ["MINIO_ROOT_USER"],
        aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],

        # S3 region configuration.
        region_name=region,

        # Configure network timeouts and S3 request behavior.
        config=Config(

            # Maximum time to establish a connection.
            connect_timeout=3,

            # Maximum time to wait for a response.
            read_timeout=5,

            # Do not repeatedly retry failed requests.
            retries={"total_max_attempts": 1},

            # Use path-style addressing:
            # endpoint/bucket/object
            #
            # This is commonly used with self-hosted
            # S3-compatible storage services such as MinIO.
            s3={"addressing_style": "path"},
        ),
    )

    # --------------------------------------------------------
    # 4.5 Check whether the MinIO bucket exists
    # --------------------------------------------------------

    try:
        # Check whether the target bucket already exists.
        # head_bucket() retrieves bucket metadata without
        # downloading its contents.
        client.head_bucket(Bucket=bucket)

    except ClientError as exc:

        # If the bucket does not exist, create it.
        # Other errors (e.g., authentication or permission errors)
        # should be raised instead of being ignored.
        if exc.response["Error"]["Code"] not in {
            "404", "NoSuchBucket", "NotFound"
        }:
            raise

        # S3 requires a LocationConstraint for regions
        # other than us-east-1 when creating a bucket.
        options = {} if region == "us-east-1" else {
            "CreateBucketConfiguration": {
                "LocationConstraint": region
            }
        }

        # Create the bucket if it does not exist.
        client.create_bucket(Bucket=bucket, **options)

    # --------------------------------------------------------
    # 4.6 Test MinIO file upload (WRITE)
    # --------------------------------------------------------

    # Generate a unique object key for this test file.
    # The ci-smoke/ prefix organizes smoke-test objects.
    key = f"ci-smoke/{uuid4().hex}.txt"

    # Define sample file content.
    payload = b"business-plan storage smoke test"

    # Upload the object to MinIO.
    #
    # put_object() writes an object into the specified bucket.
    # ContentType identifies the uploaded file as plain text.
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload,
        ContentType="text/plain"
    )

    # --------------------------------------------------------
    # 4.7 Test MinIO file download (READ)
    # --------------------------------------------------------

    try:
        # Download the uploaded object from MinIO.
        # get_object() returns a response containing the object body.
        body = client.get_object(Bucket=bucket, Key=key)["Body"]

        try:
            # Read the downloaded bytes and compare them
            # with the original uploaded content.
            #
            # If they differ, the storage round-trip has failed.
            if body.read() != payload:
                raise RuntimeError(
                    "MinIO round-trip contents differ"
                )

        finally:
            # Always close the response body to release resources.
            body.close()

    # --------------------------------------------------------
    # 4.8 Test MinIO file deletion (DELETE)
    # --------------------------------------------------------

    finally:
        # Delete the temporary test object.
        #
        # This cleanup runs even if the download or content
        # verification fails.
        client.delete_object(Bucket=bucket, Key=key)

    # --------------------------------------------------------
    # 4.9 Report successful smoke test
    # --------------------------------------------------------

    print(
        "Smoke test passed: API health, authentication, "
        "and MinIO write/read/delete"
    )


# ============================================================
# 5. Python entry point
# ============================================================

# Execute main() only when this file is run directly.
#
# This prevents main() from automatically executing if
# smoke_test.py is imported as a module by another Python file.
if __name__ == "__main__":
    main()
