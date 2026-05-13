#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "engine.h"
#include "chessAi.h"

extern std::atomic<int> currentBestScore;
extern std::atomic<int> mateDepth;

namespace py = pybind11;

PYBIND11_MODULE(chess_cpp, m) {
    m.doc() = "C++ Chess Engine and AI module";
    py::class_<Move>(m, "Move")
        .def(py::init<int, int, int, int, const std::array<std::array<std::string, 8>, 8>&, bool, bool, const std::string&>(),
             py::arg("startRow"), py::arg("startCol"), py::arg("endRow"), py::arg("endCol"),
             py::arg("board"), py::arg("isEnpassantMove") = false, 
             py::arg("castle") = false, py::arg("promotion") = "")
        .def_readwrite("startRow", &Move::startRow)
        .def_readwrite("startCol", &Move::startCol)
        .def_readwrite("endRow", &Move::endRow)
        .def_readwrite("endCol", &Move::endCol)
        .def_readwrite("pieceMoved", &Move::pieceMoved)
        .def_readwrite("pieceCaptured", &Move::pieceCaptured)
        .def_readwrite("isEnpassantMove", &Move::isEnpassantMove)
        .def_readwrite("castle", &Move::castle)
        .def_readwrite("promotion", &Move::promotion)
        .def_readwrite("isCapture", &Move::isCapture)
        .def_readwrite("isPawnPromotion", &Move::isPawnPromotion)
        .def_readwrite("moveID", &Move::moveID)
        .def("getChessNotation", &Move::getChessNotation)
        .def("toString", &Move::toString)
        .def("__str__", &Move::toString)
        .def("__repr__", &Move::toString)
        .def("__eq__", &Move::operator==);
    
    // CastleRights class binding
    py::class_<CastleRights>(m, "CastleRights")
        .def(py::init<bool, bool, bool, bool>())
        .def_readwrite("wks", &CastleRights::wks)
        .def_readwrite("wqs", &CastleRights::wqs)
        .def_readwrite("bks", &CastleRights::bks)
        .def_readwrite("bqs", &CastleRights::bqs);
    py::class_<GameState>(m, "GameState")
        .def(py::init<>())
        .def_readwrite("board", &GameState::board)
        .def_readwrite("whiteToMove", &GameState::whiteToMove)
        .def_readwrite("moveLog", &GameState::moveLog)
        .def_readwrite("whiteKingLocation", &GameState::whiteKingLocation)
        .def_readwrite("blackKingLocation", &GameState::blackKingLocation)
        .def_readwrite("checkmate", &GameState::checkmate)
        .def_readwrite("stalemate", &GameState::stalemate)
        .def_readwrite("inCheck", &GameState::inCheck)
        .def_readwrite("pins", &GameState::pins)
        .def_readwrite("checks", &GameState::checks)
        .def_readwrite("enpassantPossible", &GameState::enpassantPossible)
        .def_readwrite("whiteCastleKingside", &GameState::whiteCastleKingside)
        .def_readwrite("whiteCastleQueenside", &GameState::whiteCastleQueenside)
        .def_readwrite("blackCastleKingside", &GameState::blackCastleKingside)
        .def_readwrite("blackCastleQueenside", &GameState::blackCastleQueenside)
        .def_readwrite("enpassantPossibleLog", &GameState::enpassantPossibleLog)
        .def_readwrite("castleRightsLog", &GameState::castleRightsLog)
        .def_readwrite("halfmoveClockLog", &GameState::halfmoveClockLog)
        .def_readwrite("playerWantsToPlayAsBlack", &GameState::playerWantsToPlayAsBlack)
        .def_readwrite("halfmoveClock", &GameState::halfmoveClock)
        .def_readwrite("positionHistory", &GameState::positionHistory)
        .def("makeMove", &GameState::makeMove)
        .def("undoMove", &GameState::undoMove)
        .def("getValidMoves", &GameState::getValidMoves)
        .def("getAllPossibleMoves", &GameState::getAllPossibleMoves)
        .def("squareUnderAttack", &GameState::squareUnderAttack)
        .def("checkForPinsAndChecks", &GameState::checkForPinsAndChecks)
        .def("getBoardString", &GameState::getBoardString)
        .def("getPositionKey", &GameState::getPositionKey)
        .def("isDrawByRepetition", &GameState::isDrawByRepetition)
        .def("isDrawByFiftyMoves", &GameState::isDrawByFiftyMoves);
    m.def("findBestMove", &findBestMove, "Find the best move using negamax alpha-beta search",
          py::arg("gs"), py::arg("validMoves"), py::call_guard<py::gil_scoped_release>());
    m.def("findBestMoveIterative", &findBestMoveIterative, "Find the best move using iterative deepening",
          py::arg("gs"), py::arg("validMoves"), py::arg("timeLimitSeconds") = 0.0, py::call_guard<py::gil_scoped_release>());
    m.def("scoreBoard", &scoreBoard, "Evaluate the board position",
          py::arg("gs"), py::arg("depth") = 0, py::call_guard<py::gil_scoped_release>());
    m.def("initializePST", &initializePST, "Initialize piece-square tables");
    m.def("cloneGameState", [](GameState gs){ return gs; },
          "Return a deep copy of GameState");
    m.def("get_progress_counters", [](){
        extern int indepth;
        int done = rootDone.load();
        int total = rootTotal.load();
        long long nodes = cnt.load();
        int bestScore = currentBestScore.load();
        int mate = mateDepth.load();
        int depth = indepth;
        return py::make_tuple(done, total, nodes, bestScore, mate, depth);
    });
    m.attr("CHECKMATE") = py::int_(CHECKMATE);
    m.attr("STALEMATE") = py::int_(STALEMATE);
    m.attr("DEPTH") = py::int_(DEPTH);
}
