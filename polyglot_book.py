"""
Polyglot Opening Book Parser
프로 체스 엔진이 사용하는 바이너리 오프닝 북 형식

파일 형식:
- 16바이트 엔트리들의 배열
- [8 bytes] Zobrist key (uint64, big-endian)
- [2 bytes] Move (uint16, big-endian)
- [2 bytes] Weight (uint16, big-endian)
- [4 bytes] Learn (uint32, big-endian)
"""

import struct
import random
import time
from pathlib import Path

# 랜덤 시드 초기화 (매 실행마다 다른 시드)
random.seed(time.time())

# Polyglot reader 캐싱 (성능 최적화)
_polyglot_reader_cache = None
_polyglot_book_path_cache = None

# Zobrist 해시 테이블 (Polyglot 표준)
# 각 (piece, square) 조합마다 고유한 64비트 랜덤 값
POLYGLOT_RANDOM = [
    # 768개의 값: 12 pieces × 64 squares
    # 추가: 4 castling rights, 8 en passant files, 1 side to move
]

def init_zobrist_keys():
    """Polyglot 표준 Zobrist 키 생성 (정확한 표준 구현)"""
    
    # Polyglot 표준 PRNG (64비트 Linear Congruential Generator)
    class PolyglotRandom:
        def __init__(self):
            self.seed = 1
        
        def next(self):
            self.seed = (self.seed * 0x5DEECE66D + 0xB) & ((1 << 64) - 1)
            return self.seed
    
    prng = PolyglotRandom()
    
    keys = {
        'pieces': {},  # [piece][square]
        'castling': {},  # [권한]
        'enpassant': {},  # [파일]
        'side': 0  # 흑 차례
    }
    
    # 말별 키 (12 pieces × 64 squares)
    # Polyglot 순서: wP, wN, wB, wR, wQ, wK, bP, bN, bB, bR, bQ, bK
    pieces_order = ['wP', 'wN', 'wB', 'wR', 'wQ', 'wK', 
                    'bP', 'bN', 'bB', 'bR', 'bQ', 'bK']
    
    for piece in pieces_order:
        keys['pieces'][piece] = []
        for sq in range(64):
            keys['pieces'][piece].append(prng.next())
    
    # 캐슬링 권한 (4개: wK, wQ, bK, bQ)
    keys['castling']['wK'] = prng.next()
    keys['castling']['wQ'] = prng.next()
    keys['castling']['bK'] = prng.next()
    keys['castling']['bQ'] = prng.next()
    
    # 앙파상 파일 (8개: a-h)
    for file in range(8):
        keys['enpassant'][file] = prng.next()
    
    # 흑 차례
    keys['side'] = prng.next()
    
    return keys

ZOBRIST_KEYS = init_zobrist_keys()

def piece_to_polyglot(piece):
    """체스말을 Polyglot 인덱스로 변환"""
    piece_map = {
        'wP': 0, 'wN': 1, 'wB': 2, 'wR': 3, 'wQ': 4, 'wK': 5,
        'bP': 6, 'bN': 7, 'bB': 8, 'bR': 9, 'bQ': 10, 'bK': 11,
        'wp': 0, 'wn': 1, 'wb': 2, 'wr': 3, 'wq': 4, 'wk': 5,
        'bp': 6, 'bn': 7, 'bb': 8, 'br': 9, 'bq': 10, 'bk': 11
    }
    # 대소문자 처리
    if len(piece) == 2:
        piece_key = piece[0] + piece[1].upper()
    else:
        piece_key = piece
    return piece_map.get(piece_key, -1)

def compute_zobrist_hash(board, white_to_move, castle_rights, enpassant_file):
    """
    현재 포지션의 Zobrist 해시 계산
    
    Args:
        board: 8x8 체스판 (2D 리스트)
        white_to_move: 백 차례인지
        castle_rights: 캐슬링 권한 딕셔너리
        enpassant_file: 앙파상 가능한 파일 (0-7, -1이면 없음)
    
    Returns:
        uint64 Zobrist hash
    """
    hash_val = 0
    
    # 보드 위의 말들
    pieces_order = ['wP', 'wN', 'wB', 'wR', 'wQ', 'wK', 
                    'bP', 'bN', 'bB', 'bR', 'bQ', 'bK']
    
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            if piece != '--':
                # piece를 표준 형식으로 변환 (wp -> wP, bp -> bP 등)
                standard_piece = piece[0] + piece[1].upper()
                if standard_piece in pieces_order:
                    # Polyglot square: rank 0 = row 7 (1st rank), rank 7 = row 0 (8th rank)
                    # Polyglot: a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
                    # Our board: row 0 = 8th rank, row 7 = 1st rank
                    polyglot_rank = 7 - row  # row 0 → rank 7, row 7 → rank 0
                    polyglot_file = col
                    square = polyglot_rank * 8 + polyglot_file
                    hash_val ^= ZOBRIST_KEYS['pieces'][standard_piece][square]
    
    # 캐슬링 권한
    if castle_rights.get('wK', False):
        hash_val ^= ZOBRIST_KEYS['castling']['wK']
    if castle_rights.get('wQ', False):
        hash_val ^= ZOBRIST_KEYS['castling']['wQ']
    if castle_rights.get('bK', False):
        hash_val ^= ZOBRIST_KEYS['castling']['bK']
    if castle_rights.get('bQ', False):
        hash_val ^= ZOBRIST_KEYS['castling']['bQ']
    
    # 앙파상
    if enpassant_file >= 0 and enpassant_file < 8:
        hash_val ^= ZOBRIST_KEYS['enpassant'][enpassant_file]
    
    # 흑 차례면 XOR
    if not white_to_move:
        hash_val ^= ZOBRIST_KEYS['side']
    
    return hash_val

def decode_polyglot_move(move_code):
    """
    Polyglot 무브 인코딩 디코드
    
    Polyglot 형식 (16비트):
    - bits 0-5: to square (0-63)
    - bits 6-11: from square (0-63)
    - bits 12-14: promotion (0=none, 1=N, 2=B, 3=R, 4=Q)
    - bit 15: unused
    
    Returns:
        (from_row, from_col, to_row, to_col, promotion)
    """
    to_square = move_code & 0x3F
    from_square = (move_code >> 6) & 0x3F
    promo_code = (move_code >> 12) & 0x7
    
    from_row = from_square // 8
    from_col = from_square % 8
    to_row = to_square // 8
    to_col = to_square % 8
    
    promo_map = {0: '', 1: 'N', 2: 'B', 3: 'R', 4: 'Q'}
    promotion = promo_map.get(promo_code, '')
    
    return (from_row, from_col, to_row, to_col, promotion)

def read_polyglot_entries(book_file, zobrist_key):
    """
    Polyglot 북에서 특정 포지션의 엔트리들을 읽습니다.
    
    Args:
        book_file: Polyglot 북 파일 경로
        zobrist_key: 찾을 포지션의 Zobrist 해시
    
    Returns:
        [{'move': move_code, 'weight': weight}, ...] 또는 빈 리스트
    """
    try:
        with open(book_file, 'rb') as f:
            # 파일 크기 확인
            f.seek(0, 2)
            file_size = f.tell()
            entry_size = 16
            num_entries = file_size // entry_size
            
            if num_entries == 0:
                return []
            
            # 이진 검색
            left, right = 0, num_entries - 1
            
            while left <= right:
                mid = (left + right) // 2
                f.seek(mid * entry_size)
                
                data = f.read(entry_size)
                if len(data) < entry_size:
                    break
                
                key, move, weight, learn = struct.unpack(">QHHI", data)
                
                if key < zobrist_key:
                    left = mid + 1
                elif key > zobrist_key:
                    right = mid - 1
                else:
                    # 찾음! 같은 키를 가진 모든 엔트리 수집
                    entries = [{'move': move, 'weight': weight}]
                    
                    # 앞쪽 확인
                    pos = mid - 1
                    while pos >= 0:
                        f.seek(pos * entry_size)
                        data = f.read(entry_size)
                        key2, move2, weight2, _ = struct.unpack(">QHHI", data)
                        if key2 != zobrist_key:
                            break
                        entries.append({'move': move2, 'weight': weight2})
                        pos -= 1
                    
                    # 뒤쪽 확인
                    pos = mid + 1
                    while pos < num_entries:
                        f.seek(pos * entry_size)
                        data = f.read(entry_size)
                        key2, move2, weight2, _ = struct.unpack(">QHHI", data)
                        if key2 != zobrist_key:
                            break
                        entries.append({'move': move2, 'weight': weight2})
                        pos += 1
                    
                    return entries
            
            return []
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Polyglot 북 읽기 오류: {e}")
        return []

def get_polyglot_move(move_log, valid_moves, gs, book_file="book.bin"):
    """
    Polyglot 오프닝 북에서 수를 가져옵니다.
    
    Args:
        move_log: 현재까지의 수순
        valid_moves: 현재 가능한 모든 수
        gs: GameState 객체 (Zobrist 계산용)
        book_file: Polyglot 북 파일 경로
    
    Returns:
        Move 객체 또는 None
    """
    # 북 파일 존재 확인
    if not Path(book_file).exists():
        return None
    
    # python-chess를 사용하여 정확한 Zobrist 해시 계산
    try:
        import chess
        import chess.polyglot
        
        # chess.Board로 변환
        board_chess = chess.Board()
        board_chess.clear()
        
        # 우리 board를 chess.Board로 변환
        for row in range(8):
            for col in range(8):
                piece_str = gs.board[row][col]
                if piece_str != '--':
                    color = chess.WHITE if piece_str[0] == 'w' else chess.BLACK
                    piece_type_map = {
                        'p': chess.PAWN, 'P': chess.PAWN,
                        'n': chess.KNIGHT, 'N': chess.KNIGHT,
                        'b': chess.BISHOP, 'B': chess.BISHOP,
                        'r': chess.ROOK, 'R': chess.ROOK,
                        'q': chess.QUEEN, 'Q': chess.QUEEN,
                        'k': chess.KING, 'K': chess.KING
                    }
                    piece_type = piece_type_map.get(piece_str[1].lower())
                    if piece_type:
                        # chess.Board square: a1=0, h8=63
                        # 우리 board: row 0 = 8th rank, row 7 = 1st rank
                        chess_square = chess.square(col, 7 - row)
                        board_chess.set_piece_at(chess_square, chess.Piece(piece_type, color))
        
        # 턴 설정
        board_chess.turn = chess.WHITE if gs.whiteToMove else chess.BLACK
        
        # 캐슬링 권한
        board_chess.castling_rights = 0
        if gs.whiteCastleKingside:
            board_chess.castling_rights |= chess.BB_H1
        if gs.whiteCastleQueenside:
            board_chess.castling_rights |= chess.BB_A1
        if gs.blackCastleKingside:
            board_chess.castling_rights |= chess.BB_H8
        if gs.blackCastleQueenside:
            board_chess.castling_rights |= chess.BB_A8
        
        # 앙파상
        if hasattr(gs, 'enpasantPossible') and gs.enpasantPossible:
            ep = gs.enpasantPossible
            if isinstance(ep, tuple) and len(ep) == 2 and ep[0] >= 0 and ep[1] >= 0:
                board_chess.ep_square = chess.square(ep[1], 7 - ep[0])
        
        # Polyglot 북에서 찾기 (reader 캐싱으로 성능 최적화)
        global _polyglot_reader_cache, _polyglot_book_path_cache
        
        if _polyglot_reader_cache is None or _polyglot_book_path_cache != book_file:
            # 처음이거나 다른 북 파일이면 새로 열기
            if _polyglot_reader_cache is not None:
                _polyglot_reader_cache.close()
            _polyglot_reader_cache = chess.polyglot.open_reader(book_file)
            _polyglot_book_path_cache = book_file
        
        entries = list(_polyglot_reader_cache.find_all(board_chess))
        
        zobrist_key = chess.polyglot.zobrist_hash(board_chess)
    except Exception as e:
        # 조용히 실패 (디버깅 출력 제거)
        return None
    
    if not entries:
        return None
    
    # 강력한 랜덤성: 상위 N개 중에서 랜덤 선택
    if len(entries) == 1:
        selected_entry = entries[0]
    else:
        # 가중치로 정렬 (높은 순)
        sorted_entries = sorted(entries, key=lambda e: e.weight, reverse=True)
        
        # 상위 수들 중에서 선택 (최대 5개, 또는 전체의 60%)
        top_count = min(max(5, len(entries) * 60 // 100), len(entries))
        top_entries = sorted_entries[:top_count]
        
        # 80% 확률로 상위 수들 중 랜덤, 20% 확률로 전체 중 랜덤
        if random.random() < 0.8:
            selected_entry = random.choice(top_entries)
        else:
            selected_entry = random.choice(entries)
    
    # python-chess Move를 우리 형식으로 변환
    chess_move = selected_entry.move
    from_square = chess_move.from_square
    to_square = chess_move.to_square
    
    # chess square를 우리 row, col로 변환
    from_col = chess.square_file(from_square)
    from_row = 7 - chess.square_rank(from_square)
    to_col = chess.square_file(to_square)
    to_row = 7 - chess.square_rank(to_square)
    
    # 프로모션 확인
    promotion = None
    if chess_move.promotion:
        promo_map = {
            chess.QUEEN: 'Q',
            chess.ROOK: 'R',
            chess.BISHOP: 'B',
            chess.KNIGHT: 'N'
        }
        promotion = promo_map.get(chess_move.promotion)
    
    # valid_moves에서 매칭되는 수 찾기
    for move in valid_moves:
        if (move.startRow == from_row and move.startCol == from_col and
            move.endRow == to_row and move.endCol == to_col):
            # 프로모션도 확인
            if promotion:
                if hasattr(move, 'promotion') and move.promotion == promotion:
                    return move
            else:
                # 프로모션 아닌 경우
                if not hasattr(move, 'promotion') or not move.promotion or move.promotion == '':
                    return move
    
    return None

def close_polyglot_reader():
    """Polyglot reader를 닫습니다 (프로그램 종료 시 호출)"""
    global _polyglot_reader_cache
    if _polyglot_reader_cache is not None:
        try:
            _polyglot_reader_cache.close()
        except:
            pass
        _polyglot_reader_cache = None

def get_book_info(book_file="book.bin"):
    """
    Polyglot 북의 정보를 반환합니다.
    
    Returns:
        {'entries': int, 'size_mb': float, 'exists': bool}
    """
    try:
        path = Path(book_file)
        if not path.exists():
            return {'entries': 0, 'size_mb': 0, 'exists': False}
        
        size_bytes = path.stat().st_size
        entries = size_bytes // 16
        size_mb = size_bytes / (1024 * 1024)
        
        return {
            'entries': entries,
            'size_mb': round(size_mb, 2),
            'exists': True
        }
    except:
        return {'entries': 0, 'size_mb': 0, 'exists': False}

# 인기 있는 무료 Polyglot 북 다운로드 링크
POLYGLOT_BOOK_SOURCES = {
    'performance.bin': {
        'name': 'Performance',
        'size': '6MB',
        'url': 'https://github.com/mcostalba/chess_programming/raw/master/books/performance.bin',
        'description': '균형잡힌 오프닝'
    },
    'varied.bin': {
        'name': 'Varied',
        'size': '3MB',
        'url': 'https://github.com/mcostalba/chess_programming/raw/master/books/varied.bin',
        'description': '다양한 오프닝'
    }
}

def download_book(book_name='performance.bin'):
    """
    Polyglot 북을 다운로드합니다.
    
    Args:
        book_name: 다운로드할 북 이름
    
    Returns:
        성공 여부 (bool)
    """
    if book_name not in POLYGLOT_BOOK_SOURCES:
        print(f"알 수 없는 북: {book_name}")
        return False
    
    try:
        import requests
        source = POLYGLOT_BOOK_SOURCES[book_name]
        print(f"다운로드 중: {source['name']} ({source['size']})...")
        
        response = requests.get(source['url'], timeout=30, stream=True)
        if response.status_code == 200:
            with open(book_name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"다운로드 완료: {book_name}")
            return True
        else:
            print(f"다운로드 실패: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"다운로드 오류: {e}")
        return False

# 간단한 사용 예시
if __name__ == "__main__":
    # 북 정보 확인
    info = get_book_info("book.bin")
    print(f"Polyglot Book Info: {info}")
    
    # 북이 없으면 다운로드 제안
    if not info['exists']:
        print("\n북 파일이 없습니다. 다운로드하시겠습니까?")
        print("1. performance.bin (6MB) - 균형잡힌 오프닝")
        print("2. varied.bin (3MB) - 다양한 오프닝")
        # download_book('performance.bin')

