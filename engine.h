#ifndef ENGINE_H
#define ENGINE_H

#include <vector>
#include <string>
#include <array>
#include <tuple>

class Move {
public:
    int startRow, startCol, endRow, endCol;
    int moveID;
    std::string pieceMoved;
    std::string pieceCaptured;
    std::string promotion;
    bool isEnpassantMove;
    bool castle;
    bool isCapture;
    bool isPawnPromotion;

    Move() : startRow(0), startCol(0), endRow(0), endCol(0), moveID(0),
             pieceMoved("--"), pieceCaptured("--"), promotion(""),
             isEnpassantMove(false), castle(false), 
             isCapture(false), isPawnPromotion(false) {}
    
    Move(int sRow, int sCol, int eRow, int eCol, 
         const std::array<std::array<std::string, 8>, 8>& board,
         bool enpassant = false, bool isCastle = false, 
         const std::string& promo = "");
    
    bool operator==(const Move& other) const;
    std::string getChessNotation() const;
    std::string toString() const;

private:
    std::string getRankFile(int row, int col) const;
};

class CastleRights {
public:
    bool wks, wqs, bks, bqs;
    CastleRights(bool wKingSide, bool wQueenSide, bool bKingSide, bool bQueenSide)
        : wks(wKingSide), wqs(wQueenSide), bks(bKingSide), bqs(bQueenSide) {}
};

class GameState {
public:
    std::array<std::array<std::string, 8>, 8> board;
    bool whiteToMove;
    std::vector<Move> moveLog;
    std::pair<int, int> whiteKingLocation;
    std::pair<int, int> blackKingLocation;
    bool checkmate;
    bool stalemate;
    bool inCheck;
    std::vector<std::tuple<int, int, int, int>> pins;
    std::vector<std::tuple<int, int, int, int>> checks;
    std::pair<int, int> enpassantPossible;
    bool whiteCastleKingside;
    bool whiteCastleQueenside;
    bool blackCastleKingside;
    bool blackCastleQueenside;
    std::vector<std::pair<int, int>> enpassantPossibleLog;
    std::vector<CastleRights> castleRightsLog;
    std::vector<int> halfmoveClockLog;
    bool playerWantsToPlayAsBlack;
    int halfmoveClock;
    std::vector<std::string> positionHistory;

    GameState();
    void makeMove(const Move& move);
    void undoMove();
    std::vector<Move> getValidMoves();
    std::vector<Move> getAllPossibleMoves();
    bool squareUnderAttack(int row, int col, char allyColor);
    std::tuple<bool, std::vector<std::tuple<int, int, int, int>>, 
               std::vector<std::tuple<int, int, int, int>>> checkForPinsAndChecks();
    std::string getBoardString() const;
    std::string getPositionKey() const;
    bool isDrawByRepetition() const;
    bool isDrawByFiftyMoves() const;

private:
    void getPawnMoves(int row, int col, std::vector<Move>& moves);
    void getRookMoves(int row, int col, std::vector<Move>& moves);
    void getBishopMoves(int row, int col, std::vector<Move>& moves);
    void getKnightMoves(int row, int col, std::vector<Move>& moves);
    void getQueenMoves(int row, int col, std::vector<Move>& moves);
    void getKingMoves(int row, int col, std::vector<Move>& moves);
    void getCastleMoves(int row, int col, std::vector<Move>& moves, char allyColor);
    void getKingsideCastleMoves(int row, int col, std::vector<Move>& moves, char allyColor);
    void getQueensideCastleMoves(int row, int col, std::vector<Move>& moves, char allyColor);
    void updateCastleRights(const Move& move);
};

#endif
