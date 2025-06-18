import React from 'react';

export default function RightColumn({ dateFilter, setDateFilter }) {
  return (
    <div className="right-column">
      {/* filtres Today / Week / All time */}
      <div className="BLOCR1_TRENDS_FILTRE_DATE card">
        <div className="filter-group">
          <button
            className={`filter-btn ${dateFilter==='today'?'active':''}`}
            onClick={()=>setDateFilter('today')}
          >
            Today
          </button>
          <button
            className={`filter-btn ${dateFilter==='week'?'active':''}`}
            onClick={()=>setDateFilter('week')}
          >
            This&nbsp;week
          </button>
          <button
            className={`filter-btn ${dateFilter==='all'?'active':''}`}
            onClick={()=>setDateFilter('all')}
          >
            All&nbsp;time
          </button>
        </div>
      </div>

      {/* les autres blocs sont encore vides */}
      <div className="BLOCR2_TRENDS_NOMBRE_POST card" />
      <div className="BLOCR3_TRENDS_LISTE_KEYWORDS card" />
      <div className="BLOCR4_TRENDS_SENTIMENTS card" />
      <div className="BLOCR5_FILTRE_TRENDS_CATEGORIES card" />
      <div className="BLOCR6_TRENDS_TOXICITE card" />
      <div className="BLOCR7_TRENDS_BOT_DETECTION card" />
    </div>
  );
}
