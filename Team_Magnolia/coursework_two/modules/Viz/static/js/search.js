let timer = null;
const searchBox = document.getElementById('search-box');
const resultList = document.getElementById('search-result');
const selectedForm = document.getElementById('selected-form');
const selectedList = document.getElementById('selected-list');

if(searchBox){
  searchBox.addEventListener('input', function() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      doSearch(searchBox.value);
    },300);
  });
}

function doSearch(q){
  if(!q){
    resultList.style.display='none';
    return;
  }
  fetch(`/api/search_companies?q=${encodeURIComponent(q)}`)
    .then(r=>r.json())
    .then(data=>{
      if(data.length==0){
        resultList.innerHTML="<li class='list-group-item'>No match</li>";
        resultList.style.display='block';
      } else {
        resultList.innerHTML='';
        data.forEach(item=>{
          const li=document.createElement('li');
          li.className="list-group-item";
          li.style.cursor="pointer";
          li.textContent=`${item.company_name} (${item.ticker})`;
          li.addEventListener('click', ()=> selectCompany(item));
          resultList.appendChild(li);
        });
        resultList.style.display='block';
      }
    })
    .catch(err=>console.error(err));
}

function selectCompany(item){
  const val= `${item.company_name}|${item.ticker}|${item.isin}`;

  // hidden input
  const hid= document.createElement('input');
  hid.type='hidden';
  hid.name='company_tickers';
  hid.value= val;
  selectedForm.appendChild(hid);

  // div
  const div= document.createElement('div');
  div.className="text-white mt-1";
  div.textContent=`${item.company_name} (${item.ticker})`;
  // remove on click
  div.onclick=()=>{
    selectedForm.removeChild(hid);
    selectedList.removeChild(div);
  };
  selectedList.appendChild(div);

  searchBox.value='';
  resultList.style.display='none';
  resultList.innerHTML='';
}
