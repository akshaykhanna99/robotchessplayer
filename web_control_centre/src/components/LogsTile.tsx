import type { LogEntry } from "../types";
import { Tile } from "./Tile";

type LogsTileProps = {
  logs: LogEntry[];
  embedded?: boolean;
};

function LogsContent({ logs }: { logs: LogEntry[] }) {
  return (
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
  );
}

export function LogsTile({ logs, embedded = false }: LogsTileProps) {
  if (embedded) {
    return <LogsContent logs={logs} />;
  }

  return (
    <Tile title="Logs" className="tile-logs">
      <LogsContent logs={logs} />
    </Tile>
  );
}
