export function MechanismDrawing() {
  return (
    <svg
      className="mechanism-drawing"
      viewBox="0 0 360 150"
      fill="none"
      role="img"
      aria-label="Concept illustration of a rail carriage; no generated CAD"
    >
      <g stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round">
        <path
          opacity=".3"
          d="M22 124h316M44 20v115M315 20v115"
          strokeDasharray="3 5"
        />
        <path d="m57 95 198-52 49 28-198 53z" />
        <path d="m57 95 0 10 49 28 198-53V71M106 124v9" />
        <path d="m73 83 176-46 6 6L80 90zM87 105l175-46 7 5-175 47z" />
        <path d="m142 70 60-16 38 22-60 16zM142 70v21l38 22V92M180 113l60-16V76" />
        <path d="m155 76 45-12 27 16-46 12z" />
        <ellipse cx="184" cy="78" rx="9" ry="4" />
        <path
          d="m158 87 7 4m57-7 7 4M111 45l105-27M111 41v8m105-35v8"
          opacity=".5"
        />
      </g>
      <g fill="currentColor" fontSize="9" fontFamily="monospace" opacity=".7">
        <text x="132" y="27" transform="rotate(-14 132 27)">
          DESIGN INTENT
        </text>
        <text x="257" y="128">
          CONCEPT / 01
        </text>
      </g>
    </svg>
  );
}
