"""
PGN (Portable Game Notation) utilities for saving and loading chess games.
"""
import datetime
from typing import List, Optional, Tuple

def move_to_pgn(gs, move, check_after_move=False, checkmate_after_move=False) -> str:
    """
    Convert a Move object to PGN notation (e.g., 'e4', 'Nf3', 'O-O', 'exd5')
    
    Args:
        gs: GameState before the move
        move: Move object
        check_after_move: Whether this move gives check
        checkmate_after_move: Whether this move gives checkmate
    """
    # Castling
    if move.castle:
        # Kingside castle
        if move.endCol > move.startCol:
            notation = "O-O"
        # Queenside castle
        else:
            notation = "O-O-O"
    else:
        piece = move.pieceMoved[1]
        
        # Convert to algebraic notation
        files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        ranks = ['8', '7', '6', '5', '4', '3', '2', '1']
        
        start_file = files[move.startCol]
        start_rank = ranks[move.startRow]
        end_file = files[move.endCol]
        end_rank = ranks[move.endRow]
        
        # Piece prefix (empty for pawns)
        piece_prefix = '' if piece == 'p' else piece.upper()
        
        # Capture symbol
        capture = 'x' if move.isCapture else ''
        
        # For pawn captures, include starting file
        if piece == 'p' and move.isCapture:
            notation = f"{start_file}{capture}{end_file}{end_rank}"
        elif piece == 'p':
            notation = f"{end_file}{end_rank}"
        else:
            # For pieces, check if disambiguation is needed
            disambiguation = ""
            
            # Check if other pieces of same type can move to same square
            valid_moves = gs.getValidMoves()
            ambiguous_moves = []
            for m in valid_moves:
                # Same piece type and destination, but different starting position
                if (m.pieceMoved[1] == piece and 
                    m.endRow == move.endRow and m.endCol == move.endCol and
                    (m.startRow != move.startRow or m.startCol != move.startCol)):
                    ambiguous_moves.append(m)
            
            # If there are ambiguous moves, add disambiguation
            if ambiguous_moves:
                # Check if file is enough to disambiguate
                same_file = any(m.startCol == move.startCol for m in ambiguous_moves)
                same_rank = any(m.startRow == move.startRow for m in ambiguous_moves)
                
                if not same_file:
                    # File is unique, use it
                    disambiguation = start_file
                elif not same_rank:
                    # Rank is unique, use it
                    disambiguation = start_rank
                else:
                    # Need both file and rank
                    disambiguation = f"{start_file}{start_rank}"
            
            notation = f"{piece_prefix}{disambiguation}{capture}{end_file}{end_rank}"
        
        # Add promotion
        if move.isPawnPromotion and move.promotion:
            # Handle both "wQ" format and "Q" format
            if len(move.promotion) >= 2:
                promo_piece = move.promotion[1].upper()
            elif len(move.promotion) == 1:
                promo_piece = move.promotion[0].upper()
            else:
                promo_piece = 'Q'  # Default to Queen
            notation += f"={promo_piece}"
    
    # Add check/checkmate symbols
    if checkmate_after_move:
        notation += '#'
    elif check_after_move:
        notation += '+'
    
    return notation


def save_game_to_pgn(moves: List[Tuple], result: str, player_white: bool, 
                     filename: str, opening_name: str = "Unknown") -> bool:
    """
    Save a chess game to PGN format.
    
    Args:
        moves: List of (move, notation) tuples
        result: "1-0", "0-1", "1/2-1/2", or "*"
        player_white: True if human played white
        filename: Output filename
        opening_name: Name of the opening played
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # PGN Headers
            f.write('[Event "Chess AI Game"]\n')
            f.write(f'[Site "Local Computer"]\n')
            f.write(f'[Date "{datetime.datetime.now().strftime("%Y.%m.%d")}"]\n')
            f.write('[Round "1"]\n')
            f.write(f'[White "{"Human" if player_white else "Chess AI"}"]\n')
            f.write(f'[Black "{"Chess AI" if player_white else "Human"}"]\n')
            f.write(f'[Result "{result}"]\n')
            f.write(f'[Opening "{opening_name}"]\n')
            f.write('\n')
            
            # Moves - strict formatting for Chess.com compatibility
            move_number = 1
            line = ""
            for i, (move_obj, notation) in enumerate(moves):
                # Ensure notation is valid (no embedded spaces or invalid chars)
                notation = notation.strip()
                
                if i % 2 == 0:
                    # White's move
                    move_text = f"{move_number}. {notation}"
                else:
                    # Black's move
                    move_text = notation
                    move_number += 1
                
                # Add to line with proper spacing
                if line:
                    line += " " + move_text
                else:
                    line = move_text
                    
                # Wrap at reasonable length (but complete the move pair)
                if i % 2 == 1 and len(line) > 60:
                    f.write(line + '\n')
                    line = ""
            
            # Write remaining moves and result on same line
            if line:
                f.write(line + ' ')
            f.write(f"{result}\n")
        
        return True
    except Exception as e:
        print(f"Error saving PGN: {e}")
        return False


def parse_pgn_text(pgn_text: str) -> Optional[Tuple[List[str], dict]]:
    """
    Parse PGN text content.
    
    Returns:
        (moves_list, metadata) or None if failed
        moves_list: List of move notations (e.g., ['e4', 'e5', 'Nf3', ...])
        metadata: Dict with game info (Event, White, Black, etc.)
    """
    try:
        # Parse headers
        metadata = {}
        lines = pgn_text.split('\n')
        move_text = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('[') and line.endswith(']'):
                # Parse header
                parts = line[1:-1].split('"')
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    metadata[key] = value
            elif line and not line.startswith('['):
                # Moves section
                move_text += " " + line
        
        # Parse moves
        moves = []
        move_text = move_text.strip()
        
        # Remove result indicators
        for result in ['1-0', '0-1', '1/2-1/2', '*']:
            move_text = move_text.replace(result, '')
        
        # Remove comments and variations
        import re
        move_text = re.sub(r'\{[^}]*\}', '', move_text)  # Remove {comments}
        move_text = re.sub(r'\([^)]*\)', '', move_text)  # Remove (variations)
        
        # Remove move numbers
        move_text = re.sub(r'\d+\.+', '', move_text)
        
        # Split into individual moves
        tokens = move_text.split()
        for token in tokens:
            token = token.strip()
            if token and not token.startswith('$'):  # Skip annotations
                moves.append(token)
        
        return (moves, metadata)
    
    except Exception as e:
        print(f"Error parsing PGN: {e}")
        return None


def load_game_from_pgn(filename: str) -> Optional[Tuple[List[str], dict]]:
    """
    Load a chess game from PGN file.
    
    Returns:
        (moves_list, metadata) or None if failed
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_pgn_text(content)
    except Exception as e:
        print(f"Error loading PGN file: {e}")
        return None


def load_game_from_clipboard() -> Optional[Tuple[List[str], dict]]:
    """
    Load a chess game from clipboard (PGN text).
    
    Returns:
        (moves_list, metadata) or None if failed
    """
    try:
        import pyperclip
        pgn_text = pyperclip.paste()
        if not pgn_text or len(pgn_text.strip()) == 0:
            print("Clipboard is empty")
            return None
        return parse_pgn_text(pgn_text)
    except ImportError:
        # Fallback to pygame scrap if pyperclip not available
        try:
            import pygame.scrap
            pygame.scrap.init()
            if pygame.scrap.get_init():
                pgn_bytes = pygame.scrap.get(pygame.SCRAP_TEXT)
                if pgn_bytes:
                    pgn_text = pgn_bytes.decode('utf-8', errors='ignore')
                    return parse_pgn_text(pgn_text)
            print("Could not access clipboard")
            return None
        except Exception as e:
            print(f"Error reading clipboard: {e}")
            return None
    except Exception as e:
        print(f"Error loading PGN from clipboard: {e}")
        return None


def pgn_to_move(gs, pgn_notation: str):
    """
    Convert PGN notation to a Move object by finding the matching legal move.
    
    Args:
        gs: Current GameState
        pgn_notation: PGN notation (e.g., 'e4', 'Nf3', 'O-O')
    
    Returns:
        Move object or None if not found
    """
    # Remove check/checkmate symbols
    notation = pgn_notation.replace('+', '').replace('#', '').replace('!', '').replace('?', '').strip()
    
    valid_moves = gs.getValidMoves()
    
    # Handle castling
    if notation == "O-O" or notation == "0-0":
        # Kingside castle
        for move in valid_moves:
            if move.castle and move.endCol > move.startCol:
                return move
    elif notation == "O-O-O" or notation == "0-0-0":
        # Queenside castle
        for move in valid_moves:
            if move.castle and move.endCol < move.startCol:
                return move
    
    files = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}
    ranks = {'8': 0, '7': 1, '6': 2, '5': 3, '4': 4, '3': 5, '2': 6, '1': 7}
    
    # Parse notation
    piece_type = 'p'  # Default to pawn
    if notation[0].isupper():
        piece_type = notation[0].lower()
        notation = notation[1:]
    
    # Check for capture
    is_capture = 'x' in notation
    notation = notation.replace('x', '')
    
    # Check for promotion
    promotion = ''
    if '=' in notation:
        parts = notation.split('=')
        notation = parts[0]
        promotion = parts[1].lower() if len(parts) > 1 else ''
    
    # Get destination square (last 2 characters)
    if len(notation) >= 2:
        dest_file = notation[-2]
        dest_rank = notation[-1]
        
        if dest_file in files and dest_rank in ranks:
            dest_col = files[dest_file]
            dest_row = ranks[dest_rank]
            
            # Disambiguation (if notation has extra info)
            start_file = None
            start_rank = None
            if len(notation) > 2:
                if notation[0] in files:
                    start_file = files[notation[0]]
                if notation[0] in ranks:
                    start_rank = ranks[notation[0]]
                if len(notation) > 3:
                    if notation[1] in files:
                        start_file = files[notation[1]]
                    if notation[1] in ranks:
                        start_rank = ranks[notation[1]]
            
            # Find matching move
            for move in valid_moves:
                # Check piece type
                if move.pieceMoved[1].lower() != piece_type:
                    continue
                
                # Check destination
                if move.endRow != dest_row or move.endCol != dest_col:
                    continue
                
                # Check disambiguation
                if start_file is not None and move.startCol != start_file:
                    continue
                if start_rank is not None and move.startRow != start_rank:
                    continue
                
                # Check capture
                if is_capture and not move.isCapture:
                    continue
                
                # Check promotion
                if promotion and move.promotion:
                    if move.promotion[1].lower() != promotion.lower():
                        continue
                elif promotion or move.isPawnPromotion:
                    continue
                
                return move
    
    return None

