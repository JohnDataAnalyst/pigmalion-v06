/* CategoryFilter.jsx */
const CATS = [
  "news_social_concern","arts_entertainment","sports_gaming","pop_culture",
  "learning_educational","science_technology","business_entrepreneurship",
  "food_dining","travel_adventure","fashion_style","health_fitness","family"
];

export default function CategoryFilter({ value, onChange }) {
  return (
    <div className="grid grid-cols-4 gap-2 mb-4">
      {["All", ...CATS].map(cat => {
        // « All » correspond à l’état “aucune catégorie sélectionnée” (null)
        const key     = cat === "All" ? null : cat;
        const active  = value === key;                       // actif ?
        const classes = active
          ? "bg-green-600 text-white"
          : "bg-gray-200";

        return (
          <button
            key={cat}
            className={`text-xs px-2 py-1 rounded ${classes}`}
            // ➊ si on reclique sur la catégorie active → on repasse à null (= agrégat global)
            // ➋ sinon on sélectionne cette catégorie
            onClick={() => onChange(active ? null : key)}
          >
            {cat.replace(/_/g, " ")}
          </button>
        );
      })}
    </div>
  );
}