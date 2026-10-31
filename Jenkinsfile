pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
    timeout(time: 45, unit: 'MINUTES')
  }

  environment {
    COMPOSE_FILE = 'docker-compose.yml:docker-compose.ci.yml'
    // Disposable CI-only credentials; this stack publishes no host ports.
    MINIO_ROOT_USER = 'ci-minio'
    MINIO_ROOT_PASSWORD = 'ci-only-disposable-password'
    API_ACCESS_TOKEN = 'ci-only-disposable-api-token'
    OPENAI_API_KEY = ''
    MINIO_LICENSE_FILE = '/run/secrets/minio.license'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.COMPOSE_PROJECT_NAME = "ci-${env.BUILD_TAG}".toLowerCase().replaceAll('[^a-z0-9_-]', '-')
        }
      }
    }

    stage('Validate prerequisites') {
      steps {
        sh '''
          set -eu
          docker info >/dev/null
          docker compose version
          test -s "$MINIO_LICENSE_FILE"
          docker compose config -q
        '''
      }
    }

    stage('Build image') {
      steps {
        sh 'docker compose build app'
      }
    }

    stage('Validate CrewAI configuration') {
      steps {
        sh 'docker compose run --rm --no-deps app python -c "from business_plan.crew import validate_crew_configuration; validate_crew_configuration()"'
      }
    }

    stage('Unit tests') {
      steps {
        sh '''
          set -eu
          mkdir -p reports
          rm -f reports/junit.xml
          docker compose run --name "$COMPOSE_PROJECT_NAME-tests" --no-deps -e MINIO_ENABLED=false app python -m pytest --junitxml=/tmp/junit.xml
        '''
      }
      post {
        always {
          sh 'docker cp "$COMPOSE_PROJECT_NAME-tests:/tmp/junit.xml" reports/junit.xml || true'
          junit testResults: 'reports/junit.xml', allowEmptyResults: true
        }
      }
    }

    stage('Start API and MinIO') {
      steps {
        sh '''
          set -eu
          docker compose create minio
          # docker cp streams from the Jenkins client, unlike Docker bind mounts.
          docker compose cp "$MINIO_LICENSE_FILE" minio:/licenses/minio.license
          docker compose up -d --wait --wait-timeout 120 app minio
        '''
      }
    }

    stage('Smoke test') {
      steps {
        sh 'docker compose exec -T app python scripts/smoke_test.py'
      }
    }
  }

  post {
    failure {
      script {
        if (env.COMPOSE_PROJECT_NAME?.startsWith('ci-')) {
          sh 'docker compose logs --no-color --tail=100 app minio || true'
        }
      }
    }
    cleanup {
      script {
        if (env.COMPOSE_PROJECT_NAME?.startsWith('ci-')) {
          sh '''
            docker rm -f "$COMPOSE_PROJECT_NAME-tests" >/dev/null 2>&1 || true
            docker compose down --volumes --remove-orphans
            docker image rm "$COMPOSE_PROJECT_NAME-app" >/dev/null 2>&1 || true
          '''
        }
      }
    }
  }
}
