import React, { PureComponent } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default class ToxicityChart extends PureComponent {
  render() {
    const data = this.props.data;

    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 10, right: 20, left: 20, bottom: 10 }}
        >
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis dataKey="label" type="category" tick={{ fontSize: 12 }} width={80} />
          <Tooltip formatter={(value) => (value * 100).toFixed(1) + '%'} />
          <Bar dataKey="score" fill="#E74C3C" />
        </BarChart>
      </ResponsiveContainer>
    );
  }
}
