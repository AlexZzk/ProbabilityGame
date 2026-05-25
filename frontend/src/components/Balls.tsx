interface Props {
  reds: number[];
  blue: number;
  highlightReds?: Set<number>;
  highlightBlue?: boolean;
}

export function Balls({ reds, blue, highlightReds, highlightBlue }: Props) {
  return (
    <span>
      {reds.map((n) => (
        <span
          key={n}
          className="ball red"
          style={highlightReds?.has(n) ? { outline: "2px solid #fbbf24" } : undefined}
        >
          {n.toString().padStart(2, "0")}
        </span>
      ))}
      <span
        className="ball blue"
        style={highlightBlue ? { outline: "2px solid #fbbf24" } : undefined}
      >
        {blue.toString().padStart(2, "0")}
      </span>
    </span>
  );
}
