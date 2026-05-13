#ifdef _MSC_VER
    #pragma optimize("gt", on)
#else
    #pragma GCC optimize("O3")
    #pragma GCC optimize("unroll-loops")
    #pragma GCC target("avx2")
#endif

#include "engine.h"
#include <algorithm>
#include <map>

static std::map<char, int> ranksToRows = {
    {'1', 7}, {'2', 6}, {'3', 5}, {'4', 4},
    {'5', 3}, {'6', 2}, {'7', 1}, {'8', 0}
};

static std::map<int, char> rowsToRanks = {
    {7, '1'}, {6, '2'}, {5, '3'}, {4, '4'},
    {3, '5'}, {2, '6'}, {1, '7'}, {0, '8'}
};

static std::map<char, int> filesToCols = {
    {'a', 0}, {'b', 1}, {'c', 2}, {'d', 3},
    {'e', 4}, {'f', 5}, {'g', 6}, {'h', 7}
};

static std::map<int, char> colsToFiles = {
    {0, 'a'}, {1, 'b'}, {2, 'c'}, {3, 'd'},
    {4, 'e'}, {5, 'f'}, {6, 'g'}, {7, 'h'}
};

static std::map<char, std::string> pieceNotation = {
    {'p', ""}, {'R', "R"}, {'N', "N"},
    {'B', "B"}, {'Q', "Q"}, {'K', "K"}
};

constexpr inline bool inside(int row, int col) noexcept {
    return (row >= 0) & (row <= 7) & (col >= 0) & (col <= 7);
}

Move::Move(int sRow, int sCol, int eRow, int eCol,
           const std::array<std::array<std::string, 8>, 8>& board,
           bool enpassant, bool isCastle, const std::string& promo)
    : startRow(sRow), startCol(sCol), endRow(eRow), endCol(eCol),
      pieceMoved(board[sRow][sCol]),
      promotion(promo),
      isEnpassantMove(enpassant), castle(isCastle) {
    if (isEnpassantMove) {
        pieceCaptured = board[startRow][endCol];
    } else {
        pieceCaptured = board[endRow][endCol];
    }
    isCapture = (pieceCaptured != "--");
    const int promoVal = promotion.empty() ? 0 : static_cast<int>(promotion[0]);
    moveID = startRow * 1000 + startCol * 100 + endRow * 10 + endCol + promoVal;
    isPawnPromotion = (pieceMoved[1] == 'p') && (!promotion.empty() || endRow == 0 || endRow == 7);
}

bool Move::operator==(const Move& other) const {
    return moveID == other.moveID;
}

std::string Move::getRankFile(int row, int col) const {
    std::string result;
    result += colsToFiles[col];
    result += rowsToRanks[row];
    return result;
}

std::string Move::getChessNotation() const {
    std::string base = getRankFile(startRow, startCol) + getRankFile(endRow, endCol);
    if (!promotion.empty()) {
        base += (char)tolower(promotion[0]);
    }
    return base;
}

std::string Move::toString() const {
    if (castle) {
        return (endCol == 6) ? "O-O" : "O-O-O";
    }
    std::string startSquare = getRankFile(startRow, startCol);
    std::string endSquare = getRankFile(endRow, endCol);
    if (pieceMoved[1] == 'p') {
        std::string base;
        if (isCapture) {
            base = startSquare + "x" + endSquare;
        } else {
            base = startSquare + endSquare;
        }
        if (!promotion.empty()) {
            base += "=" + promotion;
        }
        return base;
    }
    std::string moveString;
    moveString += pieceMoved[1];
    if (isCapture) {
        return moveString + colsToFiles[startCol] + "x" + endSquare;
    }
    return moveString + colsToFiles[startCol] + endSquare;
}

GameState::GameState() {
    board = {{
        {{"bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"}},
        {{"bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"}},
        {{"--", "--", "--", "--", "--", "--", "--", "--"}},
        {{"--", "--", "--", "--", "--", "--", "--", "--"}},
        {{"--", "--", "--", "--", "--", "--", "--", "--"}},
        {{"--", "--", "--", "--", "--", "--", "--", "--"}},
        {{"wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"}},
        {{"wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"}}
    }};
    whiteToMove = true;
    playerWantsToPlayAsBlack = false;
    if (playerWantsToPlayAsBlack) {
        whiteKingLocation = {0, 4};
        blackKingLocation = {7, 4};
    } else {
        whiteKingLocation = {7, 4};
        blackKingLocation = {0, 4};
    }
    checkmate = false;
    stalemate = false;
    inCheck = false;
    enpassantPossible = {-1, -1};
    enpassantPossibleLog.push_back(enpassantPossible);
    whiteCastleKingside = true;
    whiteCastleQueenside = true;
    blackCastleKingside = true;
    blackCastleQueenside = true;
    castleRightsLog.push_back(CastleRights(
        whiteCastleKingside, whiteCastleQueenside, 
        blackCastleKingside, blackCastleQueenside));
    halfmoveClock = 0;
    halfmoveClockLog.push_back(halfmoveClock);
}

void GameState::makeMove(const Move& move) {
    board[move.startRow][move.startCol] = "--";
    if (!move.promotion.empty()) {
        board[move.endRow][move.endCol] = std::string(1, move.pieceMoved[0]) + move.promotion;
    } else {
        board[move.endRow][move.endCol] = move.pieceMoved;
    }
    moveLog.push_back(move);
    whiteToMove = !whiteToMove;
    if (move.pieceMoved == "wK") {
        whiteKingLocation = {move.endRow, move.endCol};
        whiteCastleKingside = false;
        whiteCastleQueenside = false;
    } else if (move.pieceMoved == "bK") {
        blackKingLocation = {move.endRow, move.endCol};
        blackCastleKingside = false;
        blackCastleQueenside = false;
    }
    if (move.isEnpassantMove) {
        board[move.startRow][move.endCol] = "--";
    }
    if (move.pieceMoved[1] == 'p' && abs(move.startRow - move.endRow) == 2) {
        enpassantPossible = {(move.startRow + move.endRow) / 2, move.startCol};
    } else {
        enpassantPossible = {-1, -1};
    }
    updateCastleRights(move);
    castleRightsLog.push_back(CastleRights(
        whiteCastleKingside, whiteCastleQueenside,
        blackCastleKingside, blackCastleQueenside));
    enpassantPossibleLog.push_back(enpassantPossible);
    if (move.castle) {
        if (move.endCol - move.startCol == 2) {
            board[move.endRow][move.endCol - 1] = board[move.endRow][move.endCol + 1];
            board[move.endRow][move.endCol + 1] = "--";
        } else {
            board[move.endRow][move.endCol + 1] = board[move.endRow][move.endCol - 2];
            board[move.endRow][move.endCol - 2] = "--";
        }
    }
    if (move.pieceMoved[1] == 'p' || move.isCapture) {
        halfmoveClock = 0;
        positionHistory.clear();
    } else {
        halfmoveClock++;
    }
    halfmoveClockLog.push_back(halfmoveClock);
    positionHistory.push_back(getPositionKey());
}

void GameState::undoMove() {
    if (moveLog.empty()) return;
    Move move = moveLog.back();
    moveLog.pop_back();
    board[move.startRow][move.startCol] = move.pieceMoved;
    board[move.endRow][move.endCol] = move.pieceCaptured;
    whiteToMove = !whiteToMove;
    if (move.pieceMoved == "wK") {
        whiteKingLocation = {move.startRow, move.startCol};
    } else if (move.pieceMoved == "bK") {
        blackKingLocation = {move.startRow, move.startCol};
    }
    if (move.isEnpassantMove) {
        board[move.endRow][move.endCol] = "--";
        board[move.startRow][move.endCol] = move.pieceCaptured;
    }
    enpassantPossibleLog.pop_back();
    enpassantPossible = enpassantPossibleLog.back();
    castleRightsLog.pop_back();
    CastleRights cr = castleRightsLog.back();
    whiteCastleKingside = cr.wks;
    whiteCastleQueenside = cr.wqs;
    blackCastleKingside = cr.bks;
    blackCastleQueenside = cr.bqs;
    if (move.castle) {
        if (move.endCol - move.startCol == 2) {
            board[move.endRow][move.endCol + 1] = board[move.endRow][move.endCol - 1];
            board[move.endRow][move.endCol - 1] = "--";
        } else {
            board[move.endRow][move.endCol - 2] = board[move.endRow][move.endCol + 1];
            board[move.endRow][move.endCol + 1] = "--";
        }
    }
    if (!positionHistory.empty()) {
        positionHistory.pop_back();
    }
    halfmoveClockLog.pop_back();
    if (!halfmoveClockLog.empty()) {
        halfmoveClock = halfmoveClockLog.back();
    } else {
        halfmoveClock = 0;
    }
    checkmate = false;
    stalemate = false;
}

bool GameState::squareUnderAttack(int row, int col, char allyColor) {
    const char enemyColor = (allyColor == 'w') ? 'b' : 'w';
    static constexpr std::pair<int, int> straightDirs[4] = {{-1, 0}, {0, -1}, {1, 0}, {0, 1}};
    for (const auto& [dr, dc] : straightDirs) {
        for (int i = 1; i < 8; i++) {
            int r = row + dr * i;
            int c = col + dc * i;
            if (!inside(r, c)) break;
            std::string piece = board[r][c];
            if (piece[0] == allyColor) break;
            if (piece[0] == enemyColor) {
                char ptype = piece[1];
                if (ptype == 'R' || ptype == 'Q' || (i == 1 && ptype == 'K')) {
                    return true;
                }
                break;
            }
        }
    }
    static constexpr std::pair<int, int> diagDirs[4] = {{-1, -1}, {-1, 1}, {1, -1}, {1, 1}};
    for (const auto& [dr, dc] : diagDirs) {
        for (int i = 1; i < 8; i++) {
            int r = row + dr * i;
            int c = col + dc * i;
            if (!inside(r, c)) break;
            std::string piece = board[r][c];
            if (piece[0] == allyColor) break;
            if (piece[0] == enemyColor) {
                char ptype = piece[1];
                if (ptype == 'B' || ptype == 'Q' || (i == 1 && ptype == 'K')) {
                    return true;
                }
                if (i == 1 && ptype == 'p') {
                    if ((enemyColor == 'w' && dr == 1) || (enemyColor == 'b' && dr == -1)) {
                        return true;
                    }
                }
                break;
            }
        }
    }
    static constexpr std::pair<int, int> knightMoves[8] = {
        {-2, -1}, {-2, 1}, {-1, -2}, {-1, 2},
        {1, -2}, {1, 2}, {2, -1}, {2, 1}
    };
    for (const auto& [dr, dc] : knightMoves) {
        int r = row + dr;
        int c = col + dc;
        if (inside(r, c)) {
            std::string piece = board[r][c];
            if (piece[0] == enemyColor && piece[1] == 'N') {
                return true;
            }
        }
    }
    return false;
}

std::tuple<bool, std::vector<std::tuple<int, int, int, int>>, 
           std::vector<std::tuple<int, int, int, int>>> GameState::checkForPinsAndChecks() {
    std::vector<std::tuple<int, int, int, int>> pins;
    pins.reserve(8);
    std::vector<std::tuple<int, int, int, int>> checks;
    checks.reserve(2);
    bool inCheck = false;
    const char enemyColor = whiteToMove ? 'b' : 'w';
    const char allyColor = whiteToMove ? 'w' : 'b';
    const auto& kingLoc = whiteToMove ? whiteKingLocation : blackKingLocation;
    const int startRow = kingLoc.first;
    const int startCol = kingLoc.second;
    static constexpr std::tuple<int, int> directions[8] = {
        {-1, 0}, {0, -1}, {1, 0}, {0, 1},
        {-1, -1}, {-1, 1}, {1, -1}, {1, 1}
    };
    for (size_t j = 0; j < 8; j++) {
        const auto& [dr, dc] = directions[j];
        std::tuple<int, int, int, int> possiblePin = {-1, -1, -1, -1};
        bool hasPossiblePin = false;
        for (int i = 1; i < 8; i++) {
            int r = startRow + dr * i;
            int c = startCol + dc * i;
            if (!inside(r, c)) break;
            std::string piece = board[r][c];
            char pieceColor = piece[0];
            if (pieceColor == allyColor && piece[1] != 'K') {
                if (!hasPossiblePin) {
                    possiblePin = {r, c, dr, dc};
                    hasPossiblePin = true;
                } else {
                    break;
                }
            } else if (pieceColor == enemyColor) {
                char ptype = piece[1];
                bool isAttacking = false;
                if (j <= 3) {
                    isAttacking = (ptype == 'R' || ptype == 'Q');
                } else {
                    isAttacking = (ptype == 'B' || ptype == 'Q');
                    if (i == 1 && ptype == 'p') {
                        if ((enemyColor == 'w' && j >= 6) || (enemyColor == 'b' && j <= 5)) {
                            isAttacking = true;
                        }
                    }
                }
                if (i == 1 && ptype == 'K') {
                    isAttacking = true;
                }
                if (isAttacking) {
                    if (!hasPossiblePin) {
                        inCheck = true;
                        checks.push_back({r, c, dr, dc});
                        break;
                    } else {
                        pins.push_back(possiblePin);
                        break;
                    }
                } else {
                    break;
                }
            }
        }
    }
    static constexpr std::pair<int, int> knightMoves[8] = {
        {-2, -1}, {-2, 1}, {-1, -2}, {-1, 2},
        {1, -2}, {1, 2}, {2, -1}, {2, 1}
    };
    for (const auto& [dr, dc] : knightMoves) {
        int r = startRow + dr;
        int c = startCol + dc;
        if (inside(r, c)) {
            std::string piece = board[r][c];
            if (piece[0] == enemyColor && piece[1] == 'N') {
                inCheck = true;
                checks.push_back({r, c, dr, dc});
            }
        }
    }
    return {inCheck, pins, checks};
}

std::vector<Move> GameState::getValidMoves() {
    if (moveLog.empty() && positionHistory.empty()) {
        positionHistory.push_back(getPositionKey());
    }
    std::vector<Move> moves;
    moves.reserve(50);
    auto [inCheckVal, pinsVal, checksVal] = checkForPinsAndChecks();
    inCheck = inCheckVal;
    pins = pinsVal;
    checks = checksVal;
    int kingRow, kingCol;
    if (whiteToMove) {
        kingRow = whiteKingLocation.first;
        kingCol = whiteKingLocation.second;
    } else {
        kingRow = blackKingLocation.first;
        kingCol = blackKingLocation.second;
    }
    if (inCheck) {
        if (checks.size() == 1) {
            moves = getAllPossibleMoves();
            const auto& check = checks[0];
            const int checkRow = std::get<0>(check);
            const int checkCol = std::get<1>(check);
            const std::string& pieceChecking = board[checkRow][checkCol];
            std::vector<std::pair<int, int>> validSquares;
            validSquares.reserve(8);
            if (pieceChecking[1] == 'N') {
                validSquares.push_back({checkRow, checkCol});
            } else {
                for (int i = 1; i < 8; i++) {
                    std::pair<int, int> validSq = {
                        kingRow + std::get<2>(check) * i,
                        kingCol + std::get<3>(check) * i
                    };
                    validSquares.push_back(validSq);
                    if (validSq.first == checkRow && validSq.second == checkCol) {
                        break;
                    }
                }
            }
            for (int i = moves.size() - 1; i >= 0; i--) {
                if (moves[i].pieceMoved[1] != 'K') {
                    std::pair<int, int> endPos = {moves[i].endRow, moves[i].endCol};
                    // 앙파상은 특별 처리: 잡히는 폰 위치도 확인
                    if (moves[i].isEnpassantMove) {
                        std::pair<int, int> capturedPawnPos = {moves[i].startRow, moves[i].endCol};
                        bool endPosValid = std::find(validSquares.begin(), validSquares.end(), endPos) != validSquares.end();
                        bool capturedPosValid = std::find(validSquares.begin(), validSquares.end(), capturedPawnPos) != validSquares.end();
                        if (!endPosValid && !capturedPosValid) {
                            moves.erase(moves.begin() + i);
                        }
                    } else {
                        if (std::find(validSquares.begin(), validSquares.end(), endPos) == validSquares.end()) {
                            moves.erase(moves.begin() + i);
                        }
                    }
                }
            }
        } else {
            getKingMoves(kingRow, kingCol, moves);
        }
    } else {
        moves = getAllPossibleMoves();
    }
    if (moves.empty()) {
        if (inCheck) {
            checkmate = true;
            stalemate = false;
        } else {
            stalemate = true;
            checkmate = false;
        }
    } else {
        checkmate = false;
        stalemate = false;
        // 50수 규칙 또는 3회 반복 체크
        if (isDrawByFiftyMoves() || isDrawByRepetition()) {
            stalemate = true;
        }
    }
    return moves;
}

std::vector<Move> GameState::getAllPossibleMoves() {
    std::vector<Move> moves;
    moves.reserve(40);
    const char targetColor = whiteToMove ? 'w' : 'b';
    for (int row = 0; row < 8; ++row) {
        for (int col = 0; col < 8; ++col) {
            const std::string& square = board[row][col];
            if (square[0] != targetColor) [[likely]] continue;
            switch(square[1]) {
                case 'p': getPawnMoves(row, col, moves); break;
                case 'R': getRookMoves(row, col, moves); break;
                case 'N': getKnightMoves(row, col, moves); break;
                case 'B': getBishopMoves(row, col, moves); break;
                case 'Q': getQueenMoves(row, col, moves); break;
                case 'K': getKingMoves(row, col, moves); break;
            }
        }
    }
    return moves;
}

void GameState::getPawnMoves(int row, int col, std::vector<Move>& moves) {
    bool piecePinned = false;
    std::tuple<int, int, int, int> pinDirection = {0, 0, 0, 0};
    const size_t pinsSize = pins.size();
    for (size_t i = pinsSize; i-- > 0; ) {
        if (std::get<0>(pins[i]) == row && std::get<1>(pins[i]) == col) {
            piecePinned = true;
            pinDirection = pins[i];
            pins.erase(pins.begin() + i);
            break;
        }
    }
    int moveAmount, startRow;
    char enemyColor;
    if (playerWantsToPlayAsBlack) {
        if (whiteToMove) {
            moveAmount = 1;
            startRow = 1;
            enemyColor = 'b';
        } else {
            moveAmount = -1;
            startRow = 6;
            enemyColor = 'w';
        }
    } else {
        if (whiteToMove) {
            moveAmount = -1;
            startRow = 6;
            enemyColor = 'b';
        } else {
            moveAmount = 1;
            startRow = 1;
            enemyColor = 'w';
        }
    }
    int endRow = row + moveAmount;
    if (inside(endRow, col) && board[endRow][col] == "--") {
        if (endRow == 0 || endRow == 7) {
            for (auto promo : {"Q", "R", "B", "N"}) {
                if (!piecePinned || 
                    ((std::get<2>(pinDirection) == moveAmount || std::get<2>(pinDirection) == -moveAmount) && std::get<3>(pinDirection) == 0)) {
                    moves.push_back(Move(row, col, endRow, col, board, false, false, promo));
                }
            }
        } else {
            if (!piecePinned || 
                ((std::get<2>(pinDirection) == moveAmount || std::get<2>(pinDirection) == -moveAmount) && std::get<3>(pinDirection) == 0)) {
                moves.push_back(Move(row, col, endRow, col, board));
            }
            if (row == startRow) {
                int endRow2 = row + 2 * moveAmount;
                if (inside(endRow2, col) && board[endRow2][col] == "--") {
                    if (!piecePinned || 
                        ((std::get<2>(pinDirection) == moveAmount || std::get<2>(pinDirection) == -moveAmount) && std::get<3>(pinDirection) == 0)) {
                        moves.push_back(Move(row, col, endRow2, col, board));
                    }
                }
            }
        }
    }
    for (int dcol : {-1, 1}) {
        int c = col + dcol;
        if (c >= 0 && c <= 7) {
            if (!piecePinned || 
                ((std::get<2>(pinDirection) == moveAmount || std::get<2>(pinDirection) == -moveAmount) && std::get<3>(pinDirection) == dcol)) {
                if (inside(row + moveAmount, c) && board[row + moveAmount][c][0] == enemyColor) {
                    if (row + moveAmount == 0 || row + moveAmount == 7) {
                        for (auto promo : {"Q", "R", "B", "N"}) {
                            moves.push_back(Move(row, col, row + moveAmount, c, board, false, false, promo));
                        }
                    } else {
                        moves.push_back(Move(row, col, row + moveAmount, c, board));
                    }
                }
                if (inside(row + moveAmount, c) && 
                    enpassantPossible.first == row + moveAmount && 
                    enpassantPossible.second == c) {
                    moves.push_back(Move(row, col, row + moveAmount, c, board, true));
                }
            }
        }
    }
}

void GameState::getRookMoves(int row, int col, std::vector<Move>& moves) {
    bool piecePinned = false;
    std::tuple<int, int, int, int> pinDirection = {0, 0, 0, 0};
    const char pieceType = board[row][col][1];
    const size_t pinsSize = pins.size();
    for (size_t i = pinsSize; i-- > 0; ) {
        if (std::get<0>(pins[i]) == row && std::get<1>(pins[i]) == col) {
            piecePinned = true;
            pinDirection = pins[i];
            if (pieceType != 'Q') {
                pins.erase(pins.begin() + i);
            }
            break;
        }
    }
    static constexpr std::pair<int, int> directions[4] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    const char enemyColor = whiteToMove ? 'b' : 'w';
    for (const auto& [dr, dc] : directions) {
        for (int i = 1; i < 8; i++) {
            int endRow = row + dr * i;
            int endCol = col + dc * i;
            if (inside(endRow, endCol)) {
                if (!piecePinned || 
                    (std::get<2>(pinDirection) == dr && std::get<3>(pinDirection) == dc) ||
                    (std::get<2>(pinDirection) == -dr && std::get<3>(pinDirection) == -dc)) {
                    if (board[endRow][endCol] == "--") {
                        moves.push_back(Move(row, col, endRow, endCol, board));
                    } else if (board[endRow][endCol][0] == enemyColor) {
                        moves.push_back(Move(row, col, endRow, endCol, board));
                        break;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }
        }
    }
}

void GameState::getBishopMoves(int row, int col, std::vector<Move>& moves) {
    bool piecePinned = false;
    std::tuple<int, int, int, int> pinDirection = {0, 0, 0, 0};
    const char pieceType = board[row][col][1];
    const size_t pinsSize = pins.size();
    for (size_t i = pinsSize; i-- > 0; ) {
        if (std::get<0>(pins[i]) == row && std::get<1>(pins[i]) == col) {
            piecePinned = true;
            pinDirection = pins[i];
            if (pieceType != 'Q') {
                pins.erase(pins.begin() + i);
            }
            break;
        }
    }
    static constexpr std::pair<int, int> directions[4] = {{1, 1}, {-1, -1}, {-1, 1}, {1, -1}};
    const char enemyColor = whiteToMove ? 'b' : 'w';
    for (const auto& [dr, dc] : directions) {
        for (int i = 1; i < 8; i++) {
            int endRow = row + dr * i;
            int endCol = col + dc * i;
            if (inside(endRow, endCol)) {
                if (!piecePinned || 
                    (std::get<2>(pinDirection) == dr && std::get<3>(pinDirection) == dc) ||
                    (std::get<2>(pinDirection) == -dr && std::get<3>(pinDirection) == -dc)) {
                    if (board[endRow][endCol] == "--") {
                        moves.push_back(Move(row, col, endRow, endCol, board));
                    } else if (board[endRow][endCol][0] == enemyColor) {
                        moves.push_back(Move(row, col, endRow, endCol, board));
                        break;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }
        }
    }
}

void GameState::getKnightMoves(int row, int col, std::vector<Move>& moves) {
    bool piecePinned = false;
    const size_t pinsSize = pins.size();
    for (size_t i = pinsSize; i-- > 0; ) {
        if (std::get<0>(pins[i]) == row && std::get<1>(pins[i]) == col) {
            piecePinned = true;
            pins.erase(pins.begin() + i);
            break;
        }
    }
    static constexpr std::pair<int, int> allPossibleKnightMoves[8] = {
        {-2, -1}, {-2, 1}, {-1, -2}, {-1, 2},
        {1, -2}, {1, 2}, {2, -1}, {2, 1}
    };
    for (const auto& [dr, dc] : allPossibleKnightMoves) {
        int endRow = row + dr;
        int endCol = col + dc;
        if (inside(endRow, endCol)) {
            if (!piecePinned) {
                if (whiteToMove && (board[endRow][endCol] == "--" || board[endRow][endCol][0] == 'b')) {
                    moves.push_back(Move(row, col, endRow, endCol, board));
                } else if (!whiteToMove && (board[endRow][endCol] == "--" || board[endRow][endCol][0] == 'w')) {
                    moves.push_back(Move(row, col, endRow, endCol, board));
                }
            }
        }
    }
}

void GameState::getQueenMoves(int row, int col, std::vector<Move>& moves) {
    getBishopMoves(row, col, moves);
    getRookMoves(row, col, moves);
    const size_t pinsSize = pins.size();
    for (size_t i = pinsSize; i-- > 0; ) {
        if (std::get<0>(pins[i]) == row && std::get<1>(pins[i]) == col) {
            pins.erase(pins.begin() + i);
            break;
        }
    }
}

void GameState::getKingMoves(int row, int col, std::vector<Move>& moves) {
    char allyColor = whiteToMove ? 'w' : 'b';
    for (int i = -1; i <= 1; i++) {
        for (int j = -1; j <= 1; j++) {
            if (i == 0 && j == 0) continue;
            if (inside(row + i, col + j)) {
                std::string endPiece = board[row + i][col + j];
                if (endPiece[0] != allyColor) {
                    if (allyColor == 'w') {
                        whiteKingLocation = {row + i, col + j};
                    } else {
                        blackKingLocation = {row + i, col + j};
                    }
                    auto [inCheckVal, pinsVal, checksVal] = checkForPinsAndChecks();
                    if (!inCheckVal) {
                        moves.push_back(Move(row, col, row + i, col + j, board));
                    }
                    if (allyColor == 'w') {
                        whiteKingLocation = {row, col};
                    } else {
                        blackKingLocation = {row, col};
                    }
                }
            }
        }
    }
    getCastleMoves(row, col, moves, allyColor);
}

void GameState::getCastleMoves(int row, int col, std::vector<Move>& moves, char allyColor) {
    if (squareUnderAttack(row, col, allyColor)) {
        return;
    }
    if ((whiteToMove && whiteCastleKingside) || (!whiteToMove && blackCastleKingside)) {
        getKingsideCastleMoves(row, col, moves, allyColor);
    }
    if ((whiteToMove && whiteCastleQueenside) || (!whiteToMove && blackCastleQueenside)) {
        getQueensideCastleMoves(row, col, moves, allyColor);
    }
}

void GameState::getKingsideCastleMoves(int row, int col, std::vector<Move>& moves, char allyColor) {
    if (board[row][col + 1] == "--" && board[row][col + 2] == "--" &&
        !squareUnderAttack(row, col + 1, allyColor) &&
        !squareUnderAttack(row, col + 2, allyColor)) {
        moves.push_back(Move(row, col, row, col + 2, board, false, true));
    }
}

void GameState::getQueensideCastleMoves(int row, int col, std::vector<Move>& moves, char allyColor) {
    if (board[row][col - 1] == "--" && board[row][col - 2] == "--" &&
        board[row][col - 3] == "--" &&
        !squareUnderAttack(row, col - 1, allyColor) &&
        !squareUnderAttack(row, col - 2, allyColor)) {
        moves.push_back(Move(row, col, row, col - 2, board, false, true));
    }
}

void GameState::updateCastleRights(const Move& move) {
    if (move.pieceMoved == "wK") {
        whiteCastleKingside = false;
        whiteCastleQueenside = false;
    } else if (move.pieceMoved == "bK") {
        blackCastleKingside = false;
        blackCastleQueenside = false;
    }
    if (move.pieceCaptured == "wR" && move.endRow == 7 && move.endCol == 0) {
        whiteCastleQueenside = false;
    }
    if (move.pieceCaptured == "wR" && move.endRow == 7 && move.endCol == 7) {
        whiteCastleKingside = false;
    }
    if (move.pieceCaptured == "bR" && move.endRow == 0 && move.endCol == 0) {
        blackCastleQueenside = false;
    }
    if (move.pieceCaptured == "bR" && move.endRow == 0 && move.endCol == 7) {
        blackCastleKingside = false;
    }
}

std::string GameState::getBoardString() const {
    std::string result;
    for (const auto& row : board) {
        for (const auto& piece : row) {
            result += piece;
        }
    }
    return result;
}

std::string GameState::getPositionKey() const {
    std::string board_str = getBoardString();
    std::string castle_str;
    if (whiteCastleKingside) castle_str += 'K';
    if (whiteCastleQueenside) castle_str += 'Q';
    if (blackCastleKingside) castle_str += 'k';
    if (blackCastleQueenside) castle_str += 'q';
    std::string enpassant_str = (enpassantPossible.first != -1) 
        ? std::to_string(enpassantPossible.first) + "," + std::to_string(enpassantPossible.second)
        : "-";
    char turn_str = whiteToMove ? 'w' : 'b';
    return board_str + "|" + castle_str + "|" + enpassant_str + "|" + turn_str;
}

bool GameState::isDrawByRepetition() const {
    if (positionHistory.size() < 3) {
        return false;
    }
    std::string current_position = getPositionKey();
    int count = 0;
    for (const auto& pos : positionHistory) {
        if (pos == current_position) {
            count++;
        }
    }
    return count >= 3;
}

bool GameState::isDrawByFiftyMoves() const {
    return halfmoveClock >= 100;
}
