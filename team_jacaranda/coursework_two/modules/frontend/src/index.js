// src/index.js
import React from "react";
import ReactDOM from "react-dom";
import App from "./App"; // 导入App组件
import "./index.css"; // 引入全局样式文件

// 将App组件渲染到id为root的DOM元素中
ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById("root")
);
