"""
Lichess Opening Explorer API를 활용한 온라인 오프닝 북
수백만 게임의 통계 데이터를 기반으로 최선의 수를 선택합니다.
"""

import requests
import random
from typing import Optional, List

# Lichess API 설정
LICHESS_API_URL = "https://explorer.lichess.ovh/masters"

def fen_from_moves(move_log):
    """
    moveLog에서 FEN 문자열 생성 (간단한 구현)
    실제로는 GameState에서 FEN을 생성하는 것이 더 정확합니다.
    """
    # 초기 FEN
    if not move_log:
        return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    # UCI 무브를 기반으로 FEN을 업데이트하는 것은 복잡하므로
    # 대신 move_log를 직접 사용
    return None

def get_lichess_opening_move(move_log, valid_moves, variant="standard", speeds=["blitz", "rapid", "classical"], 
                              ratings=[2000, 2200, 2500], use_masters=True):
    """
    Lichess Opening Explorer에서 오프닝 수를 가져옵니다.
    
    Args:
        move_log: 현재까지의 수순 (Move 객체 리스트)
        valid_moves: 현재 가능한 모든 수 (Move 객체 리스트)
        variant: 체스 변형 (standard, chess960 등)
        speeds: 포함할 게임 속도 리스트
        ratings: 포함할 레이팅 범위
        use_masters: 마스터 데이터베이스 사용 여부
    
    Returns:
        Move 객체 또는 None
    """
    moves_uci = ",".join([move.getChessNotation() for move in move_log])
    
    try:
        # Lichess API 요청
        params = {
            "variant": variant,
            "play": moves_uci if moves_uci else "",
        }
        
        # 마스터 데이터베이스 우선 (고수들의 게임)
        url = "https://explorer.lichess.ovh/masters" if use_masters else "https://explorer.lichess.ovh/lichess"
        
        if not use_masters:
            params["speeds"] = ",".join(speeds)
            params["ratings"] = ",".join(map(str, ratings))
        
        response = requests.get(url, params=params, timeout=0.5)
        
        if response.status_code == 200:
            data = response.json()
            return _select_move_from_response(data, valid_moves)
        else:
            return None
            
    except Exception as e:
        print(f"Lichess API 오류: {e}")
        return None

def _select_move_from_response(data, valid_moves):
    """
    API 응답에서 최선의 수를 선택합니다.
    """
    if "moves" not in data or not data["moves"]:
        return None
    
    # Lichess 응답의 각 수에는 통계가 포함됨
    # { "uci": "e2e4", "white": 1234, "draws": 567, "black": 890, "averageRating": 2500 }
    moves_data = data["moves"]
    
    # 승률 기반 정렬
    for move_data in moves_data:
        total_games = move_data.get("white", 0) + move_data.get("draws", 0) + move_data.get("black", 0)
        if total_games > 0:
            # 승률 계산 (현재 차례 기준)
            wins = move_data.get("white", 0)  # 백 차례면 백 승수
            move_data["score"] = (wins + move_data.get("draws", 0) * 0.5) / total_games
        else:
            move_data["score"] = 0
    
    # 게임 수가 많고 승률이 높은 수 선택
    # 상위 3개 중에서 확률적으로 선택 (다양성 추가)
    moves_data.sort(key=lambda x: (x.get("white", 0) + x.get("draws", 0) + x.get("black", 0)) * x.get("score", 0), 
                    reverse=True)
    
    # 상위 3개 수 중에서 가중치 기반 랜덤 선택
    top_moves = moves_data[:min(3, len(moves_data))]
    if not top_moves:
        return None
    
    # 가중치 계산 (게임 수 * 승률)
    weights = []
    for m in top_moves:
        total = m.get("white", 0) + m.get("draws", 0) + m.get("black", 0)
        weight = total * m.get("score", 0)
        weights.append(max(weight, 1))  # 최소 1
    
    # 가중치 기반 선택
    selected_move_data = random.choices(top_moves, weights=weights)[0]
    selected_uci = selected_move_data["uci"]
    
    # valid_moves에서 해당하는 Move 객체 찾기
    for valid_move in valid_moves:
        if valid_move.getChessNotation() == selected_uci:
            return valid_move
    
    return None

def get_lichess_opening_name(move_log):
    """
    Lichess API에서 현재 포지션의 오프닝 이름을 가져옵니다.
    
    Args:
        move_log: 현재까지의 수순
    
    Returns:
        오프닝 이름 문자열 또는 None
    """
    moves_uci = ",".join([move.getChessNotation() for move in move_log])
    
    try:
        params = {"variant": "standard", "play": moves_uci if moves_uci else ""}
        response = requests.get("https://explorer.lichess.ovh/masters", params=params, timeout=0.5)
        
        if response.status_code == 200:
            data = response.json()
            if "opening" in data and "name" in data["opening"]:
                return data["opening"]["name"]
    except:
        pass
    
    return None

def get_hybrid_opening_move(move_log, valid_moves, gs=None, enable_api=True):
    """
    Polyglot과 Lichess API를 결합하여 사용합니다.
    
    우선순위:
    1. Polyglot 오프닝 북 (0.001초, 수천만 포지션) - 최우선!
    2. Lichess 마스터 데이터베이스 (0.3초, enable_api=True일 때만)
    3. Lichess 일반 데이터베이스 (0.3초, enable_api=True일 때만)
    
    Args:
        move_log: 현재까지의 수순
        valid_moves: 현재 가능한 모든 수
        gs: GameState 객체 (Polyglot용)
        enable_api: Lichess API 사용 여부 (기본 True)
    
    Returns:
        Move 객체 또는 None
    """
    # 1. Polyglot 오프닝 북 최우선! (매우 빠름, 오프라인)
    if gs is not None:
        try:
            from polyglot_book import get_polyglot_move
            polyglot_move = get_polyglot_move(move_log, valid_moves, gs, "book.bin")
            if polyglot_move:
                return polyglot_move
        except Exception as e:
            pass  # Polyglot 실패해도 계속
    
    # 2. API가 비활성화되었으면 여기서 종료
    if not enable_api:
        return None
    
    # 3. Lichess 마스터 데이터베이스 (Polyglot에 없을 때만)
    lichess_move = get_lichess_opening_move(move_log, valid_moves, use_masters=True)
    if lichess_move:
        return lichess_move
    
    # 4. Lichess 일반 데이터베이스 (높은 레이팅만)
    lichess_move = get_lichess_opening_move(
        move_log, valid_moves, 
        use_masters=False, 
        speeds=["rapid", "classical"],
        ratings=[2200, 2500]
    )
    if lichess_move:
        return lichess_move
    
    return None

def get_current_opening_name(move_log):
    """
    현재 포지션의 오프닝 이름을 Lichess API에서 가져옵니다 (캐시 없음).
    
    Args:
        move_log: 현재까지의 수순
    
    Returns:
        오프닝 이름 문자열
    """
    lichess_name = get_lichess_opening_name(move_log)
    if lichess_name:
        return lichess_name
    
    return "Unknown Opening"

def get_opening_statistics(move_log):
    """
    현재 포지션의 통계를 가져옵니다 (디버깅/분석용).
    """
    moves_uci = ",".join([move.getChessNotation() for move in move_log])
    
    try:
        params = {"variant": "standard", "play": moves_uci if moves_uci else ""}
        response = requests.get("https://explorer.lichess.ovh/masters", params=params, timeout=0.5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "total_games": data.get("white", 0) + data.get("draws", 0) + data.get("black", 0),
                "moves": data.get("moves", [])
            }
    except:
        pass
    
    return None

# 오프라인 폴백용 - 가장 인기 있는 첫 수들
POPULAR_FIRST_MOVES = {
    "": ["e2e4", "d2d4", "c2c4", "g1f3"],  # 백의 첫 수
    "e2e4": ["e7e5", "c7c5", "e7e6", "c7c6", "d7d6", "g8f6"],  # 흑의 응수 (e4에 대해)
    "d2d4": ["d7d5", "g8f6", "e7e6", "f7f5"],  # 흑의 응수 (d4에 대해)
}

def get_fallback_move(move_log, valid_moves):
    """
    API 실패 시 폴백용 간단한 오프닝 (인기 있는 첫 수들).
    """
    moves_str = ",".join([move.getChessNotation() for move in move_log])
    
    if moves_str in POPULAR_FIRST_MOVES:
        popular_moves = POPULAR_FIRST_MOVES[moves_str]
        for popular_uci in popular_moves:
            for valid_move in valid_moves:
                if valid_move.getChessNotation() == popular_uci:
                    return valid_move
    
    return None

