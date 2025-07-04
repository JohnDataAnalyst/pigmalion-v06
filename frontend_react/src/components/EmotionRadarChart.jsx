import React from 'react';
import {
  Radar, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer
} from 'recharts';

export default function EmotionRadarChart({ data }) {
  const chartData = [
    { subject: 'Joy',      A: parseFloat(data.out_post_score_sentiments_joy)      },
    { subject: 'Surprise', A: parseFloat(data.out_post_score_sentiments_surprise) },
    { subject: 'Sadness',  A: parseFloat(data.out_post_score_sentiments_sadness)  },
    { subject: 'Disgust',  A: parseFloat(data.out_post_score_sentiments_disgust)  },
    { subject: 'Fear',     A: parseFloat(data.out_post_score_sentiments_fear)     },
    { subject: 'Anger',    A: parseFloat(data.out_post_score_sentiments_anger)    }
  ];

  const emotions = {
    anger:   data.out_post_score_sentiments_anger,
    disgust: data.out_post_score_sentiments_disgust,
    fear:    data.out_post_score_sentiments_fear,
    joy:     data.out_post_score_sentiments_joy,
    sadness: data.out_post_score_sentiments_sadness,
    surprise:data.out_post_score_sentiments_surprise,
  };

  const dominant = Object.entries(emotions).reduce((a, b) => (a[1] > b[1] ? a : b));
  const labelFr = {
    anger: 'colère', disgust: 'dégoût', fear: 'peur',
    joy: 'joie', sadness: 'tristesse', surprise: 'surprise'
  };

  return (
    <div className="emotion-radar-wrapper">
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
          <PolarGrid stroke="#ccc" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#333', fontSize: 12 }} />
          <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fill: '#333', fontSize: 10 }} />
          <Radar
            name="Emotion"
            dataKey="A"
            stroke="#5ACEB7"
            fill="#5ACEB7"
            fillOpacity={0.6}
          />
        </RadarChart>
      </ResponsiveContainer>
      <div style={{ textAlign: 'center', fontSize: 13, marginTop: 8, color: '#222' }}>
        Le post exprime principalement <strong>{labelFr[dominant[0]]}</strong> ({Math.round(dominant[1] * 100)} %).
      </div>
    </div>
  );
}
