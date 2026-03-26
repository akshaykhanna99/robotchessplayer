import { useState } from "react";

const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
const DEFAULT_STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR";

const pieceGlyphs: Record<string, string> = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

const observedGlyphs: Record<string, string> = {
  white: "◯",
  black: "●",
  empty: "",
};

function parseFenBoard(fen: string): string[][] {
  const rows = fen.split("/");
  if (rows.length !== 8) {
    return Array.from({ length: 8 }, () => Array.from({ length: 8 }, () => ""));
  }

  return rows.map((row) => {
    const expanded: string[] = [];
    for (const char of row) {
      const count = Number(char);
      if (Number.isInteger(count) && count > 0) {
        for (let index = 0; index < count; index += 1) {
          expanded.push("");
        }
      } else {
        expanded.push(char);
      }
    }
    return expanded.slice(0, 8);
  });
}

function parseDetectedMove(detectedMove: string): { fromSquare: string | null; toSquare: string | null } {
  const normalized = detectedMove.trim().toLowerCase();
  if (!/^[a-h][1-8][a-h][1-8]$/.test(normalized)) {
    return { fromSquare: null, toSquare: null };
  }
  return {
    fromSquare: normalized.slice(0, 2),
    toSquare: normalized.slice(2, 4),
  };
}

type BoardPreviewProps = {
  fen: string;
  observedBoard: string[][];
  observedBoardInitialized: boolean;
  sessionActive: boolean;
  detectedMove: string;
  sideToMove: string;
  suggestedMove: string;
};

export function BoardPreview({
  fen,
  observedBoard,
  observedBoardInitialized,
  sessionActive,
  detectedMove,
  sideToMove,
  suggestedMove,
}: BoardPreviewProps) {
  const fenBoard = parseFenBoard(fen.split(" ")[0] || DEFAULT_STARTING_FEN);
  const board = sessionActive ? fenBoard : observedBoardInitialized ? observedBoard : parseFenBoard(DEFAULT_STARTING_FEN);
  const { fromSquare, toSquare } = parseDetectedMove(detectedMove);
  const [showFen, setShowFen] = useState(false);

  return (
    <div className="board-shell">
      <div className="board-file-labels">
        <span />
        {files.map((file) => (
          <span key={file}>{file}</span>
        ))}
      </div>

      <div className="board-body">
        <div className="board-rank-labels">
          {board.map((_, rowIndex) => {
            const rank = 8 - rowIndex;
            return <div className="board-rank-label" key={rank}>{rank}</div>;
          })}
        </div>

        <div className="board-frame">
          {board.map((row, rowIndex) => {
            const rank = 8 - rowIndex;
            return (
              <div className="board-row" key={rank}>
                {row.map((piece, fileIndex) => {
                  const square = `${files[fileIndex]}${rank}`;
                  const glyph = sessionActive
                    ? pieceGlyphs[piece] ?? ""
                    : observedBoardInitialized
                      ? observedGlyphs[piece] ?? ""
                      : pieceGlyphs[piece] ?? "";
                  const isLight = (fileIndex + rank) % 2 === 0;
                  const isWhitePiece = sessionActive
                    ? piece !== "" && piece === piece.toUpperCase()
                    : observedBoardInitialized
                      ? piece === "white"
                      : piece !== "" && piece === piece.toUpperCase();
                  const moveClass =
                    square === fromSquare ? "move-from" : square === toSquare ? "move-to" : "";
                  return (
                    <div
                      key={square}
                      className={`board-cell ${isLight ? "light" : "dark"} ${glyph ? "occupied" : "empty"} ${moveClass}`.trim()}
                    >
                      {glyph ? (
                        <span className={`piece-glyph ${isWhitePiece ? "white-piece" : "black-piece"}`}>{glyph}</span>
                      ) : (
                        <span className="square-label">{square}</span>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      <div className="board-pill-row">
        <span className="pill board-pill">Turn: {sideToMove}</span>
        <span className={`pill board-pill ${detectedMove !== "-" ? "" : "pill-muted"}`.trim()}>
          Detected: {detectedMove}
        </span>
        <span className={`pill board-pill ${suggestedMove !== "-" ? "" : "pill-muted"}`.trim()}>
          Suggested: {suggestedMove}
        </span>
        <button type="button" className="fen-info-button" onClick={() => setShowFen(true)} aria-label="Show FEN">
          <span aria-hidden="true">ℹ</span>
        </button>
      </div>

      {showFen ? (
        <div className="fen-modal-backdrop" onClick={() => setShowFen(false)}>
          <div className="fen-modal" onClick={(event) => event.stopPropagation()}>
            <div className="fen-modal-head">
              <strong>FEN</strong>
              <button type="button" className="fen-close-button" onClick={() => setShowFen(false)}>
                Close
              </button>
            </div>
            <div className="fen-modal-value">{fen}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
