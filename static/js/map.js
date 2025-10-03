var map = L.map('map').setView([23.5, 121.5], 8);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  // maxZoom: 19,
  maxZoom: 18,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// 載入所有 marker
function loadMarkers() {
  fetch('/markers')
    .then(res => res.json())
    .then(data => {
      data.forEach(m => {
        addMarkerToMap(m);
      });
    });
}

// 加入 marker 並綁定點擊展開 popup / 更新功能
function addMarkerToMap(m) {
  var marker = L.marker([m.lat, m.lng]).addTo(map);

  // 在 click 時動作，而不是直接在 popup HTML 呼叫 openUpdateForm
  marker.on('click', function() {
    openUpdateOverlay(m);
  });

  // 初始 popup 可顯示基本資料 + 提示可以點擊查看更新
  var popupHtml = `<div>
      <strong>初始描述：</strong><br>
      ${m.text || ""}<br>
  `;
  if (m.image_url) {
    popupHtml += `<div><img src="${m.image_url}" style="max-width:200px;"></div>`;
  }
  popupHtml += `<hr><div style="font-size:0.9em; color:#555;">(點此標記可查看 / 新增更新)</div></div>`;
  marker.bindPopup(popupHtml);
}

// 點 marker 時開 overlay 顯示歷史 + 更新表單
function openUpdateOverlay(m) {
  // 建 overlay
  var overlay = document.createElement('div');
  overlay.style.position = 'fixed';
  overlay.style.left = '0'; overlay.style.top = '0';
  overlay.style.width = '100%'; overlay.style.height = '100%';
  overlay.style.background = 'rgba(0,0,0,0.5)';
  overlay.style.zIndex = '10000';

  var box = document.createElement('div');
  box.style.background = 'white';
  box.style.margin = '50px auto';
  box.style.padding = '20px';
  box.style.maxHeight = '80%';
  box.style.overflow = 'auto';
  box.style.width = '400px';

  box.innerHTML = `
    <h3>標記更新 / 歷史紀錄</h3>
    <div id="hist"></div>
    <hr>
    <div>
      <textarea id="upd_text" placeholder="輸入描述" rows="3" cols="40"></textarea>
    </div>
    <div>
      <input type="file" id="upd_image" accept="image/*">
    </div>
    <div style="margin-top: 10px;">
      <button id="upd_submit">送出更新</button>
      <button id="upd_cancel">取消</button>
    </div>
  `;

  overlay.appendChild(box);
  document.body.appendChild(overlay);

  // 顯示初始資料 + 歷史更新
  var histDiv = box.querySelector('#hist');
  histDiv.innerHTML = `<h4>歷史紀錄：</h4>`;
  // 初始描述
  histDiv.innerHTML += `<div>
      <div style="font-weight:bold;">（初始）</div>
      <div>${m.text || ""}</div>
      ${m.image_url ? `<div><img src="${m.image_url}" style="max-width:200px;"></div>` : ""}
      <hr>
  </div>`;

  // 取得其他更新
  fetch(`/markers/${m.id}/updates`)
    .then(res => res.json())
    .then(upds => {
      upds.forEach(u => {
        var e = `<div>
          <div style="font-size:0.9em; color:#444;">${u.updated_at}</div>
          <div>${u.text || ""}</div>
          ${u.image_url ? `<div><img src="${u.image_url}" style="max-width:200px;"></div>` : ""}
          <hr>
        </div>`;
        histDiv.innerHTML += e;
      });
    });

  box.querySelector('#upd_cancel').addEventListener('click', function(){
    document.body.removeChild(overlay);
  });

  box.querySelector('#upd_submit').addEventListener('click', function(){
    var newText = box.querySelector('#upd_text').value;
    var newImage = box.querySelector('#upd_image').files[0];
    var fd = new FormData();
    fd.append('text', newText);
    if (newImage) {
      fd.append('image', newImage);
    }
    fetch(`/markers/${m.id}/updates`, {
      method: 'POST',
      body: fd
    })
    .then(res => res.json())
    .then(ret => {
      alert('更新成功');
      document.body.removeChild(overlay);
      // 重新載入整個地圖標記（簡單做法）
      map.eachLayer(function (layer) {
        if (layer instanceof L.Marker) {
          map.removeLayer(layer);
        }
      });
      loadMarkers();
    })
    .catch(err => {
      console.error('更新失敗', err);
      alert('更新失敗');
    });
  });
}

// 新增標記表單顯示 / 提交
map.on('click', function(e) {
  var px = map.latLngToContainerPoint(e.latlng);
  var formDiv = document.getElementById('formPopup');
  formDiv.style.left = px.x + 'px';
  formDiv.style.top = px.y + 'px';
  formDiv.style.display = 'block';
  document.getElementById('lat').value = e.latlng.lat;
  document.getElementById('lng').value = e.latlng.lng;
});

document.getElementById('markerForm').addEventListener('submit', function(evt) {
  evt.preventDefault();
  var form = evt.target;
  var formData = new FormData(form);
  fetch('/markers', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(m => {
    addMarkerToMap(m);
    document.getElementById('formPopup').style.display = 'none';
    form.reset();
  })
  .catch(err => {
    console.error('上傳失敗', err);
    alert('上傳失敗');
  });
});

document.getElementById('cancelBtn').addEventListener('click', function() {
  document.getElementById('formPopup').style.display = 'none';
});

// 頁面載入時執行
loadMarkers();
