# ws_sender_cam.py (Windows)
# 역할: 웹캠 -> JPEG -> base64/JSON -> WebSocket 송신
# 출력: [TX] fps / Mbps / avg_payload / CPU%

import cv2, time, json, base64, websocket, psutil, argparse, statistics
from websocket import WebSocketTimeoutException  # 타임아웃 예외

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--url", type=str, default="ws://3.39.245.63:9000")
    p.add_argument("--cam", type=int, default=0)
    p.add_argument("--width", type=int, default=640)
    p.add_argument("--height", type=int, default=480)
    p.add_argument("--fps", type=int, default=10)
    p.add_argument("--jpegq", type=int, default=70)
    p.add_argument("--secs", type=int, default=600)  # 기본 10분
    p.add_argument("--preview", action="store_true")
    return p.parse_args()

def connect(url: str):
    """
    WebSocket 연결을 표준화:
    - 초기 연결 timeout 여유
    - ping/pong keepalive로 중간 단절 방지
    - 소켓 send timeout 설정
    """
    ws = websocket.create_connection(
        url,
        timeout=10,               # 초기 연결 타임아웃
        enable_multithread=True,  # 내부 send에서 멀티스레드 안전
        ping_interval=20,         # 20초마다 ping
        ping_timeout=10,          # pong 10초 대기
        ping_payload="keep",      # 구분용 페이로드
    )
    # 송신 소켓 타임아웃도 여유
    try:
        ws.sock.settimeout(10)
    except Exception:
        pass
    return ws

def safe_send_text(ws, text: str, url: str):
    """
    텍스트 프레임(JSON)을 안전하게 전송.
    - 타임아웃 나면 재연결 후 None 반환 -> 바깥에서 ws 갱신
    """
    try:
        ws.send(text)  # 기본은 텍스트 프레임
        return ws
    except WebSocketTimeoutException:
        print("[TX] send timeout → reconnect")
    except Exception as e:
        print(f"[TX] send error → reconnect: {e}")

    # 재연결
    try:
        ws.close()
    except Exception:
        pass

    for _ in range(3):
        try:
            ws2 = connect(url)
            print("[TX] reconnected")
            return ws2
        except Exception as e:
            print("[TX] reconnect fail:", e)
            time.sleep(1)

    print("[TX] abort: cannot reconnect")
    return None

def main():
    args = parse_args()
    ws = connect(args.url)

    cap = cv2.VideoCapture(args.cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS,          args.fps)

    interval   = 1.0 / max(args.fps, 1)
    t0         = time.time()
    last_stat  = t0
    frames     = 0
    bytes_total = 0
    sizes      = []

    try:
        while True:
            t_loop = time.time()

            ok, frame = cap.read()
            if not ok:
                time.sleep(0.005)
                # 타이머 갱신
                now = time.time()
                if now - t0 >= args.secs:
                    break
                continue

            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), args.jpegq])
            if not ok:
                now = time.time()
                if now - t0 >= args.secs:
                    break
                continue

            b64 = base64.b64encode(buf).decode("utf-8")
            payload = {
                "ts_send": time.time(),
                "seq": frames,
                "width": args.width,
                "height": args.height,
                "fps_target": args.fps,
                "image_b64": b64
            }
            data = json.dumps(payload)

            # 안전 송신 (타임아웃 시 내부에서 재연결 시도)
            ws2 = safe_send_text(ws, data, args.url)
            if ws2 is None:
                # 재연결 실패 → 종료
                break
            ws = ws2

            frames += 1
            bytes_total += len(data)
            sizes.append(len(data))

            if args.preview:
                # preview 옵션일 때만 GUI 사용
                try:
                    cv2.imshow("preview", frame)
                    if cv2.waitKey(1) & 0xFF == 27:
                        break
                except Exception:
                    pass

            now = time.time()
            if now - last_stat >= 1.0:
                elapsed = now - t0
                fps  = frames / elapsed if elapsed > 0 else 0.0
                mbps = (bytes_total * 8 / elapsed) / 1e6 if elapsed > 0 else 0.0
                cpu  = psutil.cpu_percent(interval=None)
                avgk = (sum(sizes)/len(sizes))/1024 if sizes else 0
                print(f"[TX] fps={fps:.2f}, Mbps={mbps:.2f}, avg_payload={avgk:.1f} KiB, CPU%={cpu:.0f}")
                last_stat = now

            # 목표 FPS에 맞춰 슬립
            delay = interval - (time.time() - t_loop)
            if delay > 0:
                time.sleep(delay)

            # 총 테스트 시간 종료 체크
            if now - t0 >= args.secs:
                break

    finally:
        cap.release()
        try:
            ws.close()
        except Exception:
            pass
        # 헤드리스 OpenCV에서도 오류 안 나게 보호
        if args.preview:
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass

        if sizes:
            avg  = sum(sizes)/len(sizes)
            stdd = statistics.pstdev(sizes) if len(sizes) > 1 else 0.0
            print(f"[SUMMARY] frames={frames}, avg_payload={avg/1024:.1f} KiB, stdev={stdd/1024:.1f} KiB")

if __name__ == "__main__":
    # 필요 패키지: opencv-python-headless, websocket-client, psutil
    main()
