import { useState, useEffect } from "react";

export default function PostCountCard({ period, category }) {
  const [count, setCount] = useState("…");

  useEffect(() => {
    setCount("…");
    fetch(`/api/trends/count?period=${period}&category=${encodeURIComponent(category)}`)

      .then((r) => r.json())
      .then((d) => {
        if (d && d.posts !== undefined) {
          setCount(d.posts.toLocaleString());
        } else {
          setCount("—");
        }
      })
      .catch(() => setCount("—"));
  }, [period, category]);

  return (
    <div className="rounded-lg bg-white shadow p-5 text-center">
      <p className="text-sm text-gray-500 mb-1">Posts</p>
      <p className="text-3xl font-semibold">{count}</p>
    </div>
  );
}
