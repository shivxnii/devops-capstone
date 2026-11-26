pipeline {
  agent any
  triggers { githubPush() }            // runs on every git push (GitHub webhook -> /github-webhook/)
  environment {
    REGISTRY = 'docker.io'
    IMAGE    = "${env.DOCKERHUB_USER ?: 'shivanii2507'}/taskmanager"
    TAG      = "${env.BUILD_NUMBER}-${env.GIT_COMMIT?.take(7) ?: 'local'}"
  }
  options { timestamps(); disableConcurrentBuilds(); buildDiscarder(logRotator(numToKeepStr: '15')) }
  stages {
    stage('Checkout') { steps { checkout scm } }
    stage('Build & Unit Test') {
      steps {
        sh '''python3 -m venv .venv && . .venv/bin/activate
              pip install -q -r requirements-dev.txt
              pytest --cov=app --cov-report=xml --junitxml=report.xml'''
      }
      post { always { junit 'report.xml' } }
    }
    stage('SonarQube Analysis') {
      steps {
        withSonarQubeEnv('sonarqube') {   // token stored in Jenkins credentials, never in repo
          sh 'sonar-scanner'
        }
      }
    }
    stage('Quality Gate') { steps { timeout(time: 5, unit: 'MINUTES') { waitForQualityGate abortPipeline: true } } }
    stage('Package (Docker image)') { steps { sh 'docker build -t $IMAGE:$TAG -t $IMAGE:latest .' } }
    stage('Image Security Scan') {
      steps { sh 'trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed $IMAGE:$TAG' }
    }
    stage('Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'U', passwordVariable: 'P')]) {
          sh 'echo "$P" | docker login -u "$U" --password-stdin && docker push $IMAGE:$TAG && docker push $IMAGE:latest'
        }
      }
    }
    stage('GitOps: bump idle colour') {   // Argo CD picks up the commit and syncs the cluster
      when { branch 'main' }
      steps {
        withCredentials([usernamePassword(credentialsId: 'github-creds', usernameVariable: 'GU', passwordVariable: 'GP')]) {
          sh '''ACTIVE=$(grep -o "color: [a-z]*" k8s/app/service.yaml | tail -1 | awk '{print $2}')
                IDLE=$([ "$ACTIVE" = blue ] && echo green || echo blue)
                sed -i "s|image: .*taskmanager:.*|image: $IMAGE:$TAG|" k8s/app/deployment-$IDLE.yaml
                git config user.email ci@example.com && git config user.name jenkins-ci
                git add k8s/app && git commit -m "ci: deploy $TAG to $IDLE [skip ci]" || true
                git push https://$GU:$GP@github.com/$GU/devops-capstone.git HEAD:main'''
        }
      }
    }
  }
  post { always { sh 'docker logout || true'; cleanWs() } }
}
