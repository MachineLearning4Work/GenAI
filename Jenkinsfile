pipeline {
  agent any
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
    stage('Build & Tests') {
      steps {
        sh 'docker compose down --remove-orphans'
        sh 'docker compose up -d --build minio'
        sh 'python -m pytest -q'
      }
    }
    stage('Bring up stack') {
      steps {
        sh 'docker compose up -d --build'
      }
    }
  }
}
