# coursework_two/visualisation/app.py
# -*- coding: utf-8 -*-
"""
Flask dashboard for CSR-ESG records
──────────────────────────────────────────────────────────────────────────────
* Reads documents from **MongoDB → csr_extraction.csr_reports** (localhost:27019)
* Provides four views:
*       1) Quick Dashboard            GET  /
*       2) Data-check page            GET  /datacheck
*       3) Search (table view)        GET  /search
*       4) Basic charting API         GET  /dataviz  + AJAX helpers
*
"""

import itertools
import os
from typing import List, Dict, Any

from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient

# ────────────────────────────────────────────────────────────────────────────
# 0) 读取 MongoDB 中的全部文档 → data (list[dict])
# ────────────────────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27019")
MONGO_DB  = os.getenv("MONGO_DB",  "csr_extraction")
MONGO_COLL = os.getenv("MONGO_COLL", "csr_reports")

client = MongoClient(MONGO_URI)
coll   = client[MONGO_DB][MONGO_COLL]

# 只排除 _id 以便直接 JSON 序列化；其余字段全部保留
data: List[Dict[str, Any]] = list(coll.find({}, {"_id": 0}))

if not data:
    raise RuntimeError(
        f"Collection '{MONGO_DB}.{MONGO_COLL}' is empty – "
        "please ingest some reports first."
    )

# ────────────────────────────────────────────────────────────────────────────
# 1) 构建 “Thematic Area → 指标(id) 列表” 映射（页面下拉菜单用）
# ────────────────────────────────────────────────────────────────────────────
thematic_area_choices: Dict[str, List[str]] = {}
for rec in data:
    area = rec.get("thematic_area", "Unknown")
    ind  = rec.get("indicator_id")
    if not ind:
        continue
    thematic_area_choices.setdefault(area, [])
    if ind not in thematic_area_choices[area]:
        thematic_area_choices[area].append(ind)

# ────────────────────────────────────────────────────────────────────────────
# 2) Flask 应用 & 路由
# ────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# ===============  (1) DASHBOARD  首页  ======================================
@app.route("/", methods=["GET"])
def index() -> str:
    available_years = [str(y) for y in range(2017, 2026)]
    esg_choices = list(itertools.chain.from_iterable(thematic_area_choices.values()))
    company_list = sorted({rec.get("company_name", "") for rec in data})
    return render_template(
        "index.html",
        available_years=available_years,
        esg_choices=esg_choices,
        company_list=company_list
    )


@app.route("/api/dashboard_data", methods=["POST"])
def dashboard_data():
    body = request.json or {}
    company = body.get("company")
    metric  = body.get("metric")
    selected_years = list(map(int, body.get("years", [])))

    result_years, result_values = [], []

    for rec in data:
        if rec.get("company_name") == company and rec.get("indicator_id") == metric:
            rec_years = rec.get("years", [])
            nums      = rec.get("values_numeric", [])
            for y, v in zip(rec_years, nums):
                if y in selected_years:
                    result_years.append(y)
                    result_values.append(v)
            break

    return jsonify({
        "years":   result_years,
        "values":  result_values,
        "summary": f"Performance of {company} on {metric}."
    })

# ===============  (2) DATACHECK  公司覆盖情况  ===============================
@app.route("/datacheck", methods=["GET"])
def datacheck_page():
    company_status = [
        {
            "company_name": c,
            "has_report": any(rec.get("company_name") == c for rec in data)
        }
        for c in sorted({rec.get("company_name", "") for rec in data})
    ]
    return render_template("datacheck.html", company_status=company_status)

# ===============  (3) SEARCH  查询表格 ======================================
@app.route("/search", methods=["GET"])
def search_page():
    years = [str(y) for y in range(2017, 2026)]
    return render_template(
        "search.html",
        available_years=years,
        thematic_area_choices=thematic_area_choices,
        search_results=[]
    )


@app.route("/api/search_companies", methods=["GET"])
def api_search_companies():
    q = request.args.get("q", "").lower()
    names = {
        rec.get("company_name", "")
        for rec in data
        if q and q in rec.get("company_name", "").lower()
    }
    return jsonify([{"company_name": n} for n in sorted(names)])


@app.route("/search_results", methods=["POST"])
def search_results():
    companies = request.form.getlist("company_tickers")
    years     = list(map(int, request.form.getlist("selected_years")))
    metrics   = request.form.getlist("selected_metrics")

    results = []
    for rec in data:
        if rec.get("company_name") not in companies:
            continue
        mid = rec.get("indicator_id")
        if mid not in metrics:
            continue

        row = {
            "company_name":  rec.get("company_name"),
            "thematic_area": rec.get("thematic_area"),
            "esg_metric":    mid,
            "record_type":   rec.get("record_type", "metric")
        }

        if row["record_type"] == "metric":
            ry, nums, txts = (
                rec.get("years", []),
                rec.get("values_numeric", []),
                rec.get("values_text", []),
            )
            for y in years:
                if y in ry:
                    i   = ry.index(y)
                    val = nums[i] if i < len(nums) and nums[i] is not None else (
                          txts[i] if i < len(txts) else None)
                else:
                    val = None
                row[f"year_{y}"] = val
            row.update(goal_text="-", progress_text="-",
                       target_value="-", target_unit="-")
        else:  # target
            row.update(
                goal_text     = rec.get("goal_text", "-"),
                progress_text = rec.get("progress_text", "-"),
                target_value  = rec.get("target_value", "-"),
                target_unit   = rec.get("target_unit", "-"),
            )
            for y in years:
                row[f"year_{y}"] = "-"

        results.append(row)

    return render_template(
        "search.html",
        available_years=[str(y) for y in range(2017, 2026)],
        thematic_area_choices=thematic_area_choices,
        search_results=results
    )

# ===============  (4) DATA-VIZ  图表页面 & API ===============================
@app.route("/dataviz", methods=["GET"])
def dataviz_page():
    years       = [str(y) for y in range(2017, 2026)]
    esg_choices = list(itertools.chain.from_iterable(thematic_area_choices.values()))
    chart_types = ["line", "bar", "pie"]
    return render_template(
        "data_viz.html",
        all_years  = years,
        esg_choices= esg_choices,
        chart_types= chart_types
    )


@app.route("/api/dv_search_companies", methods=["GET"])
def dv_search_companies():
    q = request.args.get("q", "").lower()
    names = {
        rec.get("company_name", "")
        for rec in data
        if q and q in rec.get("company_name", "").lower()
    }
    return jsonify([{"company_name": n} for n in sorted(names)])


@app.route("/api/dv_chart_data", methods=["POST"])
def dv_chart_data():
    body        = request.json or {}
    comp_list   = body.get("company_list", [])
    year_list   = list(map(int, body.get("year_list", [])))
    metric_list = body.get("metric_list", [])
    chart_type  = body.get("chart_type", "line")

    if not (comp_list and year_list and metric_list):
        return jsonify({"chart_type": chart_type, "data": {}})

    chart_data = {}
    for rec in data:
        name   = rec.get("company_name")
        metric = rec.get("indicator_id")
        if name not in comp_list or metric not in metric_list:
            continue

        key       = f"{name}|{metric}"
        year_vals = {}
        for y in year_list:
            val = 0
            if rec.get("record_type") == "metric":
                ry, nums, txts = (
                    rec.get("years", []),
                    rec.get("values_numeric", []),
                    rec.get("values_text", []),
                )
                if y in ry:
                    i = ry.index(y)
                    val = nums[i] if i < len(nums) and nums[i] is not None else (
                          txts[i] if i < len(txts) else 0)
            year_vals[y] = val or 0
        chart_data[key] = year_vals

    return jsonify({"chart_type": chart_type, "data": chart_data})

# ────────────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 所有路由注册完毕后再启动
    app.run(debug=True, port=5000)
