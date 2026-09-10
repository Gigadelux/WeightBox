// An original, deliberately generic hardware drawing; not a product photograph.
export function GpuIllustration() {
  return (
    <svg
      className="gpu-illustration"
      viewBox="0 0 340 210"
      fill="none"
      aria-hidden="true"
    >
      <g stroke="#729184" strokeWidth="0.7" opacity="0.35">
        <path
          d="M15 35h310M15 175h310M35 15v180M305 15v180"
          strokeDasharray="3 5"
        />
        <path d="M22 35h26M35 22v26M292 175h26M305 162v26" />
      </g>
      <g transform="translate(25 58) rotate(-10 145 55)">
        <path
          d="M17 98L271 98L286 82V16L270 2H18L4 17V83Z"
          fill="#152a24"
          stroke="#95a79d"
          strokeWidth="1.2"
        />
        <path d="M17 98v12h242l12-12" fill="#101f1a" stroke="#5f796b" />
        <path d="M41 110v9h83v-9M137 110v9h84v-9" fill="#b3a66d" />
        {Array.from({ length: 26 }, (_, i) => (
          <path
            key={i}
            d={`M${44 + i * 6.7} 111v7`}
            stroke="#1b332a"
            strokeWidth="2"
          />
        ))}
        <path
          d="M5 17H-5v70H5M-5 24h-7v10h7M-5 44h-7v10h7M-5 64h-7v10h7"
          stroke="#a1b2a8"
        />
        <path
          d="M132 6l-18 84M158 6l-18 84M18 6l20 10M261 6l15 14"
          stroke="#557467"
        />
        {[74, 212].map((cx) => (
          <g key={cx} transform={`translate(${cx} 49)`}>
            <circle r="40" stroke="#84998d" />
            <circle r="35" fill="#0e211b" stroke="#3f5f50" />
            {Array.from({ length: 9 }, (_, i) => (
              <path
                key={i}
                d="M5-9C20-30 34-22 32-14C23-18 14-10 10-3Z"
                transform={`rotate(${i * 40})`}
                fill="#3e5d4e"
                stroke="#769181"
                strokeWidth="0.5"
              />
            ))}
            <circle r="10" fill="#1c392d" stroke="#8ca495" />
            <circle r="3" stroke="#7e9a88" />
          </g>
        ))}
        {[
          [18, 17],
          [272, 17],
          [18, 85],
          [272, 85],
        ].map(([x, y]) => (
          <g key={`${x}-${y}`}>
            <circle cx={x} cy={y} r="2" stroke="#829a8c" />
            <path d={`M${x - 1} ${y}h2`} stroke="#829a8c" />
          </g>
        ))}
        <path
          d="M151 13h17M150 18h17M149 23h17M148 28h17"
          stroke="#8fa899"
          strokeWidth="1.5"
        />
      </g>
      <path d="M256 156l17 24h39" stroke="#9db3a3" strokeWidth="0.7" />
      <circle cx="256" cy="156" r="2" fill="#b1c7b6" />
      <text
        x="274"
        y="194"
        fill="#a7beae"
        fontSize="7"
        fontFamily="monospace"
        letterSpacing="1.5"
      >
        SCHEMATIC
      </text>
    </svg>
  );
}
