#ifdef _MSC_VER
    #pragma optimize("gt", on)
#else
    #pragma GCC optimize("O3")
    #pragma GCC optimize("unroll-loops")
    #pragma GCC target("avx2")
#endif

#include "chessAi.h"
#include <algorithm>
#include <atomic>
#include <chrono>

#ifdef _MSC_VER
#include <xmmintrin.h>  // For _mm_prefetch
#endif

std::atomic<long long> cnt{0};
int indepth = DEPTH;
int SET_WHITE_AS_BOT = -1;
Move* nextMovePtr = nullptr;
std::atomic<int> rootTotal{0};
std::atomic<int> rootDone{0};
std::atomic<int> currentBestScore{0};
std::atomic<int> mateDepth{0};

// Thread-local last move for countermove heuristic
thread_local Move threadLastMove;

std::array<KillerMoves, MAX_KILLER_DEPTH> killerMoves;

// History Heuristic
std::array<std::array<std::array<std::array<int, 8>, 8>, 8>, 8> historyTable{};

// Countermove Heuristic
std::array<std::array<std::array<std::array<CountermoveEntry, 8>, 8>, 8>, 8> countermoveTable{};

// Simple position cache (lightweight)
std::array<SimpleCache, CACHE_SIZE> positionCache{};

void clearKillerMoves() {
    for (auto& km : killerMoves) {
        km.hasMove1 = false;
        km.hasMove2 = false;
    }
}

void clearHistoryTable() {
    for (auto& a : historyTable) {
        for (auto& b : a) {
            for (auto& c : b) {
                c.fill(0);
            }
        }
    }
}

void clearCountermoveTable() {
    for (auto& a : countermoveTable) {
        for (auto& b : a) {
            for (auto& c : b) {
                for (auto& d : c) {
                    d.valid = false;
                }
            }
        }
    }
}


std::map<char, int> pieceScore = {
    {'K', 20000}, {'Q', 900}, {'R', 500}, 
    {'B', 330}, {'N', 320}, {'p', 100}
};

std::array<std::array<int, 8>, 8> whitePstP;
std::array<std::array<int, 8>, 8> whitePstN;
std::array<std::array<int, 8>, 8> whitePstB;
std::array<std::array<int, 8>, 8> whitePstR;
std::array<std::array<int, 8>, 8> whitePstQ;
std::array<std::array<int, 8>, 8> whitePstK;
std::array<std::array<int, 8>, 8> whitePstKEndgame;

std::array<std::array<int, 8>, 8> blackPstP;
std::array<std::array<int, 8>, 8> blackPstN;
std::array<std::array<int, 8>, 8> blackPstB;
std::array<std::array<int, 8>, 8> blackPstR;
std::array<std::array<int, 8>, 8> blackPstQ;
std::array<std::array<int, 8>, 8> blackPstK;
std::array<std::array<int, 8>, 8> blackPstKEndgame;

void initializePST() {
    int pRaw[64] = {
          0,   0,   0,   0,   0,   0,   0,   0,
         98, 134,  61,  95,  68, 126,  34, -11,
         -6,   7,  26,  31,  65,  56,  25, -20,
        -14,  13,   6,  21,  23,  12,  17, -23,
        -27,  -2,  -5,  12,  17,   6,  10, -25,
        -26,  -4,  -4, -10,   3,   3,  33, -12,
        -35,  -1, -20, -23, -15,  24,  38, -22,
          0,   0,   0,   0,   0,   0,   0,   0
    };
    int nRaw[64] = {
        -167, -89, -34, -49,  61, -97, -15, -107,
         -73, -41,  72,  36,  23,  62,   7,  -17,
         -47,  60,  37,  65,  84, 129,  73,   44,
          -9,  17,  19,  53,  37,  69,  18,   22,
         -13,   4,  16,  13,  28,  19,  21,   -8,
         -23,  -9,  12,  10,  19,  17,  25,  -16,
         -29, -53, -12,  -3,  -1,  18, -14,  -19,
        -105, -21, -58, -33, -17, -28, -19,  -23
    };
    int bRaw[64] = {
        -29,   4, -82, -37, -25, -42,   7,  -8,
        -26,  16, -18, -13,  30,  59,  18, -47,
        -16,  37,  43,  40,  35,  50,  37,  -2,
         -4,   5,  19,  50,  37,  37,   7,  -2,
         -6,  13,  13,  26,  34,  12,  10,   4,
          0,  15,  15,  15,  14,  27,  18,  10,
          4,  15,  16,   0,   7,  21,  33,   1,
        -33,  -3, -14, -21, -13, -12, -39, -21
    };
    int rRaw[64] = {
         32,  42,  32,  51,  63,   9,  31,  43,
         27,  32,  58,  62,  80,  67,  26,  44,
         -5,  19,  26,  36,  17,  45,  61,  16,
        -24, -11,   7,  26,  24,  35,  -8, -20,
        -36, -26, -12,  -1,   9,  -7,   6, -23,
        -45, -25, -16, -17,   3,   0,  -5, -33,
        -44, -16, -20,  -9,  -1,  11,  -6, -71,
        -19, -13,   1,  17,  16,   7, -37, -26
    };
    int qRaw[64] = {
        -28,   0,  29,  12,  59,  44,  43,  45,
        -24, -39,  -5,   1, -16,  57,  28,  54,
        -13, -17,   7,   8,  29,  56,  47,  57,
        -27, -27, -16, -16,  -1,  17,  -2,   1,
         -9, -26,  -9, -10,  -2,  -4,   3,  -3,
        -14,   2, -11,  -2,  -5,   2,  14,   5,
        -35,  -8,  11,   2,   8,  15,  -3,   1,
         -1, -18,  -9,  10, -15, -25, -31, -50
    };
    // Middlegame king table (safety-focused)
    int kRaw[64] = {
        -65,  23,  16, -15, -56, -34,   2,  13,
         29,  -1, -20,  -7,  -8,  -4, -38, -29,
         -9,  24,   2, -16, -20,   6,  22, -22,
        -17, -20, -12, -27, -30, -25, -14, -36,
        -49,  -1, -27, -39, -46, -44, -33, -51,
        -14, -14, -22, -46, -44, -30, -15, -27,
          1,   7,  -8, -64, -43, -16,   9,   8,
        -15,  36,  12, -54,   8, -28,  24,  14
    };
    
    // Endgame king table (conservative centralization)
    int kEndgameRaw[64] = {
        -30, -20, -10, -10, -10, -10, -20, -30,
        -20, -10,   0,   5,   5,   0, -10, -20,
        -10,   0,  10,  15,  15,  10,   0, -10,
        -10,   5,  15,  20,  20,  15,   5, -10,
        -10,   5,  15,  20,  20,  15,   5, -10,
        -10,   0,  10,  15,  15,  10,   0, -10,
        -20, -10,   0,   5,   5,   0, -10, -20,
        -30, -20, -10, -10, -10, -10, -20, -30
    };
    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 8; j++) {
            whitePstP[i][j] = pRaw[i * 8 + j];
            whitePstN[i][j] = nRaw[i * 8 + j];
            whitePstB[i][j] = bRaw[i * 8 + j];
            whitePstR[i][j] = rRaw[i * 8 + j];
            whitePstQ[i][j] = qRaw[i * 8 + j];
            whitePstK[i][j] = kRaw[i * 8 + j];
            whitePstKEndgame[i][j] = kEndgameRaw[i * 8 + j];
        }
    }
    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 8; j++) {
            blackPstP[i][j] = whitePstP[7 - i][j];
            blackPstN[i][j] = whitePstN[7 - i][j];
            blackPstB[i][j] = whitePstB[7 - i][j];
            blackPstR[i][j] = whitePstR[7 - i][j];
            blackPstQ[i][j] = whitePstQ[7 - i][j];
            blackPstK[i][j] = whitePstK[7 - i][j];
            blackPstKEndgame[i][j] = whitePstKEndgame[7 - i][j];
        }
    }
}

// Game phase detection (0 = endgame, 256 = middlegame)
inline int getGamePhase(const GameState& gs) noexcept {
    int phase = 0;
    const auto& board = gs.board;
    
    // Optimized: single character comparisons
    for (int row = 0; row < 8; ++row) {
        const auto& boardRow = board[row];
        for (int col = 0; col < 8; ++col) {
            const char type = boardRow[col][1];
            if (type == 'N') [[unlikely]] phase += 1;
            else if (type == 'B') [[unlikely]] phase += 1;
            else if (type == 'R') [[unlikely]] phase += 2;
            else if (type == 'Q') [[unlikely]] phase += 4;
        }
    }
    
    return (phase * 256 / 24) & 255;  // Clamp to 0-255 with bitwise AND
}

inline bool movesEqual(const Move& a, const Move& b) noexcept {
    // Fast path: compare positions first (most likely to differ)
    if (a.startRow != b.startRow || a.startCol != b.startCol) [[likely]] {
        return false;
    }
    if (a.endRow != b.endRow || a.endCol != b.endCol) [[likely]] {
        return false;
    }
    // Slow path: compare promotion (rarely different)
    return a.promotion == b.promotion;
}

inline int getMoveScore(const Move& move, const int depth, const Move* lastMove = nullptr) noexcept {
    // Fast path: promotions (highest priority)
    if (!move.promotion.empty()) [[unlikely]] {
        const char promo = move.promotion[0];
        return 9000 + ((promo == 'Q') ? 900 : ((promo == 'R') ? 500 : 300));
    }
    
    // Captures: prioritize good captures, demote bad captures
    if (move.isCapture) [[likely]] {
        const int mvvLva = pieceScore[move.pieceCaptured[1]] * 10 - pieceScore[move.pieceMoved[1]];
        // Good captures (winning or equal): higher than killers
        if (mvvLva >= 0) [[likely]] {
            return 10000 + mvvLva;  // Range: 10000~18900
        }
        // Bad captures (losing): lower than killers but higher than history
        return 100 + mvvLva;  // Range: -700~100
    }
    
    // Killer moves
    if (depth < MAX_KILLER_DEPTH) [[likely]] {
        const auto& km = killerMoves[depth];
        if (km.hasMove1 && movesEqual(move, km.move1)) [[unlikely]] {
            return 8000;
        }
        if (km.hasMove2 && movesEqual(move, km.move2)) [[unlikely]] {
            return 7000;
        }
    }
    
    // Countermove: best response to opponent's last move
    if (lastMove != nullptr && lastMove->startRow >= 0) [[likely]] {
        const auto& cm = countermoveTable[lastMove->startRow][lastMove->startCol][lastMove->endRow][lastMove->endCol];
        if (cm.valid && movesEqual(move, cm.move)) [[unlikely]] {
            return 6500;  // Lower than killer but higher than history
        }
    }
    
    // History score (base)
    int score = historyTable[move.startRow][move.startCol][move.endRow][move.endCol];
    
    // Castle bonus
    if (move.castle) [[unlikely]] {
        return score + 100;
    }
    
    // Center control (bitwise trick for d4,d5,e4,e5)
    const int endRow = move.endRow;
    const int endCol = move.endCol;
    if (((endRow - 3) & ~1) == 0 && ((endCol - 3) & ~1) == 0) [[likely]] {
        score += 50;
    }
    
    // Development bonus
    const char pieceType = move.pieceMoved[1];
    if ((pieceType != 'p') & (pieceType != 'K')) [[likely]] {
        const int startRow = move.startRow;
        if ((startRow == 0) | (startRow == 7)) [[unlikely]] {
            score += 30;
        }
    }
    
    return score;
}

inline void orderMoves(std::vector<Move>& moves, const int depth, const Move* lastMove = nullptr) {
    const size_t size = moves.size();
    if (size <= 1) return;
    
    std::sort(moves.begin(), moves.end(), [depth, lastMove](const Move& a, const Move& b) noexcept {
        return getMoveScore(a, depth, lastMove) > getMoveScore(b, depth, lastMove);
    });
}

inline int scoreBoard(const GameState& gs, const int depth) noexcept {
    if (gs.checkmate) [[unlikely]] {
        return gs.whiteToMove ? (-CHECKMATE + depth) : (CHECKMATE - depth);
    }
    if (gs.stalemate) [[unlikely]] {
        return STALEMATE;
    }
    
    // Check for draw by repetition or fifty-move rule
    // Use contempt factor: AI prefers to play on rather than draw
    if (gs.isDrawByRepetition() || gs.isDrawByFiftyMoves()) [[unlikely]] {
        // Contempt: AI slightly dislikes draws (will avoid unless losing)
        // This prevents AI from seeking draws when winning
        constexpr int CONTEMPT = -30;  // Negative = avoid draws
        return STALEMATE + CONTEMPT;
    }
    
    const int phase = getGamePhase(gs);
    const int invPhase = 256 - phase;
    
    int score = 0;
    const auto& board = gs.board;
    
    // Single-pass evaluation with optimized branching
    for (int row = 0; row < 8; ++row) {
        const auto& boardRow = board[row];
        
        // Prefetch next row for better cache performance
        #ifdef _MSC_VER
        if (row < 7) [[likely]] {
            _mm_prefetch((const char*)&board[row + 1], _MM_HINT_T0);
        }
        #else
        if (row < 7) [[likely]] {
            __builtin_prefetch(&board[row + 1], 0, 3);
        }
        #endif
        
        for (int col = 0; col < 8; ++col) {
            const std::string& piece = boardRow[col];
            const char color = piece[0];
            if (color == '-') [[likely]] continue;
            
            const char type = piece[1];
            const int baseValue = pieceScore[type];
            int pstValue = 0;
            
            if (color == 'w') {
                switch (type) {
                    case 'p': pstValue = whitePstP[row][col]; break;
                    case 'N': pstValue = whitePstN[row][col]; break;
                    case 'B': pstValue = whitePstB[row][col]; break;
                    case 'R': pstValue = whitePstR[row][col]; break;
                    case 'Q': pstValue = whitePstQ[row][col]; break;
                    case 'K':
                        pstValue = (whitePstK[row][col] * phase + whitePstKEndgame[row][col] * invPhase) >> 8;
                        break;
                }
                score += baseValue + pstValue;
            } else {
                switch (type) {
                    case 'p': 
                        pstValue = blackPstP[row][col];
                        if (phase < 64) pstValue += row * 2;
                        break;
                    case 'N': pstValue = blackPstN[row][col]; break;
                    case 'B': pstValue = blackPstB[row][col]; break;
                    case 'R': pstValue = blackPstR[row][col]; break;
                    case 'Q': pstValue = blackPstQ[row][col]; break;
                    case 'K':
                        pstValue = (blackPstK[row][col] * phase + blackPstKEndgame[row][col] * invPhase) >> 8;
                        break;
                }
                score -= baseValue + pstValue;
            }
        }
    }
    
    // White pawn endgame bonus (merged into single pass)
    if (phase < 64) [[unlikely]] {
        for (int row = 0; row < 8; ++row) {
            for (int col = 0; col < 8; ++col) {
                if (board[row][col][1] == 'p' && board[row][col][0] == 'w') [[unlikely]] {
                    score += (7 - row) * 2;
                }
            }
        }
    }
    
    return score;
}

// Quiescence Search: continue search while captures exist (prevent Horizon Effect)
inline int quiescenceSearch(GameState& gs, int alpha, int beta, const int turnMultiplier) {
    cnt.fetch_add(1, std::memory_order_relaxed);
    
    // Stand-pat: evaluate current position
    const int standPat = turnMultiplier * scoreBoard(gs, 0);
    
    // Beta cutoff (check first)
    if (standPat >= beta) [[likely]] {
        return beta;
    }
    
    // Delta pruning: stop if even capturing queen can't exceed alpha
    constexpr int BIG_DELTA = 900;
    if (standPat + BIG_DELTA < alpha) [[unlikely]] {
        return alpha;
    }
    
    // Update alpha
    if (standPat > alpha) {
        alpha = standPat;
    }
    
    // Generate capture moves only
    std::vector<Move> allMoves = gs.getValidMoves();
    std::vector<Move> captureMoves;
    captureMoves.reserve(12);
    
    const size_t allMovesSize = allMoves.size();
    for (size_t i = 0; i < allMovesSize; ++i) {
        if (allMoves[i].isCapture || allMoves[i].isPawnPromotion) [[unlikely]] {
            captureMoves.push_back(allMoves[i]);
        }
    }
    
    // Sort capture moves by MVV-LVA (optimization: check promotions first)
    const size_t captureSize = captureMoves.size();
    if (captureSize > 1) {
        std::sort(captureMoves.begin(), captureMoves.end(), [](const Move& a, const Move& b) noexcept {
            // Promotions first
            const bool aPromo = a.isPawnPromotion;
            const bool bPromo = b.isPawnPromotion;
            if (aPromo != bPromo) return aPromo;
            
            // MVV-LVA: capture high-value pieces with low-value pieces
            const int scoreA = pieceScore[a.pieceCaptured[1]] * 10 - pieceScore[a.pieceMoved[1]];
            const int scoreB = pieceScore[b.pieceCaptured[1]] * 10 - pieceScore[b.pieceMoved[1]];
            return scoreA > scoreB;
        });
    }
    
    // Search capture moves (optimization: size caching)
    for (size_t i = 0; i < captureSize; ++i) {
        gs.makeMove(captureMoves[i]);
        const int score = -quiescenceSearch(gs, -beta, -alpha, -turnMultiplier);
        gs.undoMove();
        
        if (score >= beta) [[unlikely]] {
            return beta;
        }
        if (score > alpha) {
            alpha = score;
        }
    }
    
    return alpha;
}

inline int findMoveNegaMaxAlphaBeta(GameState& gs, std::vector<Move>& validMoves, 
                             const int depth, int alpha, int beta, const int turnMultiplier, 
                             const bool allowNullMove = true, const Move* lastMove = nullptr) {
    cnt.fetch_add(1, std::memory_order_relaxed);
    const size_t numMoves = validMoves.size();
    
    if (numMoves == 0) [[unlikely]] {
        if (gs.checkmate) [[likely]] {
            return -CHECKMATE + (indepth - depth);
        }
        if (gs.stalemate) [[unlikely]] {
            return STALEMATE;
        }
        return turnMultiplier * scoreBoard(gs, depth);
    }
    if (depth == 0) [[unlikely]] {
        return quiescenceSearch(gs, alpha, beta, turnMultiplier);
    }
    
    // Null Move Pruning: Balanced approach
    if (allowNullMove && depth >= 3 && !gs.inCheck && numMoves > 6) [[likely]] {
        const int phase = getGamePhase(gs);
        if (phase > 96) [[likely]] {
            const int R = (depth >= 6) ? 3 : 2;
            
            gs.whiteToMove = !gs.whiteToMove;
            std::vector<Move> nullMoves;
            nullMoves.reserve(40);
            nullMoves = gs.getValidMoves();
            const int nullScore = -findMoveNegaMaxAlphaBeta(gs, nullMoves, depth - 1 - R, -beta, -beta + 1, -turnMultiplier, false);
            gs.whiteToMove = !gs.whiteToMove;
            
            if (nullScore >= beta) [[unlikely]] {
                return beta;
            }
        }
    }
    
    if (depth > 1) [[likely]] {
        orderMoves(validMoves, depth, lastMove);
    }
    
    int maxScore = -CHECKMATE;
    const bool isRootDepth = (depth == indepth);
    
    // Pre-compute static eval once for both RFP and Futility Pruning
    int staticEval = 0;
    bool staticEvalComputed = false;
    
    // Reverse Futility Pruning: Early cutoff if position is too good
    if (!isRootDepth && depth <= 6 && !gs.inCheck && abs(beta) < 9000) [[likely]] {
        staticEval = turnMultiplier * scoreBoard(gs, depth);
        staticEvalComputed = true;
        const int rfpMargin = 120 * depth;
        if (staticEval - rfpMargin >= beta) [[unlikely]] {
            return staticEval - rfpMargin;
        }
    }
    
    // Futility Pruning: Skip quiet moves in shallow nodes with low eval
    bool futilityPruning = false;
    if (depth <= 3 && !gs.inCheck && abs(alpha) < 9000) [[unlikely]] {
        if (!staticEvalComputed) [[likely]] {
            staticEval = turnMultiplier * scoreBoard(gs, depth);
        }
        const int futilityMargin = 150 * depth;
        if (staticEval + futilityMargin <= alpha) [[unlikely]] {
            futilityPruning = true;
        }
    }
    const int negBeta = -beta;
    std::vector<Move> nextMoves;
    nextMoves.reserve(40);  // Average ~35 moves, optimized
    
    for (size_t i = 0; i < numMoves; ++i) {
        Move& move = validMoves[i];
        gs.makeMove(move);
        nextMoves = gs.getValidMoves();
        if (nextMoves.empty() && gs.checkmate) [[unlikely]] {
            gs.undoMove();
            if (isRootDepth) [[unlikely]] {
                rootDone.store(static_cast<int>(i + 1), std::memory_order_relaxed);
                if (nextMovePtr != nullptr) {
                    *nextMovePtr = move;
                }
            }
            return CHECKMATE - (indepth - depth);
        }
        int score;
        // PVS + LMR: first move gets full window, others get null window + late move reduction
        if (i == 0) {
            score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, depth - 1, negBeta, -alpha, -turnMultiplier, true, &move);
        } else {
            // Futility Pruning: Skip quiet moves with low potential
            if (futilityPruning && !move.isCapture && move.promotion.empty() && !nextMoves.empty() && !gs.checkmate) [[unlikely]] {
                gs.undoMove();
                continue;
            }
            
            // Late Move Reduction (LMR): Adaptive reduction
            int reduction = 0;
            if (depth >= 3 && i >= 4 && !move.isCapture && move.promotion.empty() && !gs.inCheck) [[likely]] {
                const int moveScore = getMoveScore(move, depth, lastMove);
                if (moveScore < 1000) [[likely]] {  // Skip killer/history moves
                    // Adaptive reduction based on depth and move index
                    if (depth >= 6 && i >= 10) [[unlikely]] {
                        reduction = 2;
                    } else if (i >= 8 || depth >= 5) [[likely]] {
                        reduction = 1;
                    }
                }
            }
            
            const int newDepth = (depth - 1 - reduction < 0) ? 0 : (depth - 1 - reduction);
            
            score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, newDepth, -alpha - 1, -alpha, -turnMultiplier, true, &move);
            
            if (score > alpha && (reduction > 0 || score < beta)) [[unlikely]] {
                score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, depth - 1, negBeta, -alpha, -turnMultiplier, true, &move);
            }
        }
        gs.undoMove();
        if (score > maxScore) {
            maxScore = score;
            if (isRootDepth) [[unlikely]] {
                if (nextMovePtr != nullptr) {
                    *nextMovePtr = move;
                }
                currentBestScore.store(maxScore, std::memory_order_relaxed);
                if (const int absScore = abs(maxScore); absScore >= CHECKMATE - 100) {
                    const int depthToMate = CHECKMATE - absScore;
                    const int mateInMoves = (depthToMate + 1) >> 1;
                    mateDepth.store(mateInMoves, std::memory_order_relaxed);
                } else {
                    mateDepth.store(0, std::memory_order_relaxed);
                }
            }
        }
        if (maxScore > alpha) [[likely]] {
            alpha = maxScore;
        }
        if (alpha >= beta) [[unlikely]] {
            if (isRootDepth) [[unlikely]] {
                rootDone.store(static_cast<int>(i + 1), std::memory_order_relaxed);
            }
            // Store killer, history, and countermove (for quiet moves only)
            if (!move.isCapture && depth > 0) [[likely]] {
                // Killer moves
                if (depth < MAX_KILLER_DEPTH) {
                    auto& km = killerMoves[depth];
                    if (!km.hasMove1 || !movesEqual(move, km.move1)) {
                        if (km.hasMove1) {
                            km.move2 = km.move1;
                            km.hasMove2 = true;
                        }
                        km.move1 = move;
                        km.hasMove1 = true;
                    }
                }
                // History Heuristic: weighted by depth^2
                historyTable[move.startRow][move.startCol][move.endRow][move.endCol] += (depth * depth);
                
                // Countermove Heuristic: store best response to opponent's move
                if (lastMove != nullptr && lastMove->startRow >= 0) [[likely]] {
                    auto& cm = countermoveTable[lastMove->startRow][lastMove->startCol][lastMove->endRow][lastMove->endCol];
                    cm.move = move;
                    cm.valid = true;
                }
                // Overflow prevention
                if (historyTable[move.startRow][move.startCol][move.endRow][move.endCol] > 100000) {
                    // Scale down history table
                    for (auto& a : historyTable) {
                        for (auto& b : a) {
                            for (auto& c : b) {
                                for (auto& d : c) {
                                    d /= 2;
                                }
                            }
                        }
                    }
                }
            }
            break;
        }
        if (isRootDepth) [[unlikely]] {
            rootDone.store(static_cast<int>(i + 1), std::memory_order_relaxed);
        }
    }
    
    return maxScore;
}

Move findBestMove(GameState& gs, std::vector<Move>& validMoves) {
    return findBestMoveIterative(gs, validMoves, 0.0);
}

Move findBestMoveIterative(GameState& gs, std::vector<Move>& validMoves, double timeLimitSeconds) {
    cnt.store(0, std::memory_order_relaxed);
    currentBestScore.store(0, std::memory_order_relaxed);
    mateDepth.store(0, std::memory_order_relaxed);
    clearKillerMoves();
    clearHistoryTable();
    clearCountermoveTable();
    
    if (validMoves.empty()) {
        return Move();
    }
    
    Move bestMove = validMoves[0];
    Move nextMove = validMoves[0];
    nextMovePtr = &nextMove;
    SET_WHITE_AS_BOT = gs.whiteToMove ? 1 : -1;
    
    // Store previous depth scores for better move ordering
    // Use array indexing for O(1) lookup instead of linear search
    constexpr int MOVE_HASH_SIZE = 8 * 8 * 8 * 8;  // 4096 entries
    std::vector<int> previousDepthScoreMap(MOVE_HASH_SIZE, -100000);
    
    // Quick mate-in-1 check
    for (auto& m : validMoves) {
        gs.makeMove(m);
        std::vector<Move> replies = gs.getValidMoves();
        bool isMate = replies.empty() && gs.checkmate;
        gs.undoMove();
        if (isMate) {
            return m;
        }
    }
    
    // Time tracking
    auto startTime = std::chrono::high_resolution_clock::now();
    bool hasTimeLimit = (timeLimitSeconds > 0.0);
    
    // Iterative Deepening: from depth 1 to DEPTH
    int maxDepth = DEPTH;
    int completedDepth = 0;
    
    for (int currentDepth = 1; currentDepth <= maxDepth; ++currentDepth) {
        indepth = currentDepth;
        
        // Reset progress at start of each depth
        rootTotal.store(static_cast<int>(validMoves.size()), std::memory_order_relaxed);
        rootDone.store(0, std::memory_order_relaxed);
        
        // Order moves using previous depth scores (O(1) lookup)
        if (currentDepth > 1) [[likely]] {
            // Sort by previous depth scores with fast array lookup
            std::sort(validMoves.begin(), validMoves.end(), 
                [&previousDepthScoreMap](const Move& a, const Move& b) noexcept {
                    // Fast O(1) hash-based lookup
                    const int hashA = (a.startRow << 9) | (a.startCol << 6) | (a.endRow << 3) | a.endCol;
                    const int hashB = (b.startRow << 9) | (b.startCol << 6) | (b.endRow << 3) | b.endCol;
                    
                    const int scoreA = previousDepthScoreMap[hashA];
                    const int scoreB = previousDepthScoreMap[hashB];
                    
                    return scoreA > scoreB;
                });
        } else {
            // First depth: use standard move ordering
            orderMoves(validMoves, currentDepth);
        }
        
        // Search all moves and store scores
        int searchScore = 0;
        
        // Reset score map for next depth (optimized)
        if (currentDepth > 1) [[likely]] {
            // Only reset entries that were actually used
            for (size_t i = 0; i < validMoves.size(); ++i) {
                const Move& move = validMoves[i];
                const int hash = (move.startRow << 9) | (move.startCol << 6) | (move.endRow << 3) | move.endCol;
                previousDepthScoreMap[hash] = -100000;
            }
        }
        
        // Aspiration Windows
        int aspirationWindow = 50;
        int searchAlpha = -aspirationWindow;
        int searchBeta = aspirationWindow;
        
        // First depth uses full window
        if (currentDepth == 1) {
            searchAlpha = -CHECKMATE;
            searchBeta = CHECKMATE;
        }
        
        for (int attempt = 0; attempt < 3; ++attempt) {
            searchScore = findMoveNegaMaxAlphaBeta(gs, validMoves, currentDepth, searchAlpha, searchBeta, SET_WHITE_AS_BOT, true);
            
            if (searchScore <= searchAlpha) {
                searchAlpha = -CHECKMATE;
                aspirationWindow *= 2;
            } else if (searchScore >= searchBeta) {
                searchBeta = CHECKMATE;
                aspirationWindow *= 2;
            } else {
                break;
            }
        }
        
        // Store scores for each move using fast hash-based indexing
        for (size_t i = 0; i < validMoves.size(); ++i) {
            const Move& move = validMoves[i];
            const int hash = (move.startRow << 9) | (move.startCol << 6) | (move.endRow << 3) | move.endCol;
            
            // Estimate score: best move gets actual score, others get decreasing estimates
            if (i == 0) [[likely]] {
                previousDepthScoreMap[hash] = searchScore;
            } else {
                // Decreasing scores for moves further from the best
                previousDepthScoreMap[hash] = searchScore - (static_cast<int>(i) * 50);
            }
        }
        
        // Depth completed - update best move
        bestMove = nextMove;
        completedDepth = currentDepth;
        
        // Check time limit
        if (hasTimeLimit) {
            auto currentTime = std::chrono::high_resolution_clock::now();
            double elapsed = std::chrono::duration<double>(currentTime - startTime).count();
            
            // Stop if remaining time is less than estimated time for next depth
            // Empirically, next depth takes about 3x longer
            double estimatedNextDepthTime = elapsed * 3.0;
            double remaining = timeLimitSeconds - elapsed;
            
            if (remaining < estimatedNextDepthTime || elapsed >= timeLimitSeconds * 0.95) {
                break;
            }
        }
        
        // Early exit if mate found
        if (abs(searchScore) >= CHECKMATE - 100) {
            break;
        }
    }
    
    indepth = completedDepth;  // Mark completed depth
    return bestMove;
}
