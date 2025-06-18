/* TimeFilter.tsx */
type Props = {
  value: "today" | "week" | "all";
  onChange: (v: "today" | "week" | "all") => void;
};

export default function TimeFilter({ value, onChange }: Props) {
  const opts = [
    { lab: "Today",     v: "today" },
    { lab: "This week", v: "week"  },
    { lab: "All time",  v: "all"   }
  ];

  return (
    /* Conteneur centré dans son bloc (horizontal + vertical) */
    <div className="flex justify-center items-center gap-2 mb-3 w-full h-full">
      {opts.map(o => (
        <button
          key={o.v}
          className={`px-3 py-1 rounded text-sm ${
            value === o.v ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => onChange(o.v)}
        >
          {o.lab}
        </button>
      ))}
    </div>
  );
}
