# Third-Party Notices

본 프로젝트는 MIT License로 배포되지만, 다음의 제3자 소프트웨어 및 데이터에 의존합니다.
각 항목은 해당 라이선스 조건에 따라 사용되며, 그 라이선스가 본 프로젝트의 MIT 라이선스보다 우선합니다.

> **중요**: 본 프로젝트의 **자체 작성 코드는 MIT License**로 배포되지만, 실행 시점에 함께 결합되는 일부 의존성은 GPL 등 다른 라이선스를 따릅니다. 이 프로젝트를 결합 저작물(combined work) 형태로 재배포하려는 경우, 각 의존성의 라이선스 조건을 모두 충족해야 합니다.

---

## Python 의존성

### python-chess
- **소스**: https://github.com/niklasf/python-chess
- **라이선스**: GPL-3.0-or-later
- **사용처**: `main.py`, `lichess_bot_engine.py`, `polyglot_book.py`
- **용도**: 체스 보드 표현, PGN 파싱, Stockfish UCI 통신, Polyglot 오프닝 북 해싱
- **참고**: python-chess는 GPL 라이선스이므로, 본 프로젝트를 python-chess와 함께 묶어 재배포하는 결합 저작물은 GPL-3.0 조건을 따라야 합니다.

### pygame
- **소스**: https://www.pygame.org/
- **라이선스**: LGPL 2.1+
- **사용처**: `main.py` — GUI 렌더링, 입력 처리, 사운드 재생
- **참고**: LGPL은 동적 링크 사용을 허용하므로 MIT 코드에서 사용 가능합니다.

### pybind11
- **소스**: https://github.com/pybind/pybind11
- **라이선스**: BSD 3-Clause
- **사용처**: `setup.py`, `chess_cpp.cpp` — C++ 엔진의 Python 바인딩
- **참고**: MIT와 호환되는 허용형 라이선스입니다.

### requests
- **소스**: https://github.com/psf/requests
- **라이선스**: Apache License 2.0
- **사용처**: `lichess_opening_book.py` — Lichess API 호출
- **참고**: MIT와 호환됩니다.

### setuptools
- **소스**: https://github.com/pypa/setuptools
- **라이선스**: MIT
- **사용처**: `setup.py` — C++ 확장 빌드

---

## 학습 시점에만 사용된 외부 소프트웨어

### Stockfish
- **소스**: https://stockfishchess.org/ (https://github.com/official-stockfish/Stockfish)
- **라이선스**: GPL-3.0
- **사용 시점**: **학습(레이블링) 시점에만 사용**. 본 레포지토리는 Stockfish 바이너리 및 소스를 포함하지 않습니다.
- **용도**: PGN 보드 상태에 대한 평가 점수 산출 → 지도학습 라벨로 활용
- **참고**: Stockfish의 평가 출력(숫자)은 저작물이 아니므로, 그 출력으로 학습한 가중치 테이블에는 GPL이 전이되지 않습니다.

---

## 데이터 / 데이터셋

### Cerebellum_Light_3Merge_200916/Cerebellum3Merge.bin
- **소스**: BrainFish 프로젝트 (https://www.zipproth.com/Brainfish)
- **라이선스**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)
- **레포 포함 여부**: **포함되지 않음** (`.gitignore`로 제외). 라이선스 파일(`Cerebellum Light license.rtf`)과 `README.TXT`만 참고용으로 포함되어 있습니다.
- **참고**: 본 데이터는 비상업적 용도에서만 사용 가능하며, 변형하여 공유하는 경우 동일 라이선스로 공유해야 합니다.

### 그랜드마스터 PGN 데이터 (chess.com)
- **출처**: chess.com (Garry Kasparov, Magnus Carlsen 등 그랜드마스터 기보 30,000건)
- **사용 시점**: **학습 시점에만 사용**. 본 레포지토리는 원본 PGN 데이터를 포함하지 않습니다.
- **용도**: 지도학습 입력 데이터
- **참고**: chess.com 이용 약관상 개인 및 교육 목적 사용이 허용되며, 본 프로젝트는 데이터를 재배포하지 않습니다.

### Lichess 오프닝 데이터 (런타임)
- **소스**: https://lichess.org/api (오프닝 익스플로러 API)
- **라이선스**: 대체로 CC0 / 공공 도메인
- **사용처**: `lichess_opening_book.py`

### saved_games/*.pgn
- **출처**: 본 프로젝트 실행 중 자동 저장된 게임 기보
- **저작권**: 본 프로젝트 작성자

---

## 자체 작성 자산

다음 자산은 본 프로젝트 작성자(박진우)의 저작물이며, MIT License로 배포됩니다.

- 모든 Python 소스 (`.py`)
- 모든 C++ 소스 (`.cpp`, `.h`)
- `images1/` 내 기물 이미지 (자체 제작 또는 자유 이용 이미지)
- `sounds/` 내 효과음 (자체 제작 또는 자유 이용 음원)
- `report/` 내 보고서 PDF / HWPX

---

## 요약

| 항목 | 라이선스 | 레포에 포함 |
|---|---|---|
| 본 프로젝트 자체 코드 | MIT | ✅ |
| python-chess | GPL-3.0+ | ❌ (pip 의존성) |
| pygame | LGPL 2.1+ | ❌ (pip 의존성) |
| pybind11 | BSD-3-Clause | ❌ (pip 의존성) |
| requests | Apache-2.0 | ❌ (pip 의존성) |
| setuptools | MIT | ❌ (pip 의존성) |
| Stockfish | GPL-3.0 | ❌ (별도 설치) |
| Cerebellum_light.bin | CC BY-NC-SA 4.0 | ❌ (gitignore) |
| 그랜드마스터 PGN | chess.com TOS | ❌ |

본 프로젝트를 학습/연구 목적으로 사용하실 때, 위 의존성들의 라이선스도 함께 확인해주시기 바랍니다.
