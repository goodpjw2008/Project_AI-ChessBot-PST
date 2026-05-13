#ifndef CHESSAI_H
#define CHESSAI_H

#include "engine.h"
#include <map>
#include <array>
#include <atomic>

constexpr int CHECKMATE = 10000000;
constexpr int STALEMATE = 0;
constexpr int DEPTH = 8;

extern std::map<char, int> pieceScore;

extern std::array<std::array<int, 8>, 8> whitePstP;
extern std::array<std::array<int, 8>, 8> whitePstN;
extern std::array<std::array<int, 8>, 8> whitePstB;
extern std::array<std::array<int, 8>, 8> whitePstR;
extern std::array<std::array<int, 8>, 8> whitePstQ;
extern std::array<std::array<int, 8>, 8> whitePstK;

extern std::array<std::array<int, 8>, 8> blackPstP;
extern std::array<std::array<int, 8>, 8> blackPstN;
extern std::array<std::array<int, 8>, 8> blackPstB;
extern std::array<std::array<int, 8>, 8> blackPstR;
extern std::array<std::array<int, 8>, 8> blackPstQ;
extern std::array<std::array<int, 8>, 8> blackPstK;

Move findBestMove(GameState& gs, std::vector<Move>& validMoves);
Move findBestMoveIterative(GameState& gs, std::vector<Move>& validMoves, double timeLimitSeconds = 0.0);
int findMoveNegaMaxAlphaBeta(GameState& gs, std::vector<Move>& validMoves, 
                              const int depth, int alpha, const int beta, const int turnMultiplier);
int quiescenceSearch(GameState& gs, int alpha, int beta, const int turnMultiplier);
int scoreBoard(const GameState& gs, const int depth) noexcept;
void initializePST();

// Killer moves for move ordering (2 killer moves per depth)
constexpr int MAX_KILLER_DEPTH = 32;
struct KillerMoves {
    Move move1;
    Move move2;
    bool hasMove1 = false;
    bool hasMove2 = false;
};
extern std::array<KillerMoves, MAX_KILLER_DEPTH> killerMoves;
void clearKillerMoves();

// History Heuristic
extern std::array<std::array<std::array<std::array<int, 8>, 8>, 8>, 8> historyTable;
void clearHistoryTable();

// Countermove Heuristic
struct CountermoveEntry {
    Move move;
    bool valid = false;
};
extern std::array<std::array<std::array<std::array<CountermoveEntry, 8>, 8>, 8>, 8> countermoveTable;
void clearCountermoveTable();

// Progress counters for UI
extern std::atomic<long long> cnt;
extern std::atomic<int> rootTotal;
extern std::atomic<int> rootDone;
extern std::atomic<int> currentBestScore;
extern std::atomic<int> mateDepth;

// Simple position cache (lightweight)
constexpr size_t CACHE_SIZE = 4096;  // 4K entries only
struct SimpleCache {
    uint64_t key = 0;
    int score = 0;
    int depth = -1;
};
extern std::array<SimpleCache, CACHE_SIZE> positionCache;

#endif
