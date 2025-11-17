pipeline {
    // 1. 파이프라인 전체를 Jenkins 호스트에서 실행
    agent any

    // 2. GitHub 'main' 브랜치에 push/merge될 때 자동 실행
    triggers {
        githubPush()
    }

    // 3. 파이프라인 환경 변수 정의
    environment {
        // Docker 이미지 태그와 컨테이너 이름을 변수로 관리합니다. (백엔드용으로 변경)
        IMAGE_NAME = 'fisa-backend-app'
        CONTAINER_NAME = 'fisa-backend-container'
    }

    stages {
        // 4. Docker 이미지 빌드
        stage('Build Docker Image') {
            steps {
                echo "Building Docker image: ${IMAGE_NAME}..."
                
                sh "docker build -t ${IMAGE_NAME} ."
                
                echo "Docker image build complete."
            }
        }

        // 5. Docker 컨테이너 실행 (배포)
        stage('Run Docker Container') {
            steps {
                echo "Stopping and removing existing container: ${CONTAINER_NAME}..."
                // '|| true'는 컨테이너가 없어서 명령이 실패해도 파이프라인이 중지되지 않도록 합니다.
                sh "docker stop ${CONTAINER_NAME} || true"
                sh "docker rm ${CONTAINER_NAME} || true"
                
                echo "Starting new container: ${CONTAINER_NAME} from image ${IMAGE_NAME}..."
                
                // 컨테이너 실행 시점에 withCredentials를 사용하여 환경 변수를 주입합니다.
                withCredentials([
                    string(credentialsId: 'FRONTEND_HOST', variable: 'FRONTEND_HOST'),
                    string(credentialsId: 'LLMSERVER_URL', variable: 'LLMSERVER_URL'),
                    string(credentialsId: 'BACKEND_HOST_PORT', variable: 'BACKEND_HOST_PORT'),
                    string(credentialsId: 'DATABASE_URL', variable: 'DATABASE_URL'),
                    string(credentialsId: 'HTTPX_TIMEOUT', variable: 'HTTPX_TIMEOUT')
                ]) {
                    // -e 플래그를 사용하여 런타임 환경 변수로 전달
                    sh "docker run -d --name ${CONTAINER_NAME} -p ${BACKEND_HOST_PORT}:8000 -e FRONTEND_HOST=${FRONTEND_HOST} -e LLMSERVER_URL=${LLMSERVER_URL} -e HTTPX_TIMEOUT=${HTTPX_TIMEOUT} -e ENVIRONMENT=production -e DATABASE_URL=${DATABASE_URL} ${IMAGE_NAME}"
                }
                
                echo 'Deployment Complete!'
            }
        }
    } // End of stages

    // 6. 파이프라인 종료 후 작업
    post {
        always {
            // 작업 공간(workspace)을 정리합니다.
            echo 'Cleaning up workspace...'
            cleanWs()
        }
        success {
            echo 'Pipeline succeeded.'
        }
        failure {
            echo 'Pipeline failed.'
        }
    }
}