"""
Chess Opening Book
주요 오프닝 정석 수순을 저장하는 데이터베이스
"""

# 오프닝 이름 매핑: {포지션 키: 오프닝 이름}
OPENING_NAMES = {
    "": "Starting Position",
    "e2e4": "King's Pawn Opening",
    "d2d4": "Queen's Pawn Opening",
    "c2c4": "English Opening",
    "g1f3": "Reti Opening",
    
    # e4 오프닝들
    "e2e4,e7e5": "King's Pawn Game",
    "e2e4,c7c5": "Sicilian Defense",
    "e2e4,e7e6": "French Defense",
    "e2e4,c7c6": "Caro-Kann Defense",
    
    "e2e4,e7e5,g1f3": "King's Knight Opening",
    "e2e4,e7e5,g1f3,b8c6": "King's Knight: Normal Variation",
    "e2e4,e7e5,g1f3,b8c6,f1b5": "Ruy Lopez (Spanish Opening)",
    "e2e4,e7e5,g1f3,b8c6,f1b5,a7a6": "Ruy Lopez: Morphy Defense",
    "e2e4,e7e5,g1f3,b8c6,f1c4": "Italian Game",
    "e2e4,e7e5,g1f3,b8c6,f1c4,f8c5": "Giuoco Piano",
    "e2e4,e7e5,g1f3,b8c6,d2d4": "Scotch Game",
    
    "e2e4,c7c5,g1f3": "Sicilian Defense: Open",
    "e2e4,c7c5,g1f3,d7d6": "Sicilian Defense: Najdorf Variation",
    "e2e4,c7c5,g1f3,b8c6": "Sicilian Defense: Old Sicilian",
    
    "e2e4,e7e6,d2d4": "French Defense",
    "e2e4,e7e6,d2d4,d7d5": "French Defense: Advance/Exchange",
    
    "e2e4,c7c6,d2d4": "Caro-Kann Defense",
    "e2e4,c7c6,d2d4,d7d5": "Caro-Kann Defense: Main Line",
    
    # d4 오프닝들
    "d2d4,d7d5": "Closed Game",
    "d2d4,g8f6": "Indian Defense",
    "d2d4,d7d5,c2c4": "Queen's Gambit",
    "d2d4,d7d5,c2c4,e7e6": "Queen's Gambit Declined",
    "d2d4,d7d5,c2c4,c7c6": "Slav Defense",
    "d2d4,d7d5,c2c4,d5c4": "Queen's Gambit Accepted",
    
    "d2d4,g8f6,c2c4": "Indian Game",
    "d2d4,g8f6,c2c4,e7e6": "Indian Defense",
    "d2d4,g8f6,c2c4,e7e6,b1c3,f8b4": "Nimzo-Indian Defense",
    "d2d4,g8f6,c2c4,g7g6": "King's Indian Defense",
    
    # 기타
    "c2c4,e7e5": "English Opening: Reversed Sicilian",
    "c2c4,g8f6": "English Opening: Anglo-Indian",
    "g1f3,d7d5": "Reti Opening: Dutch Variation",
}

# 오프닝 북: {포지션 키: [가능한 수들]}
# 포지션 키는 moveLog를 문자열로 변환한 것

OPENING_BOOK = {
    # 게임 시작
    "": ["e2e4", "d2d4", "c2c4", "g1f3"],  # 킹스 폰, 퀸스 폰, 잉글리시, 레티
    
    # === 1. e4 오프닝 ===
    "e2e4": ["e7e5", "c7c5", "e7e6", "c7c6"],  # 킹스 폰, 시칠리안, 프렌치, 카로칸
    
    # 1... e5 이후
    "e2e4,e7e5": ["g1f3", "f2f4"],  # 킹스 나이트, 킹스 갬빗
    "e2e4,e7e5,g1f3": ["b8c6", "g8f6"],  # 나이트 디펜스
    "e2e4,e7e5,g1f3,b8c6": ["f1b5", "f1c4", "d2d4"],  # 루이 로페즈, 이탈리안, 스카치
    
    # Ruy Lopez (Spanish Opening)
    "e2e4,e7e5,g1f3,b8c6,f1b5": ["a7a6", "g8f6"],
    "e2e4,e7e5,g1f3,b8c6,f1b5,a7a6": ["b5a4", "b5c6"],  # Morphy Defense
    "e2e4,e7e5,g1f3,b8c6,f1b5,a7a6,b5a4": ["g8f6"],
    "e2e4,e7e5,g1f3,b8c6,f1b5,a7a6,b5a4,g8f6": ["e1g1", "d2d3"],
    
    # Italian Game (Giuoco Piano)
    "e2e4,e7e5,g1f3,b8c6,f1c4": ["f8c5", "g8f6"],
    "e2e4,e7e5,g1f3,b8c6,f1c4,f8c5": ["c2c3", "d2d3", "b1c3"],
    "e2e4,e7e5,g1f3,b8c6,f1c4,f8c5,c2c3": ["g8f6"],
    "e2e4,e7e5,g1f3,b8c6,f1c4,f8c5,c2c3,g8f6": ["d2d4"],
    
    # Scotch Game
    "e2e4,e7e5,g1f3,b8c6,d2d4": ["e5d4"],
    "e2e4,e7e5,g1f3,b8c6,d2d4,e5d4": ["f3d4"],
    
    # Sicilian Defense
    "e2e4,c7c5": ["g1f3", "b1c3"],
    "e2e4,c7c5,g1f3": ["d7d6", "b8c6", "e7e6"],
    "e2e4,c7c5,g1f3,d7d6": ["d2d4"],
    "e2e4,c7c5,g1f3,d7d6,d2d4": ["c5d4"],
    "e2e4,c7c5,g1f3,d7d6,d2d4,c5d4": ["f3d4"],
    "e2e4,c7c5,g1f3,d7d6,d2d4,c5d4,f3d4": ["g8f6", "b8c6"],
    
    # French Defense
    "e2e4,e7e6": ["d2d4", "d2d3"],
    "e2e4,e7e6,d2d4": ["d7d5"],
    "e2e4,e7e6,d2d4,d7d5": ["b1c3", "e4d5", "e4e5"],
    
    # Caro-Kann Defense
    "e2e4,c7c6": ["d2d4", "b1c3"],
    "e2e4,c7c6,d2d4": ["d7d5"],
    "e2e4,c7c6,d2d4,d7d5": ["b1c3", "e4d5"],
    
    # === 2. d4 오프닝 ===
    "d2d4": ["d7d5", "g8f6"],
    
    # Queen's Gambit
    "d2d4,d7d5": ["c2c4", "g1f3"],
    "d2d4,d7d5,c2c4": ["e7e6", "c7c6", "d5c4"],  # QGD, Slav, QGA
    "d2d4,d7d5,c2c4,e7e6": ["b1c3"],
    "d2d4,d7d5,c2c4,e7e6,b1c3": ["g8f6", "f8e7"],
    "d2d4,d7d5,c2c4,c7c6": ["b1c3", "g1f3"],  # Slav Defense
    "d2d4,d7d5,c2c4,d5c4": ["g1f3", "e2e3"],  # Queen's Gambit Accepted
    
    # Indian Defenses
    "d2d4,g8f6": ["c2c4", "g1f3"],
    "d2d4,g8f6,c2c4": ["e7e6", "g7g6", "c7c5"],  # Nimzo/QID, King's Indian, Benoni
    "d2d4,g8f6,c2c4,e7e6": ["b1c3", "g1f3"],
    "d2d4,g8f6,c2c4,e7e6,b1c3": ["f8b4", "d7d5"],  # Nimzo-Indian, Queen's Indian
    
    # King's Indian Defense
    "d2d4,g8f6,c2c4,g7g6": ["b1c3", "g1f3"],
    "d2d4,g8f6,c2c4,g7g6,b1c3": ["f8g7"],
    "d2d4,g8f6,c2c4,g7g6,b1c3,f8g7": ["e2e4"],
    
    # === 3. c4 오프닝 (English Opening) ===
    "c2c4": ["e7e5", "g8f6", "c7c5"],
    "c2c4,e7e5": ["b1c3", "g1f3"],
    "c2c4,g8f6": ["b1c3", "g1f3"],
    "c2c4,c7c5": ["b1c3", "g1f3"],
    
    # === 4. Nf3 오프닝 (Reti) ===
    "g1f3": ["d7d5", "g8f6"],
    "g1f3,d7d5": ["c2c4", "d2d4"],
    "g1f3,g8f6": ["c2c4", "d2d4"],
}

def get_opening_name(move_log):
    """
    현재 포지션의 오프닝 이름을 반환합니다.
    
    Args:
        move_log: 현재까지의 수순 (Move 객체 리스트)
    
    Returns:
        오프닝 이름 문자열 또는 None
    """
    position_key = ",".join([move.getChessNotation() for move in move_log])
    
    # 정확한 매칭부터 시도
    if position_key in OPENING_NAMES:
        return OPENING_NAMES[position_key]
    
    # 역순으로 부분 매칭 (가장 긴 매칭 찾기)
    for i in range(len(move_log), 0, -1):
        partial_key = ",".join([move.getChessNotation() for move in move_log[:i]])
        if partial_key in OPENING_NAMES:
            return OPENING_NAMES[partial_key]
    
    return None

def get_opening_move(move_log, valid_moves):
    """
    오프닝 북에서 수를 찾습니다.
    
    Args:
        move_log: 현재까지의 수순 (Move 객체 리스트)
        valid_moves: 현재 가능한 모든 수 (Move 객체 리스트)
    
    Returns:
        Move 객체 또는 None
    """
    import random
    
    # moveLog를 문자열 키로 변환
    position_key = ",".join([move.getChessNotation() for move in move_log])
    
    # 오프닝 북에서 조회
    if position_key in OPENING_BOOK:
        book_moves = OPENING_BOOK[position_key]
        
        # 오프닝 북의 수 중에서 현재 가능한 수 필터링
        available_book_moves = []
        for book_move_str in book_moves:
            for valid_move in valid_moves:
                if valid_move.getChessNotation() == book_move_str:
                    available_book_moves.append(valid_move)
                    break
        
        # 가능한 수가 있으면 랜덤하게 선택 (다양성 추가)
        if available_book_moves:
            return random.choice(available_book_moves)
    
    return None

def is_in_opening_phase(move_log, max_moves=12):
    """
    현재 오프닝 단계인지 확인합니다.
    
    Args:
        move_log: 현재까지의 수순
        max_moves: 오프닝으로 간주할 최대 수 (기본 12수)
    
    Returns:
        bool
    """
    return len(move_log) < max_moves

def get_opening_stats():
    """오프닝 북 통계를 반환합니다."""
    total_positions = len(OPENING_BOOK)
    total_moves = sum(len(moves) for moves in OPENING_BOOK.values())
    return {
        "total_positions": total_positions,
        "total_moves": total_moves,
        "average_options": total_moves / total_positions if total_positions > 0 else 0
    }

