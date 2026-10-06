pipeline {
  agent any
  options {
    timestamps()
    disableConcurrentBuilds()
    timeout(time: 30, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '10'))
  }
  parameters {
    booleanParam(name: 'SIMULATE_BAD_RELEASE', defaultValue: false,
      description: 'DEMO ONLY: deploy a release whose /health fails, to show the automatic rollback')
  }
  triggers {
    githubPush()                     // GitHub webhook -> build on every push
    pollSCM('H/5 * * * *')           // fallback for local Jenkins that GitHub cannot reach
  }
  environment {
    IMAGE_TAG = "${env.BUILD_NUMBER}"
    TRIVY_SEVERITY = 'HIGH,CRITICAL'
    TRIVY_EXIT_CODE = '1'            // 1 = block deploy on findings, 0 = report only
  }

  stages {
    stage('Checkout') {
      steps { checkout scm; sh 'git log -1 --oneline' }
    }

    stage('Validate') {
      steps {
        sh '''
          cp -n .env.example .env || true
          docker compose config -q            # compose file + .env interpolation is valid
          for f in scripts/*.sh; do bash -n "$f"; done   # shell syntax check
        '''
      }
    }

    stage('Build & Test') {
      steps {
        sh '''
          mkdir -p reports
          for s in product-service order-service; do
            (cd services/$s && python3 -m venv .venv && . .venv/bin/activate \
              && pip install -q -r requirements-dev.txt \
              && pytest -q --junitxml=../../reports/$s.xml)
          done
        '''
      }
      post { always { junit allowEmptyResults: true, testResults: 'reports/*.xml' } }
    }

    stage('Docker Build') {
      steps { sh 'docker compose build' }     // tags grocery-hub/<svc>:$IMAGE_TAG
    }

    stage('Trivy Scan') {
      steps { sh 'bash ./scripts/trivy_scan.sh' }
      post { always { archiveArtifacts artifacts: 'reports/trivy/*', allowEmptyArchive: true } }
    }

    stage('Deploy') {
      environment { SIMULATE_UNHEALTHY = "${params.SIMULATE_BAD_RELEASE == true}" }   // demo flag applies ONLY to deploy, not to unit tests
      steps { sh 'bash ./scripts/deploy.sh' }
    }

    stage('Health Check') {
      steps { sh 'bash ./scripts/healthcheck.sh' }
    }

    stage('Record Release & Cleanup') {
      steps { sh 'bash ./scripts/mark_good.sh && bash ./scripts/cleanup.sh' }
    }
  }

  post {
    failure {
      echo 'Pipeline failed - attempting rollback to last good release'
      sh 'bash ./scripts/rollback.sh || echo "No rollback target available"'
    }
    always { sh 'docker compose ps || true' }
  }
}
