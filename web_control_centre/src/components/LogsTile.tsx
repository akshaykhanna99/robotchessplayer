import type { LogEntry } from "../types";
import { Tile } from "./Tile";

type LogsTileProps = {
  logs: LogEntry[];
};

export function LogsTile({ logs }: LogsTileProps) {
  return (
    <Tile title="Logs" className="tile-logs">
      <div className="log-console">
        {logs
          .slice()
          .reverse()
          .map((entry, index) => (
            <article className="log-entry" data-level={entry.level} key={`${entry.level}-${index}-${entry.message}`}>
              <span className="log-level">[{entry.level}]</span>
              <span className="log-message">{entry.message}</span>
            </article>
          ))}
      </div>
    </Tile>
  );
}
