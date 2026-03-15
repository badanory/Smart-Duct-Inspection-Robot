# Legacy Deployment Notes

이 문서는 캡스톤 당시 사용했던 서버/스트리밍 운영 메모를 포트폴리오용으로 정리한 것이다.
현재 저장소는 실행 복구를 목표로 하지 않으므로, 아래 내용은 "당시 운영 방식 기록"으로 참고하면 된다.

## Placeholders

- `<EC2_PUBLIC_IP>`: EC2 퍼블릭 IPv4
- `<SSH_KEY_PATH>`: SSH 키 경로
- `<MODEL_FILE>`: 업로드할 `.pt` 파일명
- `<STREAM_SOURCE_NAME>`: Windows 카메라 장치명
- `<APP_TOKEN>`: Flask 비디오 엔드포인트 토큰
- `<RPI_IP>`: Raspberry Pi IP
- `<RPI_PASSWORD>`: Raspberry Pi 비밀번호

## EC2 Video Inference Server

### 1. 서버 접속

```powershell
ssh -i "<SSH_KEY_PATH>" ubuntu@<EC2_PUBLIC_IP>
```

### 2. 서버 내 파일 확인

```bash
ls
```

예시로 확인했던 항목:

- `app.py`
- `mediamtx`
- `mediamtx.yml`
- `venv`
- `runs`
- 모델 파일들(`best1.pt` 등)

### 3. MediaMTX 실행

```bash
./mediamtx
```

### 4. 새 세션에서 가상환경 활성화

```bash
source venv/bin/activate
```

### 5. Flask 실행

```bash
python3 app.py
```

### 6. 로컬 웹캠 영상을 RTSP로 송출

기본 모드:

```powershell
ffmpeg -f dshow -i video="<STREAM_SOURCE_NAME>" -vcodec libx264 -s 640x480 -preset ultrafast -tune zerolatency -f rtsp rtsp://<EC2_PUBLIC_IP>:8554/cam
```

저부하 모드:

```powershell
ffmpeg -f dshow -rtbufsize 50M -video_size 640x480 -framerate 30 `
  -i video="<STREAM_SOURCE_NAME>" `
  -vf "fps=10,scale=320:240" `
  -pix_fmt yuv420p -c:v libx264 -preset ultrafast -tune zerolatency `
  -r 10 -g 10 -x264-params keyint=10:min-keyint=10:scenecut=0 `
  -b:v 500k -maxrate 600k -bufsize 800k -an `
  -rtsp_transport tcp -f rtsp rtsp://<EC2_PUBLIC_IP>:8554/cam
```

### 7. 브라우저 확인

```text
http://<EC2_PUBLIC_IP>:8080/video?token=<APP_TOKEN>
```

## Model Replacement

### 1. 변수 세팅

```powershell
$IP  = "<EC2_PUBLIC_IP>"
$KEY = "<SSH_KEY_PATH>"
$SRC = "$env:USERPROFILE\\Downloads\\<MODEL_FILE>"
```

### 2. 서버로 업로드

```powershell
scp -i $KEY $SRC "ubuntu@${IP}:~/models/"
```

### 3. 서버 접속 후 모델 확인

```bash
ls -lh ~/models/
```

### 4. `app.py`에서 모델 경로 수정

예시:

```python
MODEL_PATH = "models/best_reversion.pt"
```

당시 메모에는 `nano` 기준으로 저장 절차도 남겨두었다.

- `Ctrl + O`: 저장
- `Enter`: 파일명 확정
- `Ctrl + X`: 종료

## Raspberry Pi Streaming

### 1. Pi 접속

```bash
ssh pi@<RPI_IP>
```

### 2. 카메라 스트리밍

```bash
rpicam-vid -t 0 --width 1280 --height 720 --framerate 30 \
  --codec h264 --profile baseline --inline --intra 60 --bitrate 3000000 -o - | \
ffmpeg -re -i - -c copy -f rtsp -rtsp_transport tcp \
  rtsp://<EC2_PUBLIC_IP>:8554/cam
```

## Virtual Environment Setup

```bash
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install flask ultralytics opencv-python-headless
python3 app.py
```

## MediaMTX Setup

```bash
wget https://github.com/bluenviron/mediamtx/releases/download/v1.13.1/mediamtx_v1.13.1_linux_amd64.tar.gz
tar -xvzf mediamtx_v1.13.1_linux_amd64.tar.gz
chmod +x mediamtx
./mediamtx
```

## Notes

- 실제 운영 당시에는 EC2, Raspberry Pi, 로컬 웹캠 송출 환경을 함께 사용했다.
- 현재 저장소에는 당시 인프라 전체가 남아 있지 않으므로, 위 내용은 재현 가이드라기보다 운영 기록에 가깝다.
