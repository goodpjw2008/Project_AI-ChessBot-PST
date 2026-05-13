# Chess AI — 체스에 관한 인공지능과 알고리즘 탐구

체스 인공지능에 적용할 수 있는 휴리스틱 알고리즘을 직접 구현하고, 각 알고리즘의 성능을 비교·분석한 프로젝트입니다.
고등학교 1학년 인공지능 탐구 보고서(2024.11)에서 출발하여, 이후 C++ 엔진과 Lichess 봇 연동까지 확장한 결과물입니다.

전체 보고서: [report/1407박진우_인공지능보고서_20241118.pdf](report/1407박진우_인공지능보고서_20241118.pdf)

---

## 연구 배경 및 목적

체스는 3,000개가 넘는 오프닝과 차례당 20가지 이상의 경우의 수로, 오래전부터 인공지능 탐구의 대표적인 주제로 다루어져 왔습니다.
본 프로젝트의 목적은 다음과 같습니다.

- 체스 AI에 효율적인 휴리스틱 알고리즘을 적용하고
- 각 알고리즘이 적용된 AI를 학습시켜 성능을 비교하며
- 가장 성능이 좋은 모델을 찾아내는 것

---

## 구현한 알고리즘

| # | 알고리즘 | 설명 |
|---|---|---|
| 1 | **BFS** | 시작 정점에서 가까운 정점부터 탐색. `총 합계 가중치 / 총 노드 수`가 가장 큰 노드를 선택 |
| 2 | **강화된 BFS** | 기물 가중치 기반 가지치기 + 랜덤 함수를 활용한 속도 향상 |
| 3 | **Minimax** | 짝수 깊이(자기 차례)에서 최댓값, 홀수 깊이(상대 차례)에서 최솟값을 선택하는 2인 게임 표준 알고리즘 |
| 4 | **Minimax + Alpha-Beta Pruning** | Minimax 탐색에서 최종 선택에 영향을 주지 않는 가지를 잘라내어 연산량 절감 |

데이터 분석은 Stockfish를 이용한 지도학습 방식으로 진행했습니다. 보드 데이터를 Stockfish에 입력하여 얻은 승패 가중치를 각 기물의 포지션에 적용한 뒤 평균값을 산출해 학습했습니다.

---

## 분석 결과

### 알고리즘별 성능 비교 (Depth 4)

|  | BFS | BFS + 가지치기 | Minimax | Minimax + Alpha-Beta |
|---|---|---|---|---|
| 탐색 노드 수 | 197,742 | 173,592 | 197,742 | **64,140** |
| 소요 시간 (초) | 21 | 19 | 21 | **7** |
| 정확도 (%) | 56.7 | 61.7 | 68.8 | **70.3** |
| 예상 레이팅 | 400 | 450 | 1,750 | **1,850** |

> 예상 레이팅은 Chess.com Komodo25(3200)와의 경기 후 Chess.com 리뷰 기능을 통해 산출했습니다.

### 학습 데이터 양에 따른 성능 (Minimax + Alpha-Beta, Depth 4)

| PGN 학습량 | 100 | 1,000 | 10,000 | 20,000 | 30,000 |
|---|---|---|---|---|---|
| 정확도 (%) | 62.2 | 65.8 | 69.2 | **70.3** | 69.9 |
| 레이팅 | 1,100 | 1,300 | 1,800 | **1,850** | 1,800 |

### 주요 발견

- **Alpha-Beta Pruning** 적용 시 속도가 약 3배 향상
- 평가 함수에 **포지션별 가중치**를 추가했을 때 정확도 크게 개선
- 학습 데이터는 10,000개까지 정확도가 비례 증가, 그 이후로는 증가폭 감소, 30,000개에서는 오히려 소폭 하락
- 폰: 승진 직전(7/8라인, 1/2라인)에서 가장 높은 가중치
- 나이트: 중앙 및 c3/c6/f3/f6에서 높은 가중치
- 비숍: 색에 관계없이 중앙일수록 높은 가중치
- 룩, 퀸: 중앙이 다소 높음

---

## 프로젝트 구조

```
.
├── main.py                 # Pygame 기반 체스 GUI / 게임 루프
├── engine.py / engine.cpp  # 보드 상태, 합법 수 생성 (Python / C++ 구현)
├── chessAi.py / chessAi.cpp # 탐색 및 평가 함수 (Minimax + Alpha-Beta)
├── chess_cpp.cpp           # pybind11 바인딩
├── setup.py / build.bat    # C++ 확장 빌드
├── opening_book.py         # 오프닝 단계 판정
├── lichess_opening_book.py # Lichess 오프닝 북 연동
├── polyglot_book.py        # Polyglot 포맷 오프닝 북 (book.bin)
├── pgn_utils.py            # PGN 파일 입출력 (가이드: PGN_GUIDE.md)
├── lichess_bot_engine.py   # Lichess 봇 엔진
├── images1/                # 기물 이미지 (PNG)
├── sounds/                 # 효과음 (이동/캡처/승진)
├── saved_games/            # 저장된 PGN 기보
├── book.bin                # Polyglot 오프닝 북 데이터
└── report/                 # 인공지능 탐구 보고서 (PDF/HWPX)
```

---

## 실행 방법

### 요구 사항
- Python 3.12+
- pygame
- pybind11 (C++ 엔진 빌드용)
- C++20을 지원하는 컴파일러 (MSVC, GCC, Clang)

### C++ 엔진 빌드 (선택)

성능을 위해 C++ 엔진을 빌드해서 사용하는 것을 권장합니다.

```bash
# Windows
build.bat

# macOS / Linux
python setup.py build_ext --inplace
```

빌드된 `chess_cpp.*.pyd` (또는 `.so`) 파일이 main.py에서 자동으로 로드됩니다. 빌드 실패 시 Python 구현 (`engine.py`, `chessAi.py`)으로 자동 폴백됩니다.

### 게임 실행

```bash
python main.py
```

> **참고**: 오프닝 북 데이터 `book.bin`(약 170MB)은 GitHub의 100MB 파일 제한으로 저장소에서 제외되어 있습니다. 오프닝 북 기능을 사용하려면 [Polyglot 형식의 체스 오프닝 북](https://github.com/lichess-org/chess-openings)을 별도로 다운로드하여 프로젝트 루트에 `book.bin`으로 배치해 주세요.

### Lichess 봇 실행

```bash
python lichess_bot_engine.py
```

---

## 향후 개선 방향

- 강화학습 기반 체스 AI와의 비교
- 포지션 외 **공격 가능 위치 수**, **오프닝 / 미들게임 / 엔드게임별 포지션 가중치 분리** 등 평가 요소 다양화

---

## 참고 문헌

- [Adversarial Search — Minimax & Alpha-beta Pruning](https://glanceyes.com/entry/Adversarial-Search%EC%9D%98-Minimax-Search%EC%99%80-Alpha-beta-Pruning)
- [Alpha-beta pruning — Wikipedia](https://en.wikipedia.org/wiki/Alpha%E2%80%93beta_pruning)
- [Minimax — Wikipedia](https://en.wikipedia.org/wiki/Minimax)

---

## 작성자

박진우 (1407) — 고등학교 1학년 인공지능 탐구 프로젝트 (2024.11)
