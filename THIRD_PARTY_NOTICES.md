# Third-Party Notices

본 프로젝트는 제3자 소프트웨어 및 데이터를 사용합니다. 이 문서는 사용된 각 의존성의 출처와 라이선스를 안내하기 위한 참고 자료입니다.

> **참고**: 본 프로젝트의 자체 작성 코드는 [MIT License](LICENSE)로 배포됩니다. 다만 실행 시점에 함께 사용되는 일부 의존성은 GPL 등 다른 라이선스를 따르므로, 결합 저작물(combined work) 형태로 재배포하려는 경우에는 각 의존성의 라이선스 조건도 함께 확인할 필요가 있습니다.

---

## Python 의존성

### python-chess
- **소스**: https://github.com/niklasf/python-chess
- **라이선스**: GPL-3.0-or-later
- **사용처**: `main.py`, `lichess_bot_engine.py`, `polyglot_book.py`
- **용도**: 체스 보드 표현, PGN 파싱, Stockfish UCI 통신, Polyglot 오프닝 북 해싱
- **참고**: python-chess는 GPL 라이선스로 알려져 있으며, 본 프로젝트를 python-chess와 함께 묶어 재배포할 경우 GPL-3.0 조건과의 관계를 별도로 확인할 필요가 있습니다. 자세한 사항은 원본 라이선스를 참고해주세요.

### pygame
- **소스**: https://www.pygame.org/
- **라이선스**: LGPL 2.1+
- **사용처**: `main.py` — GUI 렌더링, 입력 처리, 사운드 재생
- **참고**: LGPL의 적용 범위는 사용 형태(정적 / 동적 링크 등)에 따라 달라질 수 있으므로, 자세한 사항은 원본 라이선스를 참고해주세요.

### pybind11
- **소스**: https://github.com/pybind/pybind11
- **라이선스**: BSD 3-Clause
- **사용처**: `setup.py`, `chess_cpp.cpp` — C++ 엔진의 Python 바인딩

### requests
- **소스**: https://github.com/psf/requests
- **라이선스**: Apache License 2.0
- **사용처**: `lichess_opening_book.py` — Lichess API 호출

### setuptools
- **소스**: https://github.com/pypa/setuptools
- **라이선스**: MIT
- **사용처**: `setup.py` — C++ 확장 빌드

---

## 학습 시점에만 사용된 외부 소프트웨어

### Stockfish
- **소스**: https://stockfishchess.org/ (https://github.com/official-stockfish/Stockfish)
- **라이선스**: GPL-3.0
- **사용 시점**: 학습(레이블링) 시점에만 외부 도구로 사용. 본 레포지토리는 Stockfish 바이너리 및 소스를 포함하지 않습니다.
- **용도**: PGN 보드 상태에 대한 평가 점수 산출 → 지도학습 라벨로 활용
- **참고**: 본 프로젝트는 Stockfish 자체를 재배포하지 않으며, 학습 과정에서 외부 도구로만 사용했습니다. Stockfish의 출력 결과를 학습 데이터로 활용한 경우의 GPL 적용 범위에 대해서는 정형화된 해석이 존재하지 않을 수 있으므로, 자세한 사항은 원본 라이선스를 참고해주세요.

---

## 데이터 / 데이터셋

### Cerebellum_Light_3Merge_200916/
- **소스**: BrainFish 프로젝트 (https://www.zipproth.com/Brainfish)
- **레포에 포함된 파일**: `Cerebellum Light license.rtf`, `README.TXT` (원본 문서 참고용)
- **레포에 포함되지 않은 파일**: 실제 데이터 파일(`Cerebellum3Merge.bin`)은 `.gitignore`로 제외되어 본 레포지토리에 포함되지 않습니다.
- **원본 데이터의 라이선스 (참고)**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)
- **참고**: 원본 데이터의 사용 조건은 BrainFish 프로젝트가 배포 시 함께 제공한 라이선스 문서를 참고해주세요.

### 그랜드마스터 PGN 데이터 (chess.com)
- **출처**: chess.com에서 참고한 그랜드마스터 기보 (Garry Kasparov, Magnus Carlsen 등) 약 30,000건
- **사용 시점**: 학습 시점에만 외부 데이터로 활용. 본 레포지토리는 원본 PGN 데이터를 포함하지 않습니다.
- **용도**: 지도학습 입력 데이터
- **참고**: 본 프로젝트는 원본 PGN 데이터를 재배포하지 않으며, 학습 결과(가중치)만을 활용합니다. 원본 데이터의 이용 조건은 chess.com의 이용 약관을 참고해주세요.

### Lichess 오프닝 데이터 (런타임)
- **소스**: https://lichess.org/api (오프닝 익스플로러 API)
- **사용처**: `lichess_opening_book.py`
- **참고**: Lichess API 및 데이터의 이용 조건은 Lichess 공식 문서를 참고해주세요.

### saved_games/*.pgn
- **출처**: 본 프로젝트 실행 중 자동 저장된 게임 기보
- **저작권**: 본 프로젝트 작성자

---

## 자체 작성 자산

다음 자산은 본 프로젝트 작성자의 저작물이며, [MIT License](LICENSE)로 배포됩니다.

- 모든 Python 소스 (`.py`)
- 모든 C++ 소스 (`.cpp`, `.h`)
- `images1/` 내 기물 이미지
- `sounds/` 내 효과음
- `report/` 내 보고서 (PDF / HWPX)

---

## 요약

| 항목 | 라이선스 (참고) | 레포에 포함 |
|---|---|---|
| 본 프로젝트 자체 코드 | MIT | ✅ |
| python-chess | GPL-3.0+ | ❌ (pip 의존성) |
| pygame | LGPL 2.1+ | ❌ (pip 의존성) |
| pybind11 | BSD-3-Clause | ❌ (pip 의존성) |
| requests | Apache-2.0 | ❌ (pip 의존성) |
| setuptools | MIT | ❌ (pip 의존성) |
| Stockfish | GPL-3.0 | ❌ (별도 설치) |
| Cerebellum_light.bin | CC BY-NC-SA 4.0 (원본 기준) | ❌ (gitignore) |
| 그랜드마스터 PGN | 원본 사이트 약관 참고 | ❌ |
| Lichess 오프닝 데이터 | 원본 사이트 약관 참고 | ❌ (런타임 API) |

본 프로젝트를 활용하실 때는 위 의존성들의 원본 라이선스를 함께 확인해주시기 바랍니다.

---

## 사용 시나리오 안내

본 프로젝트는 다양한 라이선스의 오픈소스 라이브러리에 의존하며, 특히 `python-chess`(GPL-3.0) 등과의 결합 관계에 대해서는 해석에 따라 다른 관점이 존재합니다.

- 단순 import도 결합 저작물에 해당한다고 보는 해석
- 동적 import는 결합 저작물에 해당하지 않는다고 보는 해석
- 두 해석 모두 법원의 명확한 판결로 정리된 적은 없는 것으로 알려져 있습니다.

### 시나리오별 안내

| 사용 시나리오 | 참고 | 권장 |
|---|---|---|
| 학생 포트폴리오 / 개인 학습 | ✅ 일반적으로 무리 없는 사용 형태 | 현재 상태 그대로 사용 |
| GitHub 공개 (현재 상태) | ✅ 통상적인 오픈소스 관행에 해당 | 현재 상태 그대로 사용 |
| 빌드된 형태로 묶어서 배포 / 상업적 활용 | ⚠️ 추가 확인이 필요한 형태 | 전체 라이선스를 GPL-3.0으로 전환, 또는 `python-chess`를 자체 구현으로 대체 |

### 정리

- 본 프로젝트의 라이선스 표기와 의존성 고지는 일반적인 오픈소스 관행을 참고하여 구성된 안내입니다.
- 사용 형태(개인 학습, 공개 포트폴리오 등)에 따라 관련 라이선스 조건이 달라질 수 있으므로, 본인의 사용 목적에 맞게 위의 시나리오 표를 참고해주세요.
- 본 문서는 라이선스에 대한 일반적인 안내일 뿐 법적 판단이 아니며, 추후 다른 형태로 활용하게 될 경우에는 각 의존성의 원본 라이선스를 다시 한 번 확인해보시기 바랍니다.
