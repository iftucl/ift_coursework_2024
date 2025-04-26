// npm install
// npm run build
// npm start

import React, { useEffect, useState } from "react";
import axios from "axios";

// 定义主App组件
function App() {
  // 状态钩子：用于存储从FastAPI获取的数据
  const [indicators, setIndicators] = useState([]);  // 存储指标数据
  const [data, setData] = useState([]);  // 存储数据项
  const [reports, setReports] = useState([]);  // 存储报告数据

  // 状态钩子：用于存储过滤条件
  const [indicatorFilter, setIndicatorFilter] = useState("");  // 用于指标名称过滤
  const [securityFilter, setSecurityFilter] = useState("");  // 用于证券名称过滤

  // 状态钩子：用于显示加载和错误信息
  const [loading, setLoading] = useState(true); // 数据加载状态
  const [error, setError] = useState(""); // 错误信息

  // FastAPI的基本URL（本地开发环境）
  const baseURL = "https://csr.jacaranda.ngrok.app"; // 替换为你的FastAPI服务地址

  // 使用useEffect钩子获取数据
  useEffect(() => {
    // 获取指标数据
    axios
      .get(`${baseURL}/indicators`)
      .then((res) => {
        setIndicators(res.data);
        console.log("Indicators Data:", res.data);  // 打印返回的 indicators 数据
      })
      .catch((err) => {
        setError("Error fetching indicators data");
        console.error("Error fetching indicators data:", err);
      });

    // 获取数据项
    axios
      .get(`${baseURL}/data`)
      .then((res) => setData(res.data))
      .catch((err) => {
        setError("Error fetching data items");
        console.error("Error fetching data items:", err);
      });

    // 获取报告数据
    axios
      .get(`${baseURL}/reports`)
      .then((res) => setReports(res.data))
      .catch((err) => {
        setError("Error fetching reports");
        console.error("Error fetching reports:", err);
      })
      .finally(() => {
        setLoading(false);  // 无论成功或失败，都表示加载完成
      });
  }, []); // 空依赖数组，表示只在组件首次渲染时执行

  // 如果正在加载数据，显示加载提示
  if (loading) {
    return <div>Loading...</div>;
  }

  // 如果有错误，显示错误信息
  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <div className="p-6 space-y-10">
      {/* 页面标题 */}
      <h1 className="text-3xl font-bold">CSR Reporting Dashboard</h1>

      {/* 指标过滤和展示部分 */}
      <section>
        <h2 className="text-xl font-semibold mb-2">Indicators</h2>
        <input
          className="border p-2 mb-4 w-full"
          placeholder="Filter by indicator name..."
          onChange={(e) => setIndicatorFilter(e.target.value)}  // 监听输入框变化，更新过滤条件
        />
        <ul className="space-y-2">
          {/* 根据指标名称过滤并展示指标数据 */}
          {indicators
            .filter((i) =>
              i.indicator_name.toLowerCase().includes(indicatorFilter.toLowerCase())  // 过滤条件
            )
            .map((i) => (
              <li key={i.indicator_id} className="p-2 border rounded shadow">
                {i.indicator_name} ({i.theme}) - {i.unit}
              </li>
            ))}
        </ul>
      </section>

      {/* 数据项过滤和展示部分 */}
      <section>
        <h2 className="text-xl font-semibold mb-2">Data</h2>
        <input
          className="border p-2 mb-4 w-full"
          placeholder="Filter by security name..."
          onChange={(e) => setSecurityFilter(e.target.value)}  // 监听输入框变化，更新过滤条件
        />
        <ul className="space-y-2">
          {/* 根据证券名称过滤并展示数据项 */}
          {data
            .filter((d) =>
              d.security.toLowerCase().includes(securityFilter.toLowerCase())  // 过滤条件
            )
            .map((d) => (
              <li key={d.data_id} className="p-2 border rounded shadow">
                {d.security} ({d.report_year}) - {d.indicator_name}: {d.value_standardized} {d.unit_standardized}
              </li>
            ))}
        </ul>
      </section>

      {/* 报告展示部分 */}
      <section>
        <h2 className="text-xl font-semibold mb-2">Reports</h2>
        <ul className="space-y-2">
          {/* 展示报告链接 */}
          {reports.map((r) => (
            <li key={r.id} className="p-2 border rounded shadow">
              {r.security} ({r.report_year}) -{" "}
              <a
                href={r.report_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 underline"
              >
                View Report
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default App;
