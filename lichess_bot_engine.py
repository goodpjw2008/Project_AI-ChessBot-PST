"""
goodpjw chess Engine -> lichess-bot homemade adapter.

Place this file inside the lichess-bot project root (alongside homemade.py),
then in homemade.py add:

    from lichess_bot_engine import GoodpjwEngine

and reference `GoodpjwEngine` from your config.yml engine.name field.

Requirements on the host:
- chess_cpp module importable (the compiled extension built from
  chessAi.cpp + engine.cpp + chess_cpp.cpp via setup.py).
- Set CHESS_ENGINE_DIR env var, or edit ENGINE_DIR below, so the
  chess/ directory containing chess_cpp.* is on sys.path.
"""

from __future__ import annotations

import os
import sys
import logging
from typing import Any

import chess
import chess.engine

ENGINE_DIR = os.environ.get(
    "CHESS_ENGINE_DIR",
    "/Users/yhpark/workspace/chess-ai-v5/chess",
)
if ENGINE_DIR and ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

import chess_cpp  # noqa: E402

chess_cpp.initializePST()

logger = logging.getLogger(__name__)


# --- piece + square conversions -----------------------------------------------

# python-chess uses 0..63 with a1=0, h1=7, a8=56, h8=63.
# Engine board[r][c] uses r=0 at rank 8 (top), r=7 at rank 1 (bottom),
# c=0 at file a, c=7 at file h.

def _square_to_rc(sq: int) -> tuple[int, int]:
    file_ = chess.square_file(sq)            # 0..7, a..h
    rank = chess.square_rank(sq)             # 0..7, 1..8
    return (7 - rank, file_)


def _rc_to_square(r: int, c: int) -> int:
    return chess.square(c, 7 - r)


_PIECE_TO_STR = {
    (chess.PAWN,   chess.WHITE): "wp",
    (chess.KNIGHT, chess.WHITE): "wN",
    (chess.BISHOP, chess.WHITE): "wB",
    (chess.ROOK,   chess.WHITE): "wR",
    (chess.QUEEN,  chess.WHITE): "wQ",
    (chess.KING,   chess.WHITE): "wK",
    (chess.PAWN,   chess.BLACK): "bp",
    (chess.KNIGHT, chess.BLACK): "bN",
    (chess.BISHOP, chess.BLACK): "bB",
    (chess.ROOK,   chess.BLACK): "bR",
    (chess.QUEEN,  chess.BLACK): "bQ",
    (chess.KING,   chess.BLACK): "bK",
}


def board_to_gamestate(board: chess.Board) -> "chess_cpp.GameState":
    """Build a fresh chess_cpp.GameState mirroring `board`."""
    gs = chess_cpp.GameState()

    new_board = [["--"] * 8 for _ in range(8)]
    wk = (7, 4)
    bk = (0, 4)
    for sq, piece in board.piece_map().items():
        r, c = _square_to_rc(sq)
        s = _PIECE_TO_STR[(piece.piece_type, piece.color)]
        new_board[r][c] = s
        if s == "wK":
            wk = (r, c)
        elif s == "bK":
            bk = (r, c)
    gs.board = new_board

    gs.whiteToMove = board.turn == chess.WHITE
    gs.whiteKingLocation = wk
    gs.blackKingLocation = bk

    gs.whiteCastleKingside  = bool(board.castling_rights & chess.BB_H1)
    gs.whiteCastleQueenside = bool(board.castling_rights & chess.BB_A1)
    gs.blackCastleKingside  = bool(board.castling_rights & chess.BB_H8)
    gs.blackCastleQueenside = bool(board.castling_rights & chess.BB_A8)

    if board.ep_square is not None:
        r, c = _square_to_rc(board.ep_square)
        gs.enpassantPossible = (r, c)
    else:
        gs.enpassantPossible = (0, 0)

    gs.halfmoveClock = board.halfmove_clock
    gs.checkmate = board.is_checkmate()
    gs.stalemate = board.is_stalemate()
    gs.inCheck = board.is_check()
    return gs


def engine_move_to_uci(mv: "chess_cpp.Move") -> str:
    from_sq = _rc_to_square(mv.startRow, mv.startCol)
    to_sq = _rc_to_square(mv.endRow, mv.endCol)
    uci = chess.square_name(from_sq) + chess.square_name(to_sq)
    if mv.promotion:
        uci += mv.promotion[0].lower()
    return uci


# --- time management ----------------------------------------------------------

def _pick_time_seconds(board: chess.Board, limit: chess.engine.Limit) -> float:
    if limit.time is not None:
        return max(0.05, float(limit.time))

    our_clock = limit.white_clock if board.turn == chess.WHITE else limit.black_clock
    our_inc   = limit.white_inc   if board.turn == chess.WHITE else limit.black_inc

    if our_clock is None:
        # No time info -> rely on default fixed-depth search.
        return 0.0

    inc = float(our_inc or 0.0)
    moves_left = max(20, 40 - board.fullmove_number)
    budget = float(our_clock) / moves_left + 0.8 * inc
    # Keep some safety margin.
    budget = max(0.05, min(budget, max(1.0, float(our_clock) - 1.0)))
    return budget


# --- lichess-bot adapter ------------------------------------------------------

try:
    from lib.engine_wrapper import MinimalEngine
except ImportError:  # pragma: no cover - allow import standalone for testing
    MinimalEngine = object  # type: ignore[misc,assignment]


class GoodpjwEngine(MinimalEngine):
    """lichess-bot homemade engine wrapping chess_cpp.findBestMoveIterative."""

    def search(
        self,
        board: chess.Board,
        time_limit: chess.engine.Limit,
        ponder: bool,
        draw_offered: bool,
        root_moves: Any,
    ) -> chess.engine.PlayResult:
        gs = board_to_gamestate(board)
        valid = gs.getValidMoves()
        if not valid:
            # Should not happen — lichess-bot would have ended the game.
            return chess.engine.PlayResult(None, None, resigned=True)

        seconds = _pick_time_seconds(board, time_limit)
        try:
            mv = chess_cpp.findBestMoveIterative(gs, valid, seconds)
        except Exception:
            logger.exception("engine search failed; falling back to first legal move")
            mv = valid[0]

        uci = engine_move_to_uci(mv)
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            logger.error("engine returned non-UCI move %r; resigning", uci)
            return chess.engine.PlayResult(None, None, resigned=True)

        if move not in board.legal_moves:
            logger.error(
                "engine returned illegal move %s for FEN %s; falling back",
                uci, board.fen(),
            )
            move = next(iter(board.legal_moves))

        return chess.engine.PlayResult(move, None)


# --- standalone smoke test ----------------------------------------------------

if __name__ == "__main__":
    b = chess.Board()
    b.push_san("e4")
    b.push_san("e5")
    gs = board_to_gamestate(b)
    valid = gs.getValidMoves()
    print(f"position: {b.fen()}")
    print(f"engine valid move count: {len(valid)} (python-chess: {b.legal_moves.count()})")
    mv = chess_cpp.findBestMoveIterative(gs, valid, 1.0)
    print(f"engine picks: {engine_move_to_uci(mv)}")
