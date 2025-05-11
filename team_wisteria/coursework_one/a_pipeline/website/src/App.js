import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";
import "./index.css";

// 指标映射表
const indicatorMap = {
  "scope_1_emissions": "Scope 1 Emissions (tCO₂)",
  "scope_2_emissions": "Scope 2 Emissions (tCO₂)",
  "scope_3_emissions": "Scope 3 Emissions (tCO₂)",
  "ghg_intensity": "GHG Intensity (tCO₂/million USD)",
  "total_energy": "Total Energy (MWh)",
  "renewable_energy_share": "Renewable Energy Share (%)",
  "energy_intensity": "Energy Intensity (MWh/million USD)",
  "total_water_withdrawal": "Total Water Withdrawal (ML)",
  "water_consumption": "Water Consumption (ML)",
  "water_reused_share": "Water Reused Share (%)",
  "total_plastic_usage": "Total Plastic Usage (tonnes)",
  "recycled_plastic_share": "Recycled Plastic Share (%)",
  "plastic_reduction_percent": "Plastic Reduction (%)"
};

function App() {
  const [search, setSearch] = useState("");
  const [companyData, setCompanyData] = useState([]);
  const [selectedCompanyRecords, setSelectedCompanyRecords] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [activeYear, setActiveYear] = useState(null);

  useEffect(() => {
    fetch("/csr_output.json")
      .then((res) => res.json())
      .then((data) => setCompanyData(data));
  }, []);

  useEffect(() => {
    if (search.trim() === "") {
      setSelectedCompanyRecords([]);
      setSuggestions([]);
      setActiveYear(null);
      return;
    }
    const lowerSearch = search.toLowerCase().trim();

    const matched = companyData.filter((item) =>
      item.company_id.toLowerCase().startsWith(lowerSearch)
    );

    const uniqueCompanyNames = [...new Set(matched.map(item => item.company_id))];
    const suggestionList = uniqueCompanyNames.map(name => ({ company_id: name }));

    setSuggestions(suggestionList.slice(0, 5));

    const matchedRecords = companyData.filter(
      (item) => item.company_id.toLowerCase().trim() === lowerSearch
    );

    matchedRecords.sort((a, b) => b.reporting_year - a.reporting_year);

    setSelectedCompanyRecords(matchedRecords);
    setActiveYear(null); // 每次新搜索，重置展开状态
  }, [search, companyData]);

  const buildChartData = (company) => {
    if (!company) return [];
    const indicators = [];
    for (const key in indicatorMap) {
      const value = company[key];
      if (value !== null && value !== undefined) {
        indicators.push({
          name: indicatorMap[key],
          value: Number(value),
        });
      }
    }
    return indicators;
  };

  const handleSuggestionClick = (name) => {
    setSearch(name);
    setSuggestions([]);
  };

  const handleYearClick = (year) => {
    if (activeYear === year) {
      // 如果点的是当前展开的，收起
      setActiveYear(null);
    } else {
      setActiveYear(year);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-white p-6 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        <h1 className="text-4xl font-extrabold text-center text-indigo-700">
          🌿 CSR Dashboard
        </h1>

        <div className="flex flex-col items-center mb-8 relative">
          <input
            type="text"
            placeholder="🔍 Search company name..."
            className="w-full max-w-md px-4 py-3 border border-gray-300 rounded-lg shadow focus:outline-none focus:ring focus:ring-indigo-300"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

          {suggestions.length > 0 && (
            <ul className="absolute top-14 w-full max-w-md bg-white border border-gray-300 rounded-lg shadow-lg z-10">
              {suggestions.map((item) => (
                <li
                  key={item.company_id}
                  className="px-4 py-2 hover:bg-indigo-100 cursor-pointer text-left"
                  onClick={() => handleSuggestionClick(item.company_id)}
                >
                  {item.company_id}
                </li>
              ))}
            </ul>
          )}
        </div>

        {selectedCompanyRecords.length === 0 ? (
          <p className="text-center text-gray-600">
            Please enter a valid company name to view sustainability indicators.
          </p>
        ) : (
          <>
            {/* 年份快速跳转 */}
            <div className="flex flex-wrap justify-center gap-4 mb-10">
              {selectedCompanyRecords.map((record) => (
                <button
                  key={record.reporting_year}
                  onClick={() => handleYearClick(record.reporting_year)}
                  className={`px-4 py-2 rounded-full transition ${
                    activeYear === record.reporting_year
                      ? "bg-indigo-700 text-white"
                      : "bg-indigo-500 text-white hover:bg-indigo-600"
                  }`}
                >
                  {record.reporting_year}
                </button>
              ))}
            </div>

            {/* 只显示当前展开的年份 */}
            {selectedCompanyRecords.map((record) => {
              const chartData = buildChartData(record);
              if (record.reporting_year !== activeYear) return null;
              return (
                <div
                  key={record.company_id + record.reporting_year}
                  className="bg-white shadow-lg rounded-xl p-6 space-y-10 mb-10"
                >
                  <h2 className="text-2xl font-bold text-center text-gray-800">
                    📊 {record.company_id} ({record.reporting_year})
                  </h2>

                  <div className="overflow-x-auto">
                    <table className="min-w-full text-center table-auto border">
                      <thead className="bg-indigo-200">
                        <tr>
                          <th className="px-4 py-2 border">Indicator</th>
                          <th className="px-4 py-2 border">Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {chartData.length === 0 ? (
                          <tr>
                            <td colSpan="2" className="px-4 py-6 text-gray-500">
                              No sustainability data found for this year.
                            </td>
                          </tr>
                        ) : (
                          chartData.map((item) => (
                            <tr key={item.name} className="border">
                              <td className="px-4 py-2">{item.name}</td>
                              <td className="px-4 py-2">{item.value}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  {chartData.length > 0 && (
                    <div className="w-full h-[500px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={chartData}
                          margin={{ top: 20, right: 30, left: 20, bottom: 140 }}
                        >
                          <XAxis
                            dataKey="name"
                            angle={-30}
                            textAnchor="end"
                            interval={0}
                          />
                          <YAxis />
                          <Tooltip />
                          <Bar dataKey="value" fill="#4F46E5" radius={[8, 8, 0, 0]}>
                            <LabelList dataKey="value" position="top" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
