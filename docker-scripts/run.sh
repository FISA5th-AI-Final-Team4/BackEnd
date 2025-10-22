#!/bin/bash

# 스크립트 실행 중 오류 발생 시 즉시 중단
set -e

# --- 고정 변수 설정 ---
IMAGE_NAME="fisa-team4-backend"
CONTAINER_NAME="fisa-team4-backend"
CONTAINER_PORT=8000 # 컨테이너 내부 FastAPI 앱 포트
# --------------------

# 1. 인자 개수 확인 (2개 또는 3개여야 함)
if [ "$#" -ne 2 ] && [ "$#" -ne 3 ]; then
    echo "❌ 오류: 잘못된 수의 인자가 전달되었습니다."
    echo ""
    echo "사용법 1 (개발용 - 볼륨 마운트):"
    echo "  $0 [로컬 포트] [이미지 태그] [로컬 경로]"
    echo "  예시: $0 5000 1.0.0-proto \$(pwd)"
    echo ""
    echo "사용법 2 (배포용 - 마운트 없음):"
    echo "  $0 [로컬 포트] [이미지 태그]"
    echo "  예시: $0 8080 1.0.0-proto"
    exit 1
fi

# 2. 인자 개수에 따라 변수 및 마운트 옵션 설정
MOUNT_OPTION="" # 마운트 옵션 변수를 빈 문자열로 초기화

if [ "$#" -eq 3 ]; then
    # === 개발 모드 (인자 3개) ===
    LOCAL_PORT="$1"
    IMAGE_TAG="$2"
    LOCAL_PATH="$3"
    MOUNT_OPTION="-v ${LOCAL_PATH}:/app" # 마운트 옵션 설정
    echo "🚀 개발 모드로 실행합니다 (볼륨 마운트 활성화)."
else
    # === 배포 모드 (인자 2개) ===
    LOCAL_PORT="$1"
    IMAGE_TAG="$2"
    echo "🚢 배포 모드로 실행합니다 (볼륨 마운트 비활성화)."
fi


# 3. 기존에 실행 중이거나 중지된 동일 이름의 컨테이너가 있다면 알림 후 종료
if [ "$(docker ps -a -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "❌ 오류: '${CONTAINER_NAME}' 이름의 컨테이너가 이미 존재합니다."
    echo "아래 명령어로 기존 컨테이너를 삭제한 후 다시 시도하세요."
    echo "  docker stop ${CONTAINER_NAME} && docker rm ${CONTAINER_NAME}"
    exit 1
fi

# 4. 최종 이미지 이름:태그 조합
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# 4-1. .env 파일 확인
if [ ! -f ".env" ]; then
    echo "❌ 오류: .env 파일이 현재 디렉토리에 존재하지 않습니다."
    echo "컨테이너를 실행하려면 실행 위치에 .env 파일을 생성하세요."
    exit 1
fi

# 실행 시작 알림
echo "컨테이너를 실행합니다..."
echo "  - 이미지: ${FULL_IMAGE_NAME}"
echo "  - 포트: ${LOCAL_PORT} -> ${CONTAINER_PORT}"
if [ -n "$MOUNT_OPTION" ]; then # MOUNT_OPTION이 비어있지 않을 때만 경로 출력
    echo "  - 마운트: ${LOCAL_PATH} -> /app"
fi


# 5. Docker 컨테이너 실행
# MOUNT_OPTION 변수가 비어있으면 아무것도 추가되지 않고, 값이 있으면 -v 옵션이 추가됨
docker run -d \
  -p "${LOCAL_PORT}:${CONTAINER_PORT}" \
  --env-file .env \
  ${MOUNT_OPTION} \
  --name "${CONTAINER_NAME}" \
  "${FULL_IMAGE_NAME}"


# 6. 성공 메시지 출력
echo ""
echo "✅ 컨테이너가 성공적으로 실행되었습니다."
echo "브라우저에서 http://localhost:${LOCAL_PORT} 주소로 접속하세요."