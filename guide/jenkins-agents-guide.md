# Jenkins Pipeline Agents

In a Jenkins Declarative Pipeline, an **agent** tells Jenkins where the pipeline or a particular stage should run.

Agents are usually Jenkins controller-connected computers, virtual machines, containers, or cloud workers that execute pipeline steps.

## 1. `agent any`

`agent any` runs the entire pipeline on any available Jenkins agent.

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Building the application'
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests'
            }
        }
    }
}
```

Use this when any Jenkins worker has the tools required by the pipeline.

## 2. `agent none`

`agent none` means that the pipeline itself does not reserve an agent. Each stage must define its own agent.

```groovy
pipeline {
    agent none

    stages {
        stage('Build') {
            agent {
                label 'linux'
            }

            steps {
                echo 'Building on a Linux agent'
            }
        }

        stage('Windows Test') {
            agent {
                label 'windows'
            }

            steps {
                bat 'run-tests.bat'
            }
        }
    }
}
```

This is useful when different stages need different machines or environments.

## 3. Agent with a label

A label selects an agent with a specific name or capability.

```groovy
pipeline {
    agent {
        label 'linux'
    }

    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }
    }
}
```

The Jenkins node must have the `linux` label.

### Multiple labels

You can require an agent to have multiple labels:

```groovy
pipeline {
    agent {
        label 'linux && docker'
    }

    stages {
        stage('Build') {
            steps {
                sh 'docker build -t my-app .'
            }
        }
    }
}
```

This requires an agent with both the `linux` and `docker` labels.

You can also allow either of two labels:

```groovy
pipeline {
    agent {
        label 'linux || macos'
    }

    stages {
        stage('Build') {
            steps {
                echo 'Running on Linux or macOS'
            }
        }
    }
}
```

## 4. Docker agent

A Docker agent runs pipeline steps inside a Docker container.

```groovy
pipeline {
    agent {
        docker {
            image 'maven:3.9.9-eclipse-temurin-17'
        }
    }

    stages {
        stage('Build') {
            steps {
                sh 'mvn clean package'
            }
        }

        stage('Test') {
            steps {
                sh 'mvn test'
            }
        }
    }
}
```

This example uses a Maven Docker image containing Java 17.

Another example using Node.js:

```groovy
pipeline {
    agent {
        docker {
            image 'node:20'
        }
    }

    stages {
        stage('Install Dependencies') {
            steps {
                sh 'npm install'
            }
        }

        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
    }
}
```

## 5. Docker agent with additional options

You can configure Docker arguments and reuse the workspace.

```groovy
pipeline {
    agent {
        docker {
            image 'node:20'
            args '-u root'
            reuseNode true
        }
    }

    stages {
        stage('Build') {
            steps {
                sh 'npm install'
                sh 'npm run build'
            }
        }
    }
}
```

- `image` specifies the Docker image.
- `args` passes additional arguments to Docker.
- `reuseNode true` keeps the existing Jenkins workspace when supported.

## 6. Different agent for each stage

```groovy
pipeline {
    agent none

    stages {
        stage('Compile') {
            agent {
                label 'linux'
            }

            steps {
                sh 'gcc main.c -o app'
            }
        }

        stage('Windows Tests') {
            agent {
                label 'windows'
            }

            steps {
                bat 'test-app.bat'
            }
        }

        stage('Deploy') {
            agent {
                label 'deployment-server'
            }

            steps {
                sh './deploy.sh'
            }
        }
    }
}
```

In this example:

- `Compile` runs on a Linux agent.
- `Windows Tests` runs on a Windows agent.
- `Deploy` runs on an agent labeled `deployment-server`.

## 7. Agent for a specific stage only

You can define a global agent and override it for one stage.

```groovy
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'This stage uses any available agent'
            }
        }

        stage('Docker Build') {
            agent {
                docker {
                    image 'docker:27'
                }
            }

            steps {
                sh 'docker --version'
            }
        }
    }
}
```

The `Build` stage uses the global agent, while `Docker Build` uses its own stage-specific agent.

## 8. Complete practical example

```groovy
pipeline {
    agent none

    options {
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        APP_NAME = 'my-application'
    }

    stages {
        stage('Checkout') {
            agent {
                label 'linux'
            }

            steps {
                checkout scm
            }
        }

        stage('Build') {
            agent {
                docker {
                    image 'maven:3.9.9-eclipse-temurin-17'
                }
            }

            steps {
                sh 'mvn clean package'
            }
        }

        stage('Test') {
            agent {
                label 'linux'
            }

            steps {
                sh 'mvn test'
            }
        }

        stage('Deploy') {
            agent {
                label 'production'
            }

            when {
                branch 'main'
            }

            steps {
                sh './deploy.sh'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully'
        }

        failure {
            echo 'Pipeline failed'
        }

        always {
            echo "Finished building ${APP_NAME}"
        }
    }
}
```

## 9. Common agent choices

| Agent syntax | Meaning |
|---|---|
| `agent any` | Run on any available Jenkins agent |
| `agent none` | Do not use a global agent; stages must define agents |
| `agent { label 'linux' }` | Run on an agent labeled `linux` |
| `agent { label 'windows' }` | Run on an agent labeled `windows` |
| `agent { docker { image 'node:20' } }` | Run inside a Node.js 20 Docker container |
| `agent { docker { image 'maven:3.9.9-eclipse-temurin-17' } }` | Run inside a Maven and Java 17 Docker container |

## 10. Important notes

1. A Jenkins agent must be online before Jenkins can run a job on it.
2. The selected agent must have the required tools installed, unless those tools are provided by a Docker container.
3. Use `sh` for Linux and macOS agents.
4. Use `bat` for Windows agents.
5. Use `agent none` when different stages require different environments.
6. A stage-specific agent can override the pipeline-level agent.
7. Docker agents require Jenkins and the agent machine to be configured for Docker.
8. Labels describe an agent's operating system, installed software, hardware, or purpose.

## Simple rule

```groovy
agent any
```

Means:

> Run everything on any available agent.

```groovy
agent none
```

Means:

> Do not choose one global agent; define an agent for each stage.

```groovy
agent { label 'linux' }
```

Means:

> Run on an agent labeled `linux`.

```groovy
agent { docker { image 'node:20' } }
```

Means:

> Run inside a Node.js 20 Docker container.
