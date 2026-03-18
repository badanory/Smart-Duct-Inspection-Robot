# Architecture

포트폴리오에서 빠르게 이해할 수 있도록 Mermaid 기준으로 다시 정리한 시스템 아키텍처입니다.

## 1. System Overview

```mermaid
flowchart LR
    U[Operator]

    subgraph R[Robot Platform]
        C[Camera]
        L[2D LiDAR / IMU]
        J[Raspberry Pi]
        S[STM32 Motor Control]
        C --> J
        L --> J
        J --> S
    end

    subgraph N[ROS2 Stack]
        M[SLAM Mapping]
        E[Frontier Exploration]
        P[Navigation / cmd_vel]
    end

    subgraph V[Vision Pipeline]
        T[RTSP or WebSocket Streaming]
        Y[YOLO Damage Detection]
    end

    subgraph W[Web Control Station]
        F[Flask + Socket.IO]
        H[Dashboard UI]
        D[MongoDB / Warning Logs]
    end

    J --> M
    M --> E
    E --> P
    C --> T
    T --> Y
    M --> F
    P --> F
    Y --> F
    F --> H
    F --> D
    Y --> D
    U --> H
    H --> F
```

## 2. Runtime Flow

```mermaid
sequenceDiagram
    participant O as Operator
    participant UI as Web Dashboard
    participant WS as Flask + Socket.IO
    participant ROS as rosbridge / ROS2
    participant CAM as Camera Stream
    participant YOLO as YOLO Inference
    participant DB as MongoDB

    CAM->>YOLO: RTSP or WebSocket frames
    YOLO->>WS: damage result / annotated image
    ROS->>WS: map, odom, battery, tf
    WS->>UI: live status + image + map
    O->>UI: control / start exploration
    UI->>WS: Socket.IO event
    WS->>ROS: cmd_vel / exploration command
    YOLO->>DB: warning image + metadata
    WS->>DB: final map or status logs
```

## 3. Notes

- 위 다이어그램은 "통합 시스템 구조"를 설명하기 위한 문서입니다.
- 기존 SVG 참고 자산은 `docs/raw/`에 보관했습니다.
