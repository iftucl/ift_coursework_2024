function renderChart() {
  const selectEl = document.getElementById('company-select');
  const scopeEl = document.getElementById('scope-select');
  const chartTypeEl = document.getElementById('chart-type');

  const scopeChoice = scopeEl.value;
  const chartType = chartTypeEl.value;

  // 收集选中的公司
  const selected = [];
  for (let opt of selectEl.options) {
    if (opt.selected) {
      selected.push(opt.value);
    }
  }
  if (selected.length === 0) {
    alert("Please select at least one company.");
    return;
  }

  fetch('/api/compare_data', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      company_ids: selected,
      chart_type: chartType,
      scope_choice: scopeChoice
    })
  })
  .then(res => res.json())
  .then(data => {
    drawCompareChart(data, chartType, scopeChoice);
  })
  .catch(err => console.error(err));
}

function drawCompareChart(apiResp, chartType, scopeLabel) {
  // apiResp = { data: { "CompanyName": { "2015": val, "2016": val, ...}, ... } }
  const ctx = document.getElementById('compareChart').getContext('2d');

  if (window.myChart) {
    window.myChart.destroy();
  }

  const dataResp = apiResp.data || {};
  const labels = new Set();
  const datasets = [];
  let colorIndex = 0;
  const colorPalette = ["#1f77b4","#2ca02c","#ff7f0e","#9467bd","#8c564b","#e377c2"];

  // 收集所有年份
  for (let compName in dataResp) {
    for (let y in dataResp[compName]) {
      labels.add(y);
    }
  }
  const sortedLabels = Array.from(labels).sort();

  // 构造 dataset
  for (let compName in dataResp) {
    const yearObj = dataResp[compName];
    const dataArr = sortedLabels.map(y => yearObj[y] || 0);
    datasets.push({
      label: compName + ` (${scopeLabel})`,
      data: dataArr,
      backgroundColor: colorPalette[colorIndex % colorPalette.length],
      borderColor: colorPalette[colorIndex % colorPalette.length],
      fill: false
    });
    colorIndex++;
  }

  window.myChart = new Chart(ctx, {
    type: chartType,
    data: {
      labels: sortedLabels,
      datasets: datasets
    },
    options: {
      responsive: true,
      plugins: {
        title: {
          display: true,
          text: 'Emissions Data'
        }
      },
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
}
