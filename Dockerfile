# 1단계: 기본 파이썬 이미지 설정 (슬림한 버전으로 용량 절약!)
FROM python:3.12.12-slim AS base

# 2단계: 빌드 전용 이미지 만들기
FROM base AS builder

# 필요한 시스템 패키지 설치
# (scikit-learn 등 컴파일할 때 필요)
# C 컴파일러, Make 등 빌드 도구 -> gcc (C 언어 컴파일러)
# -> rm~ (용량 줄이기 위한 정리)
RUN apt-get update && apt-get install -y \
    build-essential \  
    gcc \              
    && rm -rf /var/lib/apt/lists/*  

# 작업 디렉토리 설정 (빌드 전용)
WORKDIR /install

# requirements.txt 복사 (의존성 먼저 복사하면 캐시 재사용 가능!)
COPY requirements.txt .

# pip으로 패키지 설치 (별도 디렉토리에 설치해서 나중에 옮김)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install/local -r requirements.txt

# 3단계: 실제 실행될 최종 이미지 구성
FROM base

# 앱 실행용 디렉토리 설정
WORKDIR /app

# 빌드된 패키지 복사 (1단계에서 설치한 패키지를 이 이미지로 가져옴)
COPY --from=builder /install/local /usr/local

# 실제 Python 애플리케이션 코드 복사
# .env 같은 민감한 파일은 복사하지 않음 (외부 환경변수로 주입)
COPY . .

EXPOSE 8000

# FastAPI 서버 실행 (0.0.0.0으로 외부에서도 접근 가능하게 함)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]