var map = L.map('map').setView([23.5, 121.5], 8);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

function loadMarkers(){
  fetch('/markers')
    .then(r => r.json())
    .then(arr => {
      arr.forEach(m => addMarkerToMap(m));
    });
}

function addMarkerToMap(m) {
  var marker = L.marker([m.lat, m.lng]).addTo(map);
  marker.on('click', function(){
    openUpdateOverlay(m);
  });

  var html = `<div><strong>初始：</strong><br>${m.text || ""}</div>`;
  if (m.image_url) {
    html += `<div><img src="${m.image_url}" style="max-width:200px;"></div>`;
  }
  html += `<hr><div style="font-size:0.9em; color:#555;">(點圖查看/新增更新)</div>`;
  marker.bindPopup(html);
}

map.on('click', function(e){
  var px = map.latLngToContainerPoint(e.latlng);
  var form = document.getElementById('formPopup');
  form.style.left = px.x + 'px';
  form.style.top = px.y + 'px';
  form.style.display = 'block';
  document.getElementById('lat').value = e.latlng.lat;
  document.getElementById('lng').value = e.latlng.lng;
});

document.getElementById('cancelBtn').onclick = function(){
  document.getElementById('formPopup').style.display = 'none';
};

document.getElementById('markerForm').onsubmit = function(evt){
  evt.preventDefault();
  var fd = new FormData(this);
  fetch('/markers', {
    method: 'POST',
    body: fd
  }).then(r => r.json())
    .then(m => {
      addMarkerToMap(m);
      document.getElementById('formPopup').style.display = 'none';
      this.reset();
    })
    .catch(e => {
      console.error(e);
      alert("上傳失敗");
    });
};

function openUpdateOverlay(m) {
  // 建 overlay 等同之前版本
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
    <h3>標記更新 / 歷史</h3>
    <div id="hist"></div><hr>
    <textarea id="upd_text" rows="3" cols="40" placeholder="輸入描述"></textarea><br>
    <input type="file" id="upd_image" accept="image/*"><br>
    <button id="upd_submit">送出更新</button>
    <button id="upd_cancel">取消</button>
  `;

  overlay.appendChild(box);
  document.body.appendChild(overlay);

  // 顯示主表資料作為初始紀錄
  var hist = box.querySelector('#hist');
  hist.innerHTML = `<div style="font-weight:bold;">（初始）</div>
    <div>${m.text || ""}</div>
    ${m.image_url ? `<div><img src="${m.image_url}" style="max-width:200px;"></div>` : ""}<hr>`;

  // 取得更新歷史
  fetch(`/markers/${m.id}/updates`)
    .then(r => r.json())
    .then(upds => {
      upds.forEach(u => {
        var e = `<div>
          <div style="font-size:0.9em; color:#444;">${u.updated_at}</div>
          <div>${u.text || ""}</div>
          ${u.image_url ? `<div><img src="${u.image_url}" style="max-width:200px;"></div>` : ""}
          <hr>
        </div>`;
        hist.innerHTML += e;
      });
    });

  box.querySelector('#upd_cancel').onclick = function(){
    document.body.removeChild(overlay);
  };

  box.querySelector('#upd_submit').onclick = function(){
    var newText = box.querySelector('#upd_text').value;
    var newImage = box.querySelector('#upd_image').files[0];
    var fd2 = new FormData();
    fd2.append('text', newText);
    if (newImage) fd2.append('image', newImage);
    fetch(`/markers/${m.id}/updates`, {
      method: 'POST',
      body: fd2
    }).then(r => r.json())
      .then(ret => {
        alert("更新成功");
        document.body.removeChild(overlay);
        // 重新載入地圖
        map.eachLayer(l => {
          if (l instanceof L.Marker) {
            map.removeLayer(l);
          }
        });
        loadMarkers();
      })
      .catch(e => {
        console.error(e);
        alert("更新失敗");
      });
  };
}

// 初次載入
loadMarkers();
