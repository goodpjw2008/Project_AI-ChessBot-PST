import sys
import pygame as p
import time
import datetime

USE_CPP_ENGINE = True

try:
    if USE_CPP_ENGINE:
        import chess_cpp
        chess_cpp.initializePST()
        GameState = chess_cpp.GameState
        Move = chess_cpp.Move
    else:
        from engine import GameState, Move
        from chessAi import findRandomMoves, findBestMove
except ImportError:
    USE_CPP_ENGINE = False
    from engine import GameState, Move
    from chessAi import findRandomMoves, findBestMove

from multiprocessing import Process, Queue
import threading
import queue
import random
from opening_book import is_in_opening_phase
from lichess_opening_book import get_hybrid_opening_move, get_current_opening_name
from pgn_utils import move_to_pgn, save_game_to_pgn, load_game_from_pgn, load_game_from_clipboard, pgn_to_move
ANIMATION_TIME = 0.1
try:
    p.mixer.init()
    move_sound = p.mixer.Sound("sounds/move-sound.mp3")
    capture_sound = p.mixer.Sound("sounds/capture.mp3")
    promote_sound = p.mixer.Sound("sounds/promote.mp3")
except Exception:
    move_sound = capture_sound = promote_sound = None

BOARD_WIDTH = BOARD_HEIGHT = 512
MOVE_LOG_PANEL_WIDTH = 250
MOVE_LOG_PANEL_HEIGHT = BOARD_HEIGHT
TOP_MARGIN = 40  # 상단 여백 (오프닝 이름 표시용)
DIMENSION = 8
SQ_SIZE = BOARD_HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {}

LIGHT_SQUARE_COLOR = (237, 238, 209)
DARK_SQUARE_COLOR = (119, 153, 82)
MOVE_HIGHLIGHT_COLOR = (84, 115, 161)
POSSIBLE_MOVE_COLOR = (255, 255, 51)
MIN_AI_THINKING_DISPLAY = 0.12

colors = []
_font_cache = {}
_progress_cache = {"on": False, "last_done": 0, "last_total": 0, "last_pct": 0, "color": None, "last_nodes": 0}
_last_eval_score = 0
_last_mate_depth = 0
_baseline_nodes = 0  # AI 시작 시점의 노드 수 (현재 턴 노드만 표시하기 위함)
_last_board_hash = None  # 보드 상태 해시 (중복 렌더링 방지)
_current_opening_name = "Starting Position"  # 현재 오프닝 이름 (오프닝 끝나도 유지)

def getFont(name, size, bold=False, italic=False):
    key = (name, size, bold, italic)
    if key not in _font_cache:
        _font_cache[key] = p.font.SysFont(name, size, bold, italic)
    return _font_cache[key]

def fastBoardCopy(board):
    if USE_CPP_ENGINE:
        return [[cell for cell in row] for row in board]
    return [row[:] for row in board]

def findRandomMoves(validMoves):
    if not validMoves:
        return None
    return validMoves[random.randint(0, len(validMoves) - 1)]

def findBestMove(gs, validMoves, returnQueue, timeLimit=0.0):
    if USE_CPP_ENGINE:
        try:
            if timeLimit > 0:
                bestMove = chess_cpp.findBestMoveIterative(gs, validMoves, timeLimit)
            else:
                bestMove = chess_cpp.findBestMove(gs, validMoves)
            returnQueue.put(bestMove)
        except Exception as e:
            print(f"C++ AI 오류: {e}")
            returnQueue.put(None)
    else:
        try:
            from chessAi import findBestMove as pyFindBestMove
            pyFindBestMove(gs, validMoves, returnQueue)
        except Exception as e:
            print(f"Python AI 오류: {e}")
            returnQueue.put(None)

def loadImages():
    pieces = ['bR', 'bN', 'bB', 'bQ', 'bK',
              'bp', 'wR', 'wN', 'wB', 'wQ', 'wK', 'wp']
    for piece in pieces:
        path = f"images1/{piece}.png"
        try:    
            img = p.image.load(path)
            IMAGES[piece] = p.transform.smoothscale(img, (SQ_SIZE, SQ_SIZE))
        except Exception:
            IMAGES[piece] = None

def pawnPromotionPopup(screen, gs):
    font = p.font.SysFont("Times New Roman", 30, False, False)
    text = font.render("Choose promotion:", True, p.Color("black"))
    button_w, button_h = 100, 100
    buttons = [
        p.Rect(100, 200, button_w, button_h),
        p.Rect(220, 200, button_w, button_h),
        p.Rect(340, 200, button_w, button_h),
        p.Rect(460, 200, button_w, button_h),
    ]
    imgs = ["wQ", "wR", "wB", "wN"] if gs.whiteToMove else ["bQ", "bR", "bB", "bN"]
    button_images = []
    for imgname in imgs:
        try:
            im = p.image.load(f"images1/{imgname}.png")
            button_images.append(p.transform.smoothscale(im, (button_w, button_h)))
        except Exception:
            button_images.append(None)
    while True:
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit()
                sys.exit()
            if e.type == p.MOUSEBUTTONDOWN:
                mx, my = e.pos
                for i, btn in enumerate(buttons):
                    if btn.collidepoint(mx, my):
                        return ["Q", "R", "B", "N"][i]
        screen.fill(p.Color(LIGHT_SQUARE_COLOR))
        screen.blit(text, (110, 150))
        for i, btn in enumerate(buttons):
            p.draw.rect(screen, p.Color("white"), btn)
            bi = button_images[i]
            if bi:
                screen.blit(bi, btn.topleft)
            else:
                fnt = p.font.SysFont("Arial", 30)
                lab = fnt.render(["Q", "R", "B", "N"][i], True, p.Color('black'))
                screen.blit(lab, (btn.x + 30, btn.y + 30))
        p.display.flip()
def drawOpeningName(screen):
    """상단 여백에 오프닝 이름 표시"""
    global _current_opening_name
    
    # 상단 여백 배경 (전체 너비)
    total_width = BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 50
    top_bg_rect = p.Rect(0, 0, total_width, TOP_MARGIN)
    p.draw.rect(screen, p.Color(250, 250, 240), top_bg_rect)
    
    # 오프닝 이름 텍스트
    font = getFont("Arial", 18, True, False)
    text = font.render(_current_opening_name, True, p.Color(40, 40, 40))
    text_rect = text.get_rect(center=(total_width // 2, TOP_MARGIN // 2))
    screen.blit(text, text_rect)
    
    # 구분선
    p.draw.line(screen, p.Color(150, 150, 150), (0, TOP_MARGIN), (total_width, TOP_MARGIN), 2)

def drawPGNControls(screen):
    """Draw PGN save/load controls at the bottom."""
    total_width = BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 50
    y_pos = BOARD_HEIGHT + TOP_MARGIN - 20
    
    font = getFont("Arial", 11, False, False)
    text = font.render("'S' Save | 'L' Load from Clipboard | 'Z' Undo | 'R' Restart", True, p.Color(100, 100, 100))
    text_rect = text.get_rect(center=(total_width // 2, y_pos))
    screen.blit(text, text_rect)

def drawGameState(screen, gs, validMoves, squareSelected, moveLogFont, aiThinking=False, aiStartTime=None, aiColor=None, showEval=False, aiTimeLimit=None):
    # 최적화: 보드만 항상 그리고 나머지는 조건부로
    drawSquares(screen)
    highlightSquares(screen, gs, validMoves, squareSelected)
    drawPieces(screen, gs.board)
    drawOpeningName(screen)  # 오프닝 이름 표시
    drawMoveLog(screen, gs, moveLogFont, aiThinking)
    if showEval:
        drawEvaluationBar(screen, gs, aiThinking, aiColor)
    if aiThinking and aiStartTime is not None and aiColor is not None:
        drawAIThinking(screen, aiStartTime, aiColor, True, aiTimeLimit)
    drawPGNControls(screen)  # PGN save/load controls

def drawSquares(screen):
    global colors
    if not colors:
        colors = [p.Color(LIGHT_SQUARE_COLOR), p.Color(DARK_SQUARE_COLOR)]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[(r + c) % 2]
            p.draw.rect(screen, color, p.Rect(c*SQ_SIZE, r*SQ_SIZE + TOP_MARGIN, SQ_SIZE, SQ_SIZE))

_highlight_surface = None
_possible_move_surface = None

def highlightSquares(screen, gs, validMoves, squareSelected):
    global _highlight_surface, _possible_move_surface
    if not squareSelected:
        return
    r, c = squareSelected
    # 최적화: board 접근 캐싱
    piece = gs.board[r][c]
    expected_color = 'w' if gs.whiteToMove else 'b'
    if piece[0] != expected_color:
        return
    # Surface 한 번만 생성 (캐싱)
    if _highlight_surface is None:
        _highlight_surface = p.Surface((SQ_SIZE, SQ_SIZE))
        _highlight_surface.set_alpha(100)
        _highlight_surface.fill(p.Color(MOVE_HIGHLIGHT_COLOR))
    if _possible_move_surface is None:
        _possible_move_surface = p.Surface((SQ_SIZE, SQ_SIZE))
        _possible_move_surface.set_alpha(100)
        _possible_move_surface.fill(p.Color(POSSIBLE_MOVE_COLOR))
    screen.blit(_highlight_surface, (c*SQ_SIZE, r*SQ_SIZE + TOP_MARGIN))
    # 최적화: 같은 위치의 무브만 필터링 (조기 종료)
    for m in validMoves:
        if m.startRow == r and m.startCol == c:
            screen.blit(_possible_move_surface, (m.endCol*SQ_SIZE, m.endRow*SQ_SIZE + TOP_MARGIN))

def drawPieces(screen, board):
    # 최적화: 빈 칸 스킵 (90% 이상 빈 칸)
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                img = IMAGES.get(piece)
                if img:
                    screen.blit(img, (c*SQ_SIZE, r*SQ_SIZE + TOP_MARGIN))
                else:
                    f = getFont("Arial", SQ_SIZE//2)
                    txt = f.render(piece, True, p.Color('black'))
                    txtrect = txt.get_rect(center=(c*SQ_SIZE + SQ_SIZE//2, r*SQ_SIZE + SQ_SIZE//2 + TOP_MARGIN))
                    screen.blit(txt, txtrect)

_move_log_rect = p.Rect(BOARD_WIDTH, TOP_MARGIN, MOVE_LOG_PANEL_WIDTH, MOVE_LOG_PANEL_HEIGHT)
_move_log_bg_color = None

_last_move_log_len = 0
_move_log_surface = None

def drawMoveLog(screen, gs, font, aiThinking=False):
    global _move_log_bg_color, _last_move_log_len, _move_log_surface
    if _move_log_bg_color is None:
        _move_log_bg_color = p.Color(LIGHT_SQUARE_COLOR)
    
    # 최적화: moveLog가 변경되지 않았으면 캐시된 surface 재사용
    current_len = len(gs.moveLog)
    if _move_log_surface is not None and _last_move_log_len == current_len and not aiThinking:
        screen.blit(_move_log_surface, _move_log_rect)
        return
    
    p.draw.rect(screen, _move_log_bg_color, _move_log_rect)
    
    # 최적화: moveLog 참조 캐싱
    moves = gs.moveLog
    moves_len = len(moves)
    movesPerRow = 3
    padding = 10
    lineSpacing = 5
    textY = 130 if aiThinking else padding
    
    # 최적화: 반복 계산 제거
    black_color = p.Color('black')
    for i in range(0, moves_len, 2):
        move_num = i // 2
        col_idx = move_num % movesPerRow
        
        if col_idx != 0:
            continue
        
        # 한 줄 구성
        line_parts = [f" {move_num+1}. {moves[i]} "]
        if i + 1 < moves_len:
            line_parts.append(str(moves[i+1]))
        
        # 같은 줄의 다른 수들
        for j in range(1, movesPerRow):
            next_idx = i + j * 2
            if next_idx < moves_len:
                line_parts.append(f" {next_idx//2+1}. {moves[next_idx]} ")
                if next_idx + 1 < moves_len:
                    line_parts.append(str(moves[next_idx+1]))
        
        line = "".join(line_parts)
        txtObj = font.render(line, True, black_color)
        screen.blit(txtObj, _move_log_rect.move(padding, textY))
        textY += txtObj.get_height() + lineSpacing
    
    _last_move_log_len = current_len

def animateMove(move, screen, pre_board, clock, duration=ANIMATION_TIME):
    deltaR = move.endRow - move.startRow
    deltaC = move.endCol - move.startCol
    moving_piece = move.pieceMoved
    start_img = IMAGES.get(moving_piece)
    has_capture = move.pieceCaptured != '--'
    captured_img = IMAGES.get(move.pieceCaptured) if has_capture else None
    start_time = time.perf_counter()
    
    # 최적화: 움직이지 않는 말들 미리 계산 (TOP_MARGIN은 나중에 적용)
    static_pieces = []
    for rr in range(DIMENSION):
        for cc in range(DIMENSION):
            if rr == move.startRow and cc == move.startCol:
                continue
            if (rr == move.endRow and cc == move.endCol) and not move.isEnpassantMove:
                continue
            if move.isEnpassantMove and (rr == move.startRow and cc == move.endCol):
                continue
            piece = pre_board[rr][cc]
            if piece != "--":
                img = IMAGES.get(piece)
                if img:
                    static_pieces.append((img, cc*SQ_SIZE, rr*SQ_SIZE))  # TOP_MARGIN은 나중에
    
    while True:
        elapsed = time.perf_counter() - start_time
        t = elapsed / duration
        if t > 1:
            t = 1.0
        r = move.startRow + deltaR * t
        c = move.startCol + deltaC * t
        drawSquares(screen)
        
        # 최적화: 미리 계산된 정적 말들 blit (TOP_MARGIN 적용됨)
        for img, x, y in static_pieces:
            screen.blit(img, (x, y + TOP_MARGIN))
        if has_capture:
            if move.isEnpassantMove:
                cap_r = move.startRow
                cap_c = move.endCol
            else:
                cap_r = move.endRow
                cap_c = move.endCol
            cap_rect = p.Rect(cap_c*SQ_SIZE, cap_r*SQ_SIZE + TOP_MARGIN, SQ_SIZE, SQ_SIZE)
            if captured_img:
                screen.blit(captured_img, cap_rect)
            else:
                f = p.font.SysFont("Arial", SQ_SIZE//2)
                txt = f.render(move.pieceCaptured, True, p.Color('black'))
                txtrect = txt.get_rect(center=cap_rect.center)
                screen.blit(txt, txtrect)
        draw_rect = p.Rect(c*SQ_SIZE, r*SQ_SIZE + TOP_MARGIN, SQ_SIZE, SQ_SIZE)
        if start_img:
            screen.blit(start_img, draw_rect)
        else:
            f = p.font.SysFont("Arial", SQ_SIZE//2)
            txt = f.render(moving_piece, True, p.Color('black'))
            screen.blit(txt, (c*SQ_SIZE + 5, r*SQ_SIZE + 5 + TOP_MARGIN))
        p.display.flip()
        clock.tick(60)
        if t >= 1.0:
            break
def drawEndGameText(screen, text):
    font = p.font.SysFont("Times New Roman", 30, False, False)
    textObj = font.render(text, True, p.Color('black'))
    w = textObj.get_width(); h = textObj.get_height()
    pos = p.Rect(0, TOP_MARGIN, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH/2 - w/2, BOARD_HEIGHT/2 - h/2)
    shadow = font.render(text, False, p.Color('white'))
    screen.blit(shadow, pos.move(2,2))
    screen.blit(textObj, pos)

def drawEvaluationBar(screen, gs, aiThinking=False, aiColor=None):
    global _last_eval_score, _last_mate_depth
    barWidth = 24
    barHeight = BOARD_HEIGHT - 40
    barX = BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 15
    barY = TOP_MARGIN + 20
    
    # AI가 생각 중이고 현재 차례라면 실시간 최고 점수 사용
    if aiThinking and aiColor is not None:
        try:
            done, total, nodes, bestScore, mateDepth, depth = chess_cpp.get_progress_counters()
            # AI 관점에서 점수 조정 (AI가 흑이면 점수 반전)
            if aiColor == 'b':
                score = -bestScore
            else:
                score = bestScore
            # 마지막 평가 저장
            _last_eval_score = score
            _last_mate_depth = mateDepth
        except Exception:
            score = _last_eval_score
            mateDepth = _last_mate_depth
    else:
        # 인간 차례: 마지막 AI 평가값 유지
        score = _last_eval_score
        mateDepth = _last_mate_depth
    # 막대 표시 범위는 ±1000으로 제한하되, 실제 점수는 제한하지 않음
    display_max = 1000
    display_score = max(-display_max, min(display_max, score))
    ratio = display_score / display_max
    midY = barY + barHeight // 2
    
    # 기본 배경 (중립 회색)
    p.draw.rect(screen, p.Color(120, 120, 120), (barX, barY, barWidth, barHeight), border_radius=4)
    
    # 평가치에 따른 막대 비율 계산
    # ratio: -1.0 (흑 완전우세) ~ +1.0 (백 완전우세)
    # 중립(0.0)일 때는 반반
    
    # 흰색 막대 (아래쪽부터)
    white_ratio = 0.5 + (ratio * 0.5)  # 0.0 ~ 1.0
    white_height = int(barHeight * white_ratio)
    white_y = barY + barHeight - white_height
    p.draw.rect(screen, p.Color(240, 240, 240), (barX, white_y, barWidth, white_height), border_radius=4)
    
    # 검은색 막대 (위쪽부터)
    black_ratio = 1.0 - white_ratio  # 1.0 ~ 0.0
    black_height = int(barHeight * black_ratio)
    black_y = barY
    p.draw.rect(screen, p.Color(40, 40, 40), (barX, black_y, barWidth, black_height), border_radius=4)
    
    # 점수 텍스트
    evalFont = getFont("Arial", 10, True, False)
    CHECKMATE = 10000000
    
    # 메이트 스코어인지 확인 (CHECKMATE - 100 이상)
    if abs(score) >= CHECKMATE - 100:
        # 메이트 표시 - Mx 형태로 표시
        if aiThinking and mateDepth > 0:
            # AI가 계산한 메이트 깊이 사용
            if score > 0:
                evalText = f"M{mateDepth}"
            else:
                evalText = f"-M{mateDepth}"
        else:
            # 스코어에서 메이트 깊이 역계산
            depthToMate = CHECKMATE - abs(score)
            mateInMoves = (depthToMate + 1) // 2
            if mateInMoves == 0:
                mateInMoves = 1
            if score > 0:
                evalText = f"M{mateInMoves}"
            else:
                evalText = f"-M{mateInMoves}"
    else:
        # 실제 점수를 표시 (제한 없음)
        evalValue = score / 100.0
        if abs(evalValue) >= 100:
            # 매우 큰 값은 정수로 표시
            evalText = f"{int(evalValue):+d}"
        else:
            evalText = f"{evalValue:+.1f}"
    
    # 텍스트 색상과 위치
    if score >= 0:  # 백 우세 또는 중립 - 검은색 텍스트를 맨 아래쪽에
        txtObj = evalFont.render(evalText, True, p.Color(40, 40, 40))
        txtRect = txtObj.get_rect(center=(barX + barWidth // 2, barY + barHeight - 8))
    else:  # 흑 우세 - 흰색 텍스트를 맨 위쪽에
        txtObj = evalFont.render(evalText, True, p.Color(240, 240, 240))
        txtRect = txtObj.get_rect(center=(barX + barWidth // 2, barY + 8))
    
    screen.blit(txtObj, txtRect)
    
    # 테두리
    p.draw.rect(screen, p.Color(80, 80, 80), (barX, barY, barWidth, barHeight), 2, border_radius=4)

def drawAIThinking(screen, startTime, playerColor, isThinking=False, timeLimit=None):
    global _progress_cache, _baseline_nodes
    
    elapsed = time.perf_counter() - startTime
    rectWidth = MOVE_LOG_PANEL_WIDTH - 20
    rectHeight = 110 if timeLimit is None else 130  # 시간 제한 표시 시 더 큼
    rectX = BOARD_WIDTH + 10
    rectY = TOP_MARGIN + 10
    bgRect = p.Rect(rectX, rectY, rectWidth, rectHeight)
    p.draw.rect(screen, p.Color(40, 40, 50), bgRect, border_radius=10)
    p.draw.rect(screen, p.Color(100, 150, 255), bgRect, 3, border_radius=10)
    titleFont = getFont("Arial", 18, True, False)
    infoFont = getFont("Arial", 13, False, False)
    colorText = "White" if playerColor == 'w' else "Black"
    title = titleFont.render(f"{colorText} AI", True, p.Color(255, 255, 255))
    titleRect = title.get_rect(center=(rectX + rectWidth // 2, rectY + 22))
    screen.blit(title, titleRect)
    
    # 캐시가 초기화되었는지 확인 (새로운 AI 턴 시작)
    cache_was_reset = False
    if (not _progress_cache["on"]) or (_progress_cache["color"] != playerColor):
        _progress_cache = {"on": True, "last_done": 0, "last_total": 0, "last_pct": 0, "color": playerColor, "last_nodes": 0, "last_depth": 0}
        _baseline_nodes = 0  # 새 턴 시작 시 baseline 초기화
        cache_was_reset = True
    
    # AI가 실제로 생각 중일 때만 카운터 업데이트
    current_depth = 0
    if isThinking:
        try:
            done, total, nodes_raw, bestScore, mateDepth, current_depth = chess_cpp.get_progress_counters()
            
            # 첫 프레임에서 baseline 설정
            if cache_was_reset or _baseline_nodes == 0:
                _baseline_nodes = nodes_raw
            
            # 현재 턴에서만 사용된 노드 수 계산
            nodes = max(0, nodes_raw - _baseline_nodes)
        except Exception:
            done = total = nodes = 0
            bestScore = 0
            mateDepth = 0
            current_depth = 0
    else:
        # AI가 끝났으면 캐시된 마지막 값 사용
        done = _progress_cache.get("last_done", 0)
        total = _progress_cache.get("last_total", 0)
        nodes = _progress_cache.get("last_nodes", 0)
    
    # Depth 변경 감지
    last_depth = _progress_cache.get("last_depth", 0)
    depth_changed = (current_depth != last_depth and current_depth > 0)
    
    if total <= 0:
        progress_pct = 0
        shown_done = 0
    else:
        progress_pct = int(done * 100 / total)
        shown_done = done
        if isThinking:  # avoid jumping to 100% before search finishes
            cap_done = max(0, total - 1)
            if total > 1:
                shown_done = min(shown_done, cap_done)
                progress_pct = min(progress_pct, int(cap_done * 100 / total))
    
    # Depth가 변경되지 않았을 때만 이전 값과 비교 (감소 방지)
    if not depth_changed:
        shown_done = min(total, max(_progress_cache.get("last_done", 0), shown_done))
        progress_pct = min(100, max(_progress_cache.get("last_pct", 0), progress_pct))
    
    _progress_cache["last_done"] = shown_done
    _progress_cache["last_pct"] = progress_pct
    _progress_cache["last_nodes"] = nodes
    _progress_cache["last_depth"] = current_depth
    
    # Depth 정보 표시
    if current_depth > 0:
        depthInfo = f"D{current_depth}"
    else:
        depthInfo = ""
    
    thinkingText = infoFont.render(f"Progress: {shown_done}/{total} ({progress_pct}%)  {depthInfo}", True, p.Color(200, 220, 255))
    thinkingRect = thinkingText.get_rect(center=(rectX + rectWidth // 2, rectY + 48))
    screen.blit(thinkingText, thinkingRect)
    nodes_text = f"{nodes:,}" if isinstance(nodes, (int, float)) else str(nodes)
    timeText = infoFont.render(f"Nodes: {nodes_text}  |  Time: {elapsed:.1f}s", True, p.Color(180, 200, 255))
    timeRect = timeText.get_rect(center=(rectX + rectWidth // 2, rectY + 72))
    screen.blit(timeText, timeRect)
    # 시간 제한 표시 (활성화 시)
    if timeLimit is not None:
        remaining = max(0, timeLimit - elapsed)
        timeLimitText = infoFont.render(f"Time Limit: {remaining:.1f}s / {timeLimit:.0f}s", True, 
                                       p.Color(255, 100, 100) if remaining < 2 else p.Color(180, 200, 255))
        timeLimitRect = timeLimitText.get_rect(center=(rectX + rectWidth // 2, rectY + 96))
        screen.blit(timeLimitText, timeLimitRect)
    
    barWidth = rectWidth - 40
    barHeight = 5
    barX = rectX + 20
    barY = rectY + rectHeight - 18
    p.draw.rect(screen, p.Color(60, 60, 70), (barX, barY, barWidth, barHeight), border_radius=3)
    fill = int(barWidth * (progress_pct / 100.0))
    p.draw.rect(screen, p.Color(100, 200, 255), (barX, barY, fill, barHeight), border_radius=3)

def showSettingsMenu(screen):
    titleFont = getFont("Arial", 42, True, False)
    subtitleFont = getFont("Arial", 20, False, False)
    buttonFont = getFont("Arial", 22, True, False)
    helpFont = getFont("Arial", 16, False, False)
    smallFont = getFont("Arial", 18, False, False)
    
    # 기본 설정
    whiteIsAI = False
    blackIsAI = True
    showEvalBar = True
    timeLimitMode = False
    timeLimit = 10.0  # 기본 10초
    
    centerX = (BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 50) // 2
    buttonWidth, buttonHeight = 350, 70
    whiteButton = p.Rect(centerX - buttonWidth // 2, 160, buttonWidth, buttonHeight)
    blackButton = p.Rect(centerX - buttonWidth // 2, 240, buttonWidth, buttonHeight)
    evalButton = p.Rect(centerX - buttonWidth // 2, 320, buttonWidth, buttonHeight)
    timeModeButton = p.Rect(centerX - buttonWidth // 2, 400, buttonWidth, buttonHeight)
    
    # 슬라이더 설정
    sliderWidth = 300
    sliderHeight = 10
    sliderX = centerX - sliderWidth // 2
    sliderY = 500
    sliderRect = p.Rect(sliderX, sliderY, sliderWidth, sliderHeight)
    sliderHandleRadius = 12
    draggingSlider = False
    
    startButton = p.Rect(centerX - 100, 560, 200, 60)
    
    running = True
    clock = p.time.Clock()
    
    while running:
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit()
                sys.exit()
            
            if e.type == p.MOUSEBUTTONDOWN:
                mx, my = e.pos
                if whiteButton.collidepoint(mx, my):
                    whiteIsAI = not whiteIsAI
                elif blackButton.collidepoint(mx, my):
                    blackIsAI = not blackIsAI
                elif evalButton.collidepoint(mx, my):
                    showEvalBar = not showEvalBar
                elif timeModeButton.collidepoint(mx, my):
                    timeLimitMode = not timeLimitMode
                elif startButton.collidepoint(mx, my):
                    running = False
                elif timeLimitMode:
                    # 슬라이더 클릭/드래그 시작
                    handleX = sliderX + int((timeLimit - 1) / 59 * sliderWidth)
                    handleY = sliderY + sliderHeight // 2
                    
                    # 핸들 클릭
                    if ((mx - handleX) ** 2 + (my - handleY) ** 2) <= (sliderHandleRadius + 5) ** 2:
                        draggingSlider = True
                    # 슬라이더 바 직접 클릭
                    elif sliderRect.inflate(0, 30).collidepoint(mx, my):
                        relativeX = max(0, min(sliderWidth, mx - sliderX))
                        timeLimit = 1 + (relativeX / sliderWidth) * 59
                        timeLimit = round(timeLimit)
                        draggingSlider = True
            
            elif e.type == p.MOUSEBUTTONUP:
                draggingSlider = False
            
            elif e.type == p.MOUSEMOTION:
                if draggingSlider and timeLimitMode:
                    mx, my = e.pos
                    # 슬라이더 범위 내로 제한
                    relativeX = max(0, min(sliderWidth, mx - sliderX))
                    timeLimit = 1 + (relativeX / sliderWidth) * 59  # 1~60초
                    timeLimit = round(timeLimit)  # 정수로 반올림
        screen.fill(p.Color(240, 240, 230))
        title = titleFont.render("Chess AI Setup", True, p.Color(40, 40, 40))
        titleRect = title.get_rect(center=(centerX, 80))
        screen.blit(title, titleRect)
        subtitle = subtitleFont.render("Select player type for each side", True, p.Color(80, 80, 80))
        subtitleRect = subtitle.get_rect(center=(centerX, 130))
        screen.blit(subtitle, subtitleRect)
        buttonColor = p.Color(76, 175, 80) if whiteIsAI else p.Color(158, 158, 158)
        hoverColor = p.Color(102, 187, 106) if whiteIsAI else p.Color(189, 189, 189)
        if whiteButton.collidepoint(p.mouse.get_pos()):
            p.draw.rect(screen, hoverColor, whiteButton, border_radius=10)
        else:
            p.draw.rect(screen, buttonColor, whiteButton, border_radius=10)
        p.draw.rect(screen, p.Color('black'), whiteButton, 3, border_radius=10)
        whiteText = buttonFont.render(
            f"White: {'AI' if whiteIsAI else 'Human'}", 
            True, p.Color('white')
        )
        whiteTextRect = whiteText.get_rect(center=whiteButton.center)
        screen.blit(whiteText, whiteTextRect)
        buttonColor = p.Color(76, 175, 80) if blackIsAI else p.Color(158, 158, 158)
        hoverColor = p.Color(102, 187, 106) if blackIsAI else p.Color(189, 189, 189)
        if blackButton.collidepoint(p.mouse.get_pos()):
            p.draw.rect(screen, hoverColor, blackButton, border_radius=10)
        else:
            p.draw.rect(screen, buttonColor, blackButton, border_radius=10)
        p.draw.rect(screen, p.Color('black'), blackButton, 3, border_radius=10)
        blackText = buttonFont.render(
            f"Black: {'AI' if blackIsAI else 'Human'}", 
            True, p.Color('white')
        )
        blackTextRect = blackText.get_rect(center=blackButton.center)
        screen.blit(blackText, blackTextRect)
        buttonColor = p.Color(76, 175, 80) if showEvalBar else p.Color(158, 158, 158)
        hoverColor = p.Color(102, 187, 106) if showEvalBar else p.Color(189, 189, 189)
        if evalButton.collidepoint(p.mouse.get_pos()):
            p.draw.rect(screen, hoverColor, evalButton, border_radius=10)
        else:
            p.draw.rect(screen, buttonColor, evalButton, border_radius=10)
        p.draw.rect(screen, p.Color('black'), evalButton, 3, border_radius=10)
        evalText = buttonFont.render(
            f"Eval Bar: {'ON' if showEvalBar else 'OFF'}", 
            True, p.Color('white')
        )
        evalTextRect = evalText.get_rect(center=evalButton.center)
        screen.blit(evalText, evalTextRect)
        
        # Time Limit Mode 버튼
        buttonColor = p.Color(76, 175, 80) if timeLimitMode else p.Color(158, 158, 158)
        hoverColor = p.Color(102, 187, 106) if timeLimitMode else p.Color(189, 189, 189)
        if timeModeButton.collidepoint(p.mouse.get_pos()):
            p.draw.rect(screen, hoverColor, timeModeButton, border_radius=10)
        else:
            p.draw.rect(screen, buttonColor, timeModeButton, border_radius=10)
        p.draw.rect(screen, p.Color('black'), timeModeButton, 3, border_radius=10)
        timeModeText = buttonFont.render(
            f"Time Limit: {'ON' if timeLimitMode else 'OFF'}", 
            True, p.Color('white')
        )
        timeModeTextRect = timeModeText.get_rect(center=timeModeButton.center)
        screen.blit(timeModeText, timeModeTextRect)
        
        # 슬라이더 (Time Limit ON일 때만 표시)
        if timeLimitMode:
            # 라벨
            timeLimitLabel = smallFont.render(f"AI Time Limit: {int(timeLimit)}s", True, p.Color(60, 60, 60))
            labelRect = timeLimitLabel.get_rect(center=(centerX, sliderY - 20))
            screen.blit(timeLimitLabel, labelRect)
            
            # 슬라이더 배경 (트랙)
            p.draw.rect(screen, p.Color(180, 180, 180), sliderRect, border_radius=5)
            
            # 슬라이더 채워진 부분
            fillWidth = int((timeLimit - 1) / 59 * sliderWidth)
            fillRect = p.Rect(sliderX, sliderY, fillWidth, sliderHeight)
            p.draw.rect(screen, p.Color(33, 150, 243), fillRect, border_radius=5)
            
            # 슬라이더 핸들
            handleX = sliderX + int((timeLimit - 1) / 59 * sliderWidth)
            handleY = sliderY + sliderHeight // 2
            p.draw.circle(screen, p.Color(33, 150, 243), (handleX, handleY), sliderHandleRadius)
            p.draw.circle(screen, p.Color('white'), (handleX, handleY), sliderHandleRadius - 3)
            
            # 눈금 표시 (1s, 15s, 30s, 45s, 60s)
            tickFont = getFont("Arial", 11, False, False)
            ticks = [1, 15, 30, 45, 60]
            for tick in ticks:
                tickX = sliderX + int((tick - 1) / 59 * sliderWidth)
                tickY = sliderY + sliderHeight + 15
                tickText = tickFont.render(f"{tick}s", True, p.Color(120, 120, 120))
                tickRect = tickText.get_rect(center=(tickX, tickY))
                screen.blit(tickText, tickRect)
        
        # Start Game 버튼
        startBtnColor = p.Color(33, 150, 243)
        startHoverColor = p.Color(66, 165, 245)
        if startButton.collidepoint(p.mouse.get_pos()):
            p.draw.rect(screen, startHoverColor, startButton, border_radius=10)
        else:
            p.draw.rect(screen, startBtnColor, startButton, border_radius=10)
        p.draw.rect(screen, p.Color('black'), startButton, 3, border_radius=10)
        startText = buttonFont.render("Start Game", True, p.Color('white'))
        startTextRect = startText.get_rect(center=startButton.center)
        screen.blit(startText, startTextRect)
        p.display.flip()
        clock.tick(30)
    screen.fill(p.Color(LIGHT_SQUARE_COLOR))
    p.display.flip()
    return whiteIsAI, blackIsAI, showEvalBar, timeLimitMode, timeLimit
def main():
    global _current_opening_name, _progress_cache
    
    p.init()
    # 설정 메뉴를 위해 더 큰 화면 (일시적)
    screen = p.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 50, max(BOARD_HEIGHT + TOP_MARGIN, 650)))
    clock = p.time.Clock()
    moveLogFont = getFont("Times New Roman", 12, False, False)
    loadImages()
    whiteIsAI, blackIsAI, showEvalBar, timeLimitMode, timeLimit = showSettingsMenu(screen)
    
    # 게임 화면 크기로 재설정
    screen = p.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 50, BOARD_HEIGHT + TOP_MARGIN))
    
    gs = GameState()
    if gs.playerWantsToPlayAsBlack:
        gs.board = gs.board1
    validMoves = gs.getValidMoves()
    moveMade = False
    animate = False
    running = True
    squareSelected = ()
    playerClicks = []
    gameOver = False
    playerWhiteHuman = not whiteIsAI
    playerBlackHuman = not blackIsAI
    aiTimeLimit = timeLimit  # AI 시간 제한
    aiTimeLimitEnabled = timeLimitMode  # 시간 제한 모드
    AIThinking = False
    AIThinkingStartTime = None
    AIThinkingColor = None
    AIIndicatorUntil = 0.0
    moveFinderProcess = None
    moveUndone = False
    usingOpeningBook = False
    openingBookActive = True  # 오프닝 북이 활성화되어 있는지 (한번 실패하면 False)
    pieceCaptured = False
    pre_move_board = None
    pgn_move_log = []  # PGN notation for saving games
    drawGameState(screen, gs, validMoves, squareSelected, moveLogFont, False, None, None, showEvalBar, None)
    p.display.flip()

    while running:
        humanTurn = (gs.whiteToMove and playerWhiteHuman) or (not gs.whiteToMove and playerBlackHuman)

        # 이벤트 처리 (응답 없음 방지)
        p.event.pump()  # 이벤트 큐 업데이트
        
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False

            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver and humanTurn:
                    location = p.mouse.get_pos()
                    col = location[0] // SQ_SIZE
                    row = (location[1] - TOP_MARGIN) // SQ_SIZE
                    if col >= 8:
                        squareSelected = ()
                        playerClicks = []
                        continue
                    if squareSelected == (row, col):
                        squareSelected = ()
                        playerClicks = []
                    else:
                        squareSelected = (row, col)
                        playerClicks.append(squareSelected)
                    if len(playerClicks) == 2:
                        if USE_CPP_ENGINE:
                            attempted = Move(playerClicks[0][0], playerClicks[0][1], 
                                           playerClicks[1][0], playerClicks[1][1], gs.board)
                        else:
                            attempted = Move(playerClicks[0], playerClicks[1], gs.board)
                        candidateMoves = []
                        for mv in validMoves:
                            if mv.startRow == attempted.startRow and mv.startCol == attempted.startCol and mv.endRow == attempted.endRow and mv.endCol == attempted.endCol:
                                candidateMoves.append(mv)
                        if not candidateMoves:
                            playerClicks = [squareSelected]
                        else:
                            chosen = None
                            if USE_CPP_ENGINE:
                                promoCandidates = [m for m in candidateMoves if m.promotion != ""]
                            else:
                                promoCandidates = [m for m in candidateMoves if m.promotion is not None]
                            if promoCandidates:
                                promotion_choice = pawnPromotionPopup(screen, gs)
                                for m in promoCandidates:
                                    if m.promotion == promotion_choice:
                                        chosen = m
                                        break
                            else:
                                chosen = candidateMoves[0]
                            if chosen:
                                pre_move_board = fastBoardCopy(gs.board)
                                if gs.board[chosen.endRow][chosen.endCol] != '--':
                                    pieceCaptured = True
                                
                                # Make move and check for check/checkmate
                                gs.makeMove(chosen)
                                is_check = gs.inCheck
                                is_checkmate = gs.checkmate
                                
                                # Generate PGN notation with check symbols
                                # Need to undo to get proper game state for notation
                                gs.undoMove()
                                pgn_notation = move_to_pgn(gs, chosen, is_check, is_checkmate)
                                gs.makeMove(chosen)
                                
                                pgn_move_log.append((chosen, pgn_notation))
                                
                                has_promotion_human = (chosen.promotion != "" if USE_CPP_ENGINE else chosen.promotion is not None)
                                if has_promotion_human:
                                    if promote_sound: promote_sound.play()
                                    pieceCaptured = False
                                elif pieceCaptured or chosen.isEnpassantMove:
                                    if capture_sound: capture_sound.play()
                                else:
                                    if move_sound: move_sound.play()
                                pieceCaptured = False
                                moveMade = True
                                animate = True
                                squareSelected = ()
                                playerClicks = []
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:
                    if USE_CPP_ENGINE and AIThinking and moveFinderProcess and moveFinderProcess.is_alive():
                        continue
                    gs.undoMove()
                    if pgn_move_log:
                        pgn_move_log.pop()  # Remove last move from PGN log
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking and moveFinderProcess:
                        if not USE_CPP_ENGINE:
                            moveFinderProcess.terminate()
                        AIThinking = False
                        AIIndicatorUntil = time.perf_counter() + 0.3
                    moveUndone = True
                elif e.key == p.K_s:
                    # Save game to PGN
                    if len(pgn_move_log) > 0:
                        result = "*"
                        if gameOver:
                            if gs.checkmate:
                                result = "0-1" if gs.whiteToMove else "1-0"
                            else:
                                result = "1/2-1/2"
                        
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # Create directory if needed
                        import os
                        save_dir = "saved_games"
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir, exist_ok=True)
                        
                        pgn_filename = os.path.join(save_dir, f"game_{timestamp}.pgn")
                        
                        if save_game_to_pgn(pgn_move_log, result, playerWhiteHuman, pgn_filename, _current_opening_name):
                            abs_path = os.path.abspath(pgn_filename)
                            print(f"[OK] Game saved to: {abs_path}")
                            print(f"     Moves: {len(pgn_move_log)}, Result: {result}")
                        else:
                            print("[ERROR] Failed to save game")
                    else:
                        print("[INFO] No moves to save - play some moves first!")
                
                elif e.key == p.K_l:
                    # Load game from PGN (clipboard)
                    if USE_CPP_ENGINE and AIThinking and moveFinderProcess and moveFinderProcess.is_alive():
                        continue
                    
                    print("Loading PGN from clipboard...")
                    print("Please paste your PGN in the console and press Enter (or Ctrl+C to cancel)")
                    
                    # Read from clipboard
                    result = load_game_from_clipboard()
                    
                    if result:
                        move_list, metadata = result
                        # Reset game
                        gs = GameState()
                        validMoves = gs.getValidMoves()
                        pgn_move_log = []
                        
                        # Replay moves
                        successful_moves = 0
                        for pgn_notation in move_list:
                            move = pgn_to_move(gs, pgn_notation)
                            if move:
                                pgn_move_log.append((move, pgn_notation))
                                gs.makeMove(move)
                                validMoves = gs.getValidMoves()
                                successful_moves += 1
                            else:
                                print(f"Invalid move in PGN: {pgn_notation} (stopped at move {successful_moves})")
                                break
                        
                        moveMade = True
                        animate = False
                        gameOver = False
                        
                        opening = metadata.get('Opening', 'Unknown')
                        white = metadata.get('White', 'Unknown')
                        black = metadata.get('Black', 'Unknown')
                        result_str = metadata.get('Result', '*')
                        
                        print(f"[OK] Game loaded successfully!")
                        print(f"   Opening: {opening}")
                        print(f"   White: {white}")
                        print(f"   Black: {black}")
                        print(f"   Result: {result_str}")
                        print(f"   Moves loaded: {successful_moves}")
                    else:
                        print("[ERROR] Failed to load game from clipboard")
                        print("   Make sure you copied valid PGN text")
                
                elif e.key == p.K_r:
                    if USE_CPP_ENGINE and AIThinking and moveFinderProcess and moveFinderProcess.is_alive():
                        continue
                    whiteIsAI, blackIsAI, showEvalBar, timeLimitMode, timeLimit = showSettingsMenu(screen)
                    # 화면 크기 재설정
                    screen = p.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH + 50, BOARD_HEIGHT + TOP_MARGIN))
                    playerWhiteHuman = not whiteIsAI
                    playerBlackHuman = not blackIsAI
                    aiTimeLimit = timeLimit
                    aiTimeLimitEnabled = timeLimitMode
                    gs = GameState()
                    validMoves = gs.getValidMoves()
                    squareSelected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    gameOver = False
                    openingBookActive = True  # 게임 재시작 시 오프닝 북 다시 활성화
                    _current_opening_name = "Starting Position"  # 오프닝 이름 초기화
                    pgn_move_log = []  # Reset PGN log
                    if AIThinking and moveFinderProcess:
                        if not USE_CPP_ENGINE:
                            moveFinderProcess.terminate()
                        AIThinking = False
                        AIIndicatorUntil = time.perf_counter() + 0.3
                    moveUndone = True
                    drawGameState(screen, gs, validMoves, squareSelected, moveLogFont, False, None, None, showEvalBar, None)
                    p.display.flip()
        if not gameOver and not humanTurn and not moveUndone:
            if not AIThinking:
                # 오프닝 북 체크 (초반 20수 이내 - Lichess API 사용)
                opening_book_used = False
                if openingBookActive and is_in_opening_phase(gs.moveLog, max_moves=20):
                    try:
                        # openingBookActive 플래그를 enable_api로 전달, gs도 전달 (Polyglot용)
                        opening_move = get_hybrid_opening_move(gs.moveLog, validMoves, gs, enable_api=openingBookActive)
                    except Exception as e:
                        print(f"오프닝 북 오류: {e}")
                        opening_move = None  # API 실패 시 None
                    
                    if opening_move:
                        # 오프닝 북에서 수를 찾음 - 즉시 실행
                        opening_book_used = True
                        pre_move_board = fastBoardCopy(gs.board)
                        if gs.board[opening_move.endRow][opening_move.endCol] != '--':
                            pieceCaptured = True
                        
                        # Make move and check for check/checkmate
                        gs.makeMove(opening_move)
                        is_check = gs.inCheck
                        is_checkmate = gs.checkmate
                        
                        # Generate PGN notation with check symbols
                        gs.undoMove()
                        pgn_notation = move_to_pgn(gs, opening_move, is_check, is_checkmate)
                        gs.makeMove(opening_move)
                        
                        pgn_move_log.append((opening_move, pgn_notation))
                        
                        has_promotion = (opening_move.promotion != "" if USE_CPP_ENGINE else opening_move.promotion is not None)
                        if has_promotion:
                            if promote_sound: promote_sound.play()
                            pieceCaptured = False
                        elif pieceCaptured or opening_move.isEnpassantMove:
                            if capture_sound: capture_sound.play()
                        else:
                            if move_sound: move_sound.play()
                        pieceCaptured = False
                        moveMade = True
                        animate = True
                        squareSelected = ()
                        playerClicks = []
                    else:
                        # 오프닝 북에서 수를 못 찾음 - 이후로는 일반 AI만 사용
                        openingBookActive = False
                        # 마지막 오프닝 이름 유지
                        print(f"오프닝 북 종료 (최종: {_current_opening_name}) - 이제 일반 AI 계산 사용")
                
                # 오프닝 북을 사용하지 않았을 때만 AI 계산 시작
                if not opening_book_used:
                    AIThinking = True
                    AIThinkingStartTime = time.perf_counter()
                    AIThinkingColor = 'w' if gs.whiteToMove else 'b'
                    # AI 시작 시 진행 상황 캐시 초기화
                    _progress_cache = {"on": False, "last_done": 0, "last_total": 0, "last_pct": 0, "color": AIThinkingColor, "last_nodes": 0}
                    if USE_CPP_ENGINE:
                        returnQueue = queue.Queue()
                        try:
                            gs_for_ai = chess_cpp.cloneGameState(gs)
                        except Exception:
                            gs_for_ai = gs
                        vm_copy = list(validMoves)
                        # 시간 제한 전달
                        ai_time = aiTimeLimit if aiTimeLimitEnabled else 0.0
                        moveFinderProcess = threading.Thread(target=findBestMove, args=(gs_for_ai, vm_copy, returnQueue, ai_time), daemon=True)
                        moveFinderProcess.start()
                    else:
                        returnQueue = Queue()
                        moveFinderProcess = Process(target=findBestMove, args=(gs, validMoves, returnQueue))
                        moveFinderProcess.start()
            # AI 계산이 완료되었는지 확인 (Iterative Deepening이 시간 관리)
            if moveFinderProcess and not moveFinderProcess.is_alive():
                if AIThinkingStartTime is not None:
                    if (time.perf_counter() - AIThinkingStartTime) < MIN_AI_THINKING_DISPLAY:
                        pass
                    else:
                        try:
                            AIMove = returnQueue.get(timeout=0.1)
                        except:
                            AIMove = None
                        
                        if AIMove is None:
                            AIMove = findRandomMoves(validMoves)
                        
                        # AIMove가 여전히 None이면 (게임 종료 상태)
                        if AIMove is None:
                            AIThinking = False
                            AIIndicatorUntil = time.perf_counter() + 0.3
                        else:
                            try:
                                pre_move_board = fastBoardCopy(gs.board)
                                if gs.board[AIMove.endRow][AIMove.endCol] != '--':
                                    pieceCaptured = True
                                
                                # Make move and check for check/checkmate
                                gs.makeMove(AIMove)
                                is_check = gs.inCheck
                                is_checkmate = gs.checkmate
                                
                                # Generate PGN notation with check symbols
                                gs.undoMove()
                                pgn_notation = move_to_pgn(gs, AIMove, is_check, is_checkmate)
                                gs.makeMove(AIMove)
                                
                                pgn_move_log.append((AIMove, pgn_notation))
                                
                                has_promotion = (AIMove.promotion != "" if USE_CPP_ENGINE else AIMove.promotion is not None)
                                if has_promotion:
                                    if promote_sound: promote_sound.play()
                                    pieceCaptured = False
                                if (pieceCaptured or AIMove.isEnpassantMove):
                                    if capture_sound: capture_sound.play()
                                elif not has_promotion:
                                    if move_sound: move_sound.play()
                                pieceCaptured = False
                                AIThinking = False
                                AIIndicatorUntil = time.perf_counter() + 0.3
                                moveMade = True
                                animate = True
                                squareSelected = ()
                                playerClicks = []
                            except Exception as e:
                                print(f"AI 무브 실행 오류: {e}")
                                AIThinking = False
                                AIIndicatorUntil = time.perf_counter() + 0.3
        if moveMade:
            if animate:
                if pre_move_board is None:
                    pre_move_board = fastBoardCopy(gs.board)
                animateMove(gs.moveLog[-1], screen, pre_move_board, clock)
            validMoves = gs.getValidMoves()
            
            # 오프닝 이름 업데이트 (모든 수 이후)
            if is_in_opening_phase(gs.moveLog, max_moves=20):
                try:
                    new_opening_name = get_current_opening_name(gs.moveLog)
                    if new_opening_name:
                        _current_opening_name = new_opening_name
                except Exception:
                    pass
            
            moveMade = False
            animate = False
            moveUndone = False
            pre_move_board = None
        if not AIThinking and AIThinkingStartTime is not None and time.perf_counter() >= AIIndicatorUntil:
            AIThinkingStartTime = None
            AIThinkingColor = None
        indicatorActive = AIThinking or (AIThinkingStartTime is not None and time.perf_counter() < AIIndicatorUntil)
        currentTimeLimit = aiTimeLimit if (aiTimeLimitEnabled and AIThinking) else None
        drawGameState(screen, gs, validMoves, squareSelected, moveLogFont, indicatorActive, AIThinkingStartTime, AIThinkingColor, showEvalBar, currentTimeLimit)
        if gs.stalemate:
            global _last_eval_score, _last_mate_depth
            gameOver = True
            _last_eval_score = 0
            _last_mate_depth = 0
            if gs.isDrawByRepetition():
                text = 'Draw by threefold repetition'
            elif gs.isDrawByFiftyMoves():
                text = 'Draw by fifty-move rule'
            else:
                text = 'Stalemate'
            drawEndGameText(screen, text)
        elif gs.checkmate:
            gameOver = True
            CHECKMATE = 10000000
            if gs.whiteToMove:
                _last_eval_score = -CHECKMATE
            else:
                _last_eval_score = CHECKMATE
            _last_mate_depth = 1
            text = 'Black wins by checkmate' if gs.whiteToMove else 'White wins by checkmate'
            drawEndGameText(screen, text)

        # 최적화: AI 계산 중에는 FPS 낮춤
        if AIThinking:
            clock.tick(30)  # AI 생각 중 30 FPS
        else:
            clock.tick(MAX_FPS)  # 일반 15 FPS
        p.display.flip()

if __name__ == "__main__":
    main()
