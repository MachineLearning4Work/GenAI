# How Jenkins, Webhooks, FastAPI, and MinIO Work Together

## 1. Overview

These four technologies have different responsibilities in an automated
AI/ML deployment and artifact-management system:

-   **Jenkins:** Automation and orchestration. It executes CI/CD
    pipelines.
-   **Webhook:** A notification mechanism. It tells another system that
    an event has happened.
-   **FastAPI:** The backend/API layer. It receives HTTP requests,
    validates them, and coordinates operations.
-   **MinIO:** Object storage. It stores files, models, datasets, logs,
    reports, and other artifacts.

They complement one another rather than compete.

## 2. Overall architecture

Imagine an AI solution such as `board_assistant`. A developer pushes a new
version to GitHub or Azure DevOps.

A common architecture is:

``` text
Developer
   |
   v
GitHub / Azure DevOps
   |
   | Webhook notification (HTTP POST)
   v
FastAPI webhook endpoint
   |
   | Validates event and triggers a pipeline
   v
Jenkins
   |
   | Checkout -> Build -> Test -> Package -> Deploy
   |
   +----------------------+
   |                      |
   v                      v
Docker Registry       MinIO
(container images)    (models, reports, datasets,
                       logs, evaluation artifacts)

FastAPI also provides controlled APIs to inspect or retrieve artifacts.
```

This is one possible architecture, not a mandatory arrangement. GitHub
can also send its webhook directly to Jenkins without FastAPI in the
middle.

## 3. What happens step by step?

### Step 1 --- A developer pushes code

A developer changes Python code, a Dockerfile, or configuration and
pushes it to a repository:

``` bash
git add .
git commit -m "Update Board Assistant agent"
git push origin develop
```

GitHub detects the push event.

### Step 2 --- A webhook sends a notification

GitHub sends an HTTP POST request to a configured endpoint. A simplified
payload might look like this:

``` json
{
  "repository": "board_assistant",
  "branch": "develop",
  "commit": "a81c920",
  "author": "developer",
  "event": "push"
}
```

The webhook is essentially a message saying: "Something has changed in
this repository. Please take action."

A webhook does not build the application. It notifies a receiving system
that an event occurred.

### Step 3 --- FastAPI receives the notification

FastAPI can expose an endpoint to receive the webhook:

``` python
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.post("/webhooks/github")
async def github_webhook(request: Request):
    payload = await request.json()

    repository = payload.get("repository", {}).get("name")
    branch = payload.get("ref")

    if branch != "refs/heads/develop":
        return {"status": "ignored"}

    print("Repository:", repository)

    # Validate the webhook and trigger Jenkins here.

    return {"status": "accepted"}
```

FastAPI acts as the entry point to the backend. It can:

-   Receive webhook notifications.
-   Validate the incoming request.
-   Identify the repository, branch, and commit.
-   Apply business rules.
-   Trigger Jenkins.
-   Record execution information.
-   Expose APIs to monitor pipeline results.

**Important:** The example above is illustrative. A production webhook
endpoint must verify the sender's signature or another secure
authentication mechanism before trusting the payload.

### Step 4 --- FastAPI triggers Jenkins

FastAPI does not need to execute Docker builds, tests, or Kubernetes
deployments itself. Instead, it can ask Jenkins to do that work.


Jenkins provides two common endpoints:

/build	
Trigger a job without supplying build parameters

/buildWithParameters	
Trigger a job with parameters


Jenkins needs to identify and authenticate the application making the request.

- jenkins_user: Jenkins username.



- API_TOKEN: API token generated from the Jenkins user account.






Jenkins provides a REST API that can trigger jobs. For example:

``` python
import requests

JENKINS_URL = "https://jenkins.example.com"
JOB_NAME = "board-assistant-pipeline"

response = requests.post(
    f"{JENKINS_URL}/job/{JOB_NAME}/buildWithParameters",
    auth=("jenkins_user", "API_TOKEN"),
    params={
        "BRANCH": "develop",
        "REPOSITORY": "board_assistant"
    }
)

response.raise_for_status()
```


NOTE :

``` python
response.raise_for_status()
``` 

IMPORTANT : 
This is an important line.

It checks whether the HTTP request was successful.
- If the response has an HTTP error (4xx or 5xx), Python raises an exception.

- If the response is successful, execution continues.

However, there is an important distinction:

A successful HTTP response does not mean the Jenkins pipeline completed successfully. It generally means Jenkins accepted the request and scheduled the build.



The example is simplified. Depending on Jenkins security configuration,
a request may also need a crumb (CSRF protection token), and the
credentials should be stored securely rather than hard-coded.

#### Step 4.1 --- CSRF protection: Jenkins crumb
CSRF protection: Jenkins crumb

Jenkins can enable CSRF (Cross-Site Request Forgery) protection to prevent unauthorized requests that attempt to perform actions on behalf of an authenticated user.

For POST requests, Jenkins may require a special token called a crumb.

The process is:

1. FastAPI authenticates with Jenkins.

2. FastAPI requests a crumb from Jenkins.

3. Jenkins returns the crumb and its associated HTTP header name.

4. FastAPI includes that header in the POST request that triggers the pipeline.



### Step 5 --- Jenkins executes the pipeline

Groovy is a programming language that runs on the Java Virtual Machine (JVM). It is similar to Java but has a simpler and more flexible syntax.

In Jenkins, Groovy is the language used to write and execute pipeline scripts.


``` groovy
stage('Checkout') {
    steps {
        git branch: 'develop',
            url: 'https://github.com/company/board_assistant.git'
    }
}
```

Why are there two lines?
Because branch and url are two named arguments passed to the same git step.

It is equivalent to writing everything on one line:
``` groovy
git branch: 'develop', url: 'https://github.com/company/board_assistant.git'
```

A Jenkinsfile defines the steps to execute. For example:

``` groovy
pipeline {
    agent any

     parameters {
        string(
            name: 'BRANCH',
            defaultValue: 'main'
        )

        string(
            name: 'REPOSITORY',
            defaultValue: 'board_assistant'
        )
    }
    
    
    stages {
        stage('Checkout') {
            steps {
                git branch: 'develop',
                    url: 'https://github.com/company/board_assistant.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'pytest tests/'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t board-assistant:1.0 .'
            }
        }

        stage('Upload Artifacts') {
            steps {
                sh 'python upload_artifacts.py'
            }
        }

        stage('Deploy') {
            steps {
                sh 'kubectl apply -f k8s/'
            }
        }
    }
}
```

Jenkins can automate:

-   Source-code checkout.
-   Dependency installation.
-   Unit and integration tests.
-   Static analysis and security scans.
-   AI/ML evaluation.
-   Docker image building and publishing.
-   Artifact uploads.
-   Kubernetes deployment.

The actual stages depend on the project's requirements and deployment
strategy.


In a Jenkins Declarative Pipeline, each statement inside the steps {} block represents an individual pipeline step (or operation).

For example:
``` groovy
steps {
    echo "Starting pipeline"
    echo "Checking out source code"
    sh "python --version"
    sh "pip install -r requirements.txt"
    echo "Installation completed"
}
```

## 4. Where MinIO fits

MinIO is object storage compatible with the Amazon S3 API. It provides a
centralized location for files generated by applications and pipelines.

Examples of artifacts include:

  Artifact          Example
  ----------------- -----------------------
  Model             `model.pkl`
  AI evaluation     `evaluation.json`
  Reports           `ceo_report.pdf`
  Logs              `training.log`
  Dataset           `dataset.csv`
  Docker metadata   `image_metadata.json`
  Package           `board_assistant.zip`

Instead of keeping all these files only in the Jenkins workspace, a
pipeline can upload them to MinIO.

A possible bucket/object layout:

``` text
minio/
|
+-- board-assistant/
|   +-- builds/
|   |   +-- build-101/
|   |   |   +-- model.pkl
|   |   |   +-- evaluation.json
|   |   |   +-- report.pdf
|   |   |
|   |   +-- build-102/
|   |       +-- model.pkl
|   |       +-- evaluation.json
|   |
|   +-- datasets/
|
+-- business-assist/
|   +-- builds/
|   +-- reports/
|
+-- ml-models/
    +-- classification/
    +-- anomaly-detection/
```

The exact layout is a design choice. In MinIO, buckets contain objects;
folders shown in a console are generally represented by object-key
prefixes.

### Why store artifacts in MinIO?

Artifacts are stored independently of the Jenkins workspace. A Jenkins
agent can be removed, a workspace can be cleaned, or Jenkins can be
restarted while the uploaded artifacts remain in object storage.

MinIO is suitable for large files and binary objects. It is not a
replacement for a relational database or for Jenkins build history.

## 5. How FastAPI communicates with MinIO

FastAPI can communicate with MinIO through its S3-compatible API. One
Python option is the MinIO SDK.

Install it:

``` bash
pip install minio
```

A simplified example:

``` python
from minio import Minio

client = Minio(
    "minio.example.com:9000",
    access_key="MINIO_ACCESS_KEY",
    secret_key="MINIO_SECRET_KEY",
    secure=False
)

bucket = "board-assistant"

if not client.bucket_exists(bucket):
    client.make_bucket(bucket)

client.fput_object(
    bucket,
    "build-101/evaluation.json",
    "evaluation.json"
)
```

For production, use TLS (`secure=True`), credentials from a secret
manager or environment, and a dedicated MinIO service account with the
minimum permissions required.

### FastAPI endpoint to provide a download link

FastAPI can expose an endpoint that creates a time-limited presigned
URL:

``` python
from fastapi import FastAPI
from minio import Minio

app = FastAPI()

client = Minio(
    "minio.example.com:9000",
    access_key="MINIO_ACCESS_KEY",
    secret_key="MINIO_SECRET_KEY",
    secure=True
)

@app.get("/artifacts/{object_name:path}")
async def get_artifact(object_name: str):
    url = client.presigned_get_object(
        "ceo-council",
        object_name
    )
    return {"download_url": url}
```

This lets an application retrieve an artifact without exposing MinIO
credentials to the end user. The endpoint should also authenticate and
authorize the requester and restrict which objects they may access.

The responsibilities are:

-   Jenkins generates artifacts.
-   MinIO stores artifacts.
-   FastAPI provides controlled access to artifacts.

## 6. MinIO can also send webhooks

A webhook is not used only between GitHub and Jenkins. MinIO can publish
event notifications when objects are created, removed, or otherwise
changed.

For example:

``` text
Jenkins
   |
   | Upload evaluation.json
   v
MinIO
   |
   | Object-created event notification
   v
FastAPI webhook endpoint
   |
   | Validate event and identify object
   v
Application / database / downstream workflow
```

A possible sequence:

1.  Jenkins uploads `evaluation.json`.
2.  MinIO detects the new object.
3.  MinIO sends an event notification to a configured HTTP endpoint.
4.  FastAPI receives the notification.
5.  FastAPI updates a database, refreshes a dashboard, or triggers
    another operation.

This is an example of an **event-driven architecture**.

MinIO event notifications must be configured for the relevant bucket and
event types. The receiving endpoint should be designed to handle retries
and duplicate notifications. It should also verify that the event is
genuine and safely handle object names and metadata.

## 7. Three integration patterns

There are several ways to connect the components.

  -----------------------------------------------------------------------
  Pattern                 Communication           Typical use
  ----------------------- ----------------------- -----------------------
  A                       GitHub → Jenkins        Simple CI/CD; Jenkins
                                                  receives repository
                                                  events directly

  B                       GitHub → FastAPI →      Centralized
                          Jenkins                 orchestration,
                                                  validation, and
                                                  business rules

  C                       Jenkins → MinIO →       Artifact storage and
                          FastAPI                 event-driven processing
  -----------------------------------------------------------------------

These patterns can be combined.

For an AI/ML platform, combining Patterns B and C can be useful:

-   FastAPI acts as a controlled orchestration/API layer.
-   Jenkins performs CI/CD work.
-   MinIO stores artifacts.
-   MinIO events can notify FastAPI when new artifacts arrive.

However, avoid adding FastAPI as an unnecessary middle layer if direct
GitHub-to-Jenkins integration already meets the requirements.

## 8. Suggested architecture for an AI/ML platform

For an environment with AI solutions, a Docker registry, Kubernetes,
MLflow, and MinIO, responsibilities could be separated as follows:

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  GitHub / Azure DevOps               Source control, branches, pull
                                      requests, code review

  Jenkins                             CI/CD pipelines, builds, tests,
                                      security scans, image publishing,
                                      deployment

  FastAPI                             Webhook receivers, artifact APIs,
                                      pipeline management, application
                                      endpoints

  MinIO                               Object storage for models,
                                      datasets, reports, and other
                                      artifacts

  PostgreSQL                          Relational application data and
                                      metadata

  MLflow                              Experiment tracking, parameters,
                                      metrics, model lifecycle, and
                                      related metadata

  Docker Registry                     Storage and distribution of
                                      container images

  Kubernetes                          Running and managing deployed
                                      containers
  -----------------------------------------------------------------------

Note:


Docker vs Kubernetes :  

Docker packages and runs applications in containers.

Kubernetes orchestrates those containers across a cluster of machines.

Imagine you have a FastAPI application serving ML predictions.

With Docker:
- You build a Docker image.
- You start one or more containers.

With Kubernetes:

- You deploy multiple replicas of your application.

- Kubernetes distributes Pods across available worker nodes.

- It monitors their health.

- It restarts failed containers.

- It can scale replicas according to demand.




Note: 

- IaaS – Infrastructure as a Service: Renting computing infrastructure from a cloud provider (AWS. Azure, ...)


- IaC – Infrastructure as Code: Defining, provisioning, and managing infrastructure using configuration files or code. 

IaC :

Terraform vs Terragrunt

Both Terraform and Terragrunt are Infrastructure as Code (IaC) tools


- Terraform is the core IaC tool used to provision and manage infrastructure.
- Terragrunt is a wrapper around Terraform that helps organize.



### Important distinction: MinIO versus MLflow

MinIO is not a replacement for MLflow.

-   **MinIO** stores the actual files, such as model artifacts,
    datasets, and reports.
-   **MLflow** tracks experiments, parameters, metrics, runs, and model
    lifecycle information.
-   **PostgreSQL** can store MLflow's backend metadata.
-   **MinIO** can serve as MLflow's artifact store, when configured that
    way.

Similarly, a Docker Registry stores container images; MinIO is not
normally a replacement for that registry.

## 9. Security and reliability considerations

For a production environment, pay attention to the following:

### Webhook authentication

-   Verify GitHub's webhook signature or use the relevant provider's
    authentication mechanism.
-   Reject invalid or unexpected requests.
-   Avoid trusting fields in an unverified payload.

### FastAPI security

-   Use HTTPS.
-   Apply authentication and authorization.
-   Validate request schemas and input values.
-   Avoid exposing administrative endpoints publicly.
-   Log events without recording secrets or sensitive payload contents.

### Jenkins credentials

-   Store API tokens and credentials in Jenkins Credentials or an
    approved secret manager.
-   Do not hard-code passwords or tokens in source code.
-   Use dedicated service accounts with limited permissions.

### MinIO credentials and access

-   Use dedicated service accounts and least-privilege policies.
-   Enable TLS.
-   Separate buckets or access policies where appropriate.
-   Use presigned URLs with short expiration periods when suitable.
-   Do not expose MinIO access keys to browser clients.

### Event reliability

-   Expect duplicate webhook or object-event deliveries.
-   Make event processing idempotent, so processing the same event twice
    does not cause unintended duplicate work.
-   Use retries and sensible timeouts.
-   Consider a queue or durable event-processing mechanism for workflows
    that must not lose events.
-   Record event IDs, object keys, and processing status for
    troubleshooting.

## 10. Practical learning exercise: an automated ML pipeline

A small end-to-end project is a good way to understand how all four
technologies communicate.

### Goal

Build an automated ML pipeline that starts when code is pushed to
GitHub, runs through Jenkins, stores its outputs in MinIO, and makes
evaluation results accessible through FastAPI.

### Implementation steps

1.  Create a small FastAPI application.
2.  Configure a GitHub webhook to notify the FastAPI endpoint.
3.  Push a Python code change.
4.  Have FastAPI validate the webhook and trigger Jenkins.
5.  Jenkins checks out the code and runs a Python ML training script.
6.  The script generates a model file and an evaluation JSON file.
7.  Jenkins uploads both files to MinIO.
8.  FastAPI exposes an authenticated endpoint to retrieve the evaluation
    results.
9.  Optionally, configure MinIO to notify FastAPI when a new evaluation
    object is uploaded.
10. Add tests, security checks, and deployment stages as the exercise
    grows.

### Expected end-to-end flow

``` text
Git push
   |
   v
GitHub webhook
   |
   v
FastAPI validates event
   |
   v
FastAPI triggers Jenkins
   |
   v
Jenkins checks out code
   |
   v
Jenkins runs tests and ML training
   |
   v
Jenkins generates model + evaluation.json
   |
   v
Jenkins uploads artifacts to MinIO
   |
   +------------------------------+
   |                              |
   v                              v
FastAPI API retrieves        MinIO event notification
evaluation artifacts             |
                                  v
                             FastAPI processes event
```

## 11. Key takeaways

-   **Jenkins is the worker/orchestrator for CI/CD:** it runs the
    pipeline steps.
-   **A webhook is a notification:** it tells a receiving system that an
    event has occurred.
-   **FastAPI is the API and coordination layer:** it can receive
    events, apply business rules, trigger Jenkins, and provide
    controlled access to artifacts.
-   **MinIO is object storage:** it keeps models, datasets, reports, and
    other files outside temporary build workspaces.
-   **MLflow is experiment and model tracking:** it complements MinIO
    rather than replacing it.
-   **Docker Registry and Kubernetes have separate roles:** the registry
    stores images; Kubernetes runs and manages workloads.

A useful design principle is to keep each component focused on its
responsibility. Use direct integrations when they are sufficient, and
introduce FastAPI or event-driven processing when centralized control,
application logic, or downstream workflows genuinely require them.

## 12. Architecture decision to make

Before implementing the integration, clarify the role FastAPI should
play:

**Option 1 --- Central orchestration service**

FastAPI is a central service that receives events from source-control
systems, validates them, and triggers Jenkins pipelines.

**Option 2 --- Part of each AI solution**

FastAPI already runs as part of an AI solution, and Jenkins communicates
with it for deployment, health checks, or application-specific
operations.

**Option 3 --- Both**

A central FastAPI service handles orchestration, while individual AI
solutions expose their own FastAPI APIs.

This decision affects service boundaries, authentication, network
access, deployment, and operational ownership.

## 13. Review complete (Sample Application)


78/78 tests passed locally and in Docker.
CrewAI YAML and Pydantic outputs validated.
API is healthy: http://localhost:8000/health
MinIO storage smoke test passed: http://localhost:9001
Jenkins is running: http://localhost:8081
App, MinIO, and Jenkins containers remain running.

A Jenkins Pipeline job still needs to be created from Jenkinsfile. Live OpenAI generation was not invoked to avoid API costs.