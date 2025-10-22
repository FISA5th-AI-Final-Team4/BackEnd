#!/bin/bash

# 스크립트 실행 중 오류 발생 시 즉시 중단
set -e

# --- 변수 설정 ---
IMAGE_NAME="fisa-team4-backend"
# -----------------

# 1. 실행 인자($1)가 비어있는지 확인
if [ -z "$1" ]; then
  # 인자가 없으면 오류 메시지 및 사용법 출력 후 종료
  echo "❌ 오류: 이미지 버전을 입력해주세요."
  echo "사용법: $0 [버전]"
  echo "예시: $0 1.0.1-proto"
  exit 1
fi

# 2. 첫 번째 인자를 VERSION 변수에 할당
VERSION="$1"

# 최종 이미지 태그 생성 (예: fisa-team4-backend:1.0.1-proto)
TAG="${IMAGE_NAME}:${VERSION}"

# 빌드 시작 알림
echo "Docker 이미지 빌드를 시작합니다: ${TAG}"

# Docker 빌드 명령어 실행
docker build -t "${TAG}" .

# 성공 메시지 출력
echo ""
echo "✅ Docker 이미지 빌드가 성공적으로 완료되었습니다."
echo "이미지 이름: ${TAG}"