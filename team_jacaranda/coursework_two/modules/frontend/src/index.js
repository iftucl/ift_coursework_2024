// src/index.js
import React from "react";
import ReactDOM from "react-dom/client";  // 使用新的导入路径
import App from "./App"; // 导入App组件
import "./index.css"; // 引入全局样式文件

// 创建一个root并渲染App组件
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
