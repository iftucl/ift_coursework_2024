// src/App.js

// npm install
// npm run build
// npm start

import React, { useEffect, useState } from "react";
import axios from "axios";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from "recharts";
import { AcademicCapIcon } from '@heroicons/react/solid';  // For Heroicons v1


function App() {
  const [reports, setReports] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredCompanies, setFilteredCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState("3M Company");
  const [selectedYear, setSelectedYear] = useState("");
  const [selectedReports, setSelectedReports] = useState([]);
  const [selectedIndicator, setSelectedIndicator] = useState("");
  const [searchClicked, setSearchClicked] = useState(true);
  const [viewMode, setViewMode] = useState("chart");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [indicatorData, setIndicatorData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [sourceInfo, setSourceInfo] = useState(null);

  const baseURL = "https://csr.jacaranda.ngrok.app";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [reportsRes, indicatorsRes] = await Promise.all([
          axios.get(`${baseURL}/reports`),
          axios.get(`${baseURL}/indicators/search`),
        ]);
        setReports(reportsRes.data);
        setIndicators(indicatorsRes.data);
      } catch (err) {
        console.error(err);
        setError("Failed to fetch data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [baseURL]);

  const handleSearchClick = async (customCompany = selectedCompany, customYear = selectedYear) => {
    if (customCompany && customYear) {
      setSearchClicked(true);
      try {
        const res = await axios.get(`${baseURL}/data/search`, {
          params: {
            security: customCompany,
            report_year: customYear,
          },
        });
  
        const validData = res.data
          .filter(d => d.value_standardized && !isNaN(d.value_standardized))
          .map(d => ({
            name: d.indicator_name,
            value: Number(d.value_standardized),
            unit: d.unit_standardized || "",
            source_excerpt: d.source_excerpt,
            pdf_page: d.pdf_page,
          }));
  
        setIndicatorData(validData);
      } catch (error) {
        console.error("Error fetching indicator data:", error);
        setIndicatorData([]);
      }
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (reports.length > 0) {
      const availableYears = reports
        .filter(r => r.security === "3M Company")
        .map(r => r.report_year);
      if (availableYears.length > 0) {
        const latestYear = Math.max(...availableYears);
        setSelectedYear(latestYear);
        handleSearchClick("3M Company", latestYear);
      }
    }
  }, [reports]);
  

  const companyList = [...new Set(reports.map(r => r.security))];

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    if (value.trim() === "") {
      setFilteredCompanies([]);
    } else {
      const matched = companyList.filter(c =>
        c.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredCompanies(matched);
    }
    setSearchClicked(false);
  };

  const handleCompanySelect = (company) => {
    setSelectedCompany(company);
    setSearchTerm(company);
    setFilteredCompanies([]);
    setSelectedYear("");
    setSelectedReports([]);
    setSearchClicked(false);
    setSelectedIndicator("");
    setTrendData([]);
  };

  const handleYearChange = (e) => {
    setSelectedYear(e.target.value);
    setSelectedReports([]);
    setSearchClicked(false);
  };  

  const handleIndicatorSelect = async (indicatorName) => {
    setSelectedIndicator(prev => (prev === indicatorName ? "" : indicatorName));
    if (selectedCompany && indicatorName) {
      try {
        const res = await axios.get(`${baseURL}/data/search`, {
          params: {
            security: selectedCompany,
            indicator_name: indicatorName,
          },
        });

        const actualPoints = res.data
          .filter(d => d.value_standardized && d.report_year)
          .map(d => ({
            year: d.report_year,
            actual: Number(d.value_standardized),
          }));

        setTrendData(actualPoints.sort((a, b) => a.year - b.year));
      } catch (err) {
        console.error("Error fetching trend:", err);
        setTrendData([]);
      }
    } else {
      setTrendData([]);
    }
  };

  const handleReportSelect = (report) => {
    if (selectedReports.includes(report)) {
      setSelectedReports(selectedReports.filter(r => r !== report));
    } else {
      setSelectedReports([...selectedReports, report]);
    }
  };
  const downloadSelectedReports = () => {
    if (selectedReports.length === 0) return;

    const csvContent = selectedReports.map(r =>
      `${r.security},${r.report_year},${r.indicator_name},${r.report_url}`
    ).join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedCompany || "reports"}_${selectedYear || "all"}.csv`;
    a.click();
  };

  const handleHoverIndicator = async (item) => {
    if (!selectedCompany || !selectedYear || !item.name) return;

    try {
      const res = await axios.get(`https://csr.jacaranda.ngrok.app/data/search`, {
        params: {
          security: selectedCompany,
          report_year: selectedYear,
          indicator_name: item.name,
        },
      });

      if (res.data.length > 0) {
        const firstMatch = res.data[0];
        setSourceInfo({
          pdf_page: firstMatch.pdf_page || "N/A",
          source_excerpt: firstMatch.source_excerpt || [],
        });
      } else {
        setSourceInfo({
          pdf_page: "N/A",
          source_excerpt: [{ text: "No data available for selected year." }],
        });
      }
    } catch (error) {
      console.error("Error fetching indicator source info:", error);
      setSourceInfo({
        pdf_page: "N/A",
        source_excerpt: [{ text: "Error fetching source." }],
      });
    }
  };

  const clearSourceInfo = () => {
    setSourceInfo(null);
  };

  const availableYears = selectedCompany
    ? [...new Set(reports.filter(r => r.security === selectedCompany).map(r => r.report_year))].sort()
    : [];
      
  const filteredReports = searchClicked
    ? reports.filter((report) => {
      const matchCompany = selectedCompany ? report.security === selectedCompany : true;
      const matchYear = selectedYear ? report.report_year === Number(selectedYear) : true;
      return matchCompany && matchYear;
    })
  : [];


  if (loading) return <div className="loading-spinner">Loading...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;

  return (
    <div className="h-screen bg-white flex flex-col">
      <header className="bg-white border-b-4 border-green-900 p-4 shadow-md flex items-center gap-2">
        <AcademicCapIcon className="w-8 h-8 text-green-900" /> {/* The icon */}
        <h1 className="text-3xl font-bold text-green-900 text-center">CSR DATA</h1>
      </header>
      <main className="flex-1 grid grid-cols-12 gap-6 p-6 bg-gray-50">
        {/* 左栏开始 */}
        <section className="col-span-3 border-2 border-green-900 rounded-xl p-4 bg-white shadow-lg">
          <h3 className="text-xl font-semibold text-green-900 mb-4">CSR INDICATOR</h3>
          <div className="h-[calc(100vh-14rem)] overflow-y-auto scrollbar-custom space-y-2">
            {indicators.map((indicator, index) => (
              <label
                key={index}
                className="flex items-center p-2 hover:bg-green-50 rounded-lg cursor-pointer transition-colors"
              >
                <input
                  type="checkbox"
                  className="w-5 h-5 text-green-900 border-2 border-green-900 rounded mr-2"
                  checked={selectedIndicator === indicator.indicator_name}
                  onChange={() => handleIndicatorSelect(indicator.indicator_name)}
                />
                <span className="text-gray-700">{indicator.indicator_name}</span>
              </label>
            ))}
          </div>
        </section>

        {/* middle */}
        <div className="col-span-6 flex flex-col gap-6">
          <section className="border-2 border-green-900 rounded-xl p-4 bg-white shadow-lg">
            <h3 className="text-xl font-semibold text-green-900 mb-4">Search Company Data</h3>
            <div className="flex gap-4 items-center mb-6">
              <div className="relative flex-1">
                <input
                  type="text"
                  className="w-full h-12 border-2 border-green-900 rounded-lg p-3 focus:ring-2 focus:ring-green-500"
                  placeholder="Enter company name..."
                  value={searchTerm}
                  onChange={handleSearchChange}
                />
                {filteredCompanies.length > 0 && (
                  <div className="absolute inset-x-0 top-16 max-h-60 overflow-y-auto bg-white border-2 border-green-900 rounded-lg shadow-lg z-10 scrollbar-custom">
                    {filteredCompanies.map((company, index) => (
                      <div
                        key={index}
                        className="p-3 hover:bg-green-50 cursor-pointer border-b border-green-100"
                        onClick={() => handleCompanySelect(company)}
                      >
                        <span className="text-gray-700">{company}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* year */}
              <div className="w-40">
                <select
                  className="w-full h-12 border-2 border-green-900 rounded-lg p-3 focus:ring-2 focus:ring-green-500"
                  value={selectedYear}
                  onChange={handleYearChange}
                  disabled={!selectedCompany}
                >
                  <option value="">Select Year</option>
                  {availableYears.map((year) => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </div>

              {/* Searchbutton */}
              <button
                onClick={() => handleSearchClick(selectedCompany, selectedYear)}
                className="h-12 bg-green-900 text-white px-4 py-2 rounded-lg hover:bg-green-800 transition-colors"
              >
                Search
              </button>
            </div>

            {/* table/chart */}
            {searchClicked && (
              <>
                <div className="flex gap-4 mb-4">
                  <button
                    className={`px-4 py-2 rounded-lg ${viewMode === "chart" ? "bg-green-900 text-white" : "bg-green-100 text-green-900"}`}
                    onClick={() => setViewMode("chart")}
                  >
                     Chart
                  </button>
                  <button
                    className={`px-4 py-2 rounded-lg ${viewMode === "table" ? "bg-green-900 text-white" : "bg-green-100 text-green-900"}`}
                    onClick={() => setViewMode("table")}
                  >
                     Table
                  </button>
                </div>

                <div>
                  {indicatorData.length === 0 ? (
                    <div className="text-center text-red-500">No indicator data found.</div>
                  ) : (
                    viewMode === "chart" ? (
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={indicatorData}>
                          <XAxis dataKey="name" interval={0} angle={0} textAnchor="end" height={100} />
                          <YAxis domain={[0, dataMax => dataMax * 1.2]} />
                          <Tooltip />
                          <Bar dataKey="value" fill="#004d40" barSize={40} minPointSize={5} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full bg-white border border-green-900">
                          <thead className="bg-green-100">
                            <tr>
                              <th className="py-2 px-4 border">Indicator</th>
                              <th className="py-2 px-4 border">Value</th>
                              <th className="py-2 px-4 border">Unit</th>
                            </tr>
                          </thead>
                          <tbody>
                            {indicatorData.map((item, index) => (
                              <tr
                                key={index}
                                className="border-t hover:bg-green-50 cursor-pointer"
                                onClick={() => handleHoverIndicator(item)}
                              >
                                <td className="py-2 px-4 border">{item.name}</td>
                                <td className="py-2 px-4 border">{item.value}</td>
                                <td className="py-2 px-4 border">{item.unit}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )
                  )}
                </div>
              </>
            )}
            {/* line*/}
            {selectedIndicator && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-green-900 mb-2">Trend of {selectedIndicator}</h3>
                {trendData.length === 0 ? (
                  <div className="text-red-500">No trend data available.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={trendData}>
                      <XAxis dataKey="year" />
                      <YAxis domain={[0, dataMax => dataMax * 1.2]} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="actual" name="Actual" stroke="#004d40" />
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            )}

            {/* Source Excerpt */}
            {sourceInfo && (
              <div className="mt-6 p-4 border-2 border-green-400 rounded-lg bg-green-50">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-md font-bold text-green-900">Source Details</h4>
                  <button onClick={clearSourceInfo} className="text-green-900 underline">Clear</button>
                </div>
                <div className="text-sm text-green-700 whitespace-pre-wrap">
                  {sourceInfo.source_excerpt.map((excerpt, idx) => (
                    <p key={idx} className="mb-2">
                      <strong>Page {excerpt.page || "?"}:</strong> {excerpt.text}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </section>
        </div>


        {/* left */}
        <section className="col-span-3 border-2 border-green-900 rounded-xl p-4 bg-white shadow-lg">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-semibold text-green-900">{selectedCompany || "Company"} Reports</h3>
            <button
              onClick={downloadSelectedReports}
              className="bg-green-900 text-white px-4 py-2 rounded-lg hover:bg-green-800 flex items-center transition-colors"
            >
              Download
            </button>
          </div>

          <div className="h-[calc(100vh-14rem)] overflow-y-auto scrollbar-custom space-y-3">
            {filteredReports.map((report, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${selectedReports.includes(report) ? 'bg-green-100' : 'bg-green-50'} border-green-200 hover:shadow-md cursor-pointer`}
                onClick={() => handleReportSelect(report)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-semibold text-green-900">{report.security}</h4>
                    <p className="text-sm text-green-800 mt-1">{report.indicator_name}</p>
                  </div>
                  <span className="text-sm text-green-600">{report.report_year}</span>
                </div>
                <a
                  href={report.report_url}
                  className="mt-3 inline-flex items-center text-green-900 hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View Full Report
                </a>
              </div>
            ))}
          </div>
        </section>

      </main>
    </div>
  );
}

export default App;
