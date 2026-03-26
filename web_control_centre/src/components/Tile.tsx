import type { PropsWithChildren, ReactNode } from "react";

type TileProps = PropsWithChildren<{
  title: string;
  aside?: ReactNode;
  className?: string;
}>;

export function Tile({ title, aside, className = "", children }: TileProps) {
  return (
    <section className={`tile ${className}`.trim()}>
      <div className="tile-head">
        <h2>{title}</h2>
        {aside ? <div>{aside}</div> : null}
      </div>
      {children}
    </section>
  );
}
