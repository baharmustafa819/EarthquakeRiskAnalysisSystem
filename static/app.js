document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("riskForm");
  const districtInput = document.getElementById("district");
  const districtButtons = document.querySelectorAll(".district-tab");
  const selectedTextContainer = document.getElementById("selectedDistrictText");
  const selectedDistrictName = selectedTextContainer.querySelector("strong");
  const resultCard = document.getElementById("resultCard");
  const submitBtn = document.getElementById("submitBtn");

  const scoreText = document.getElementById("scoreText");
  const riskBadge = document.getElementById("riskBadge");
  const recommendationText = document.getElementById("recommendationText");
  const ageRisk = document.getElementById("ageRisk");
  const floorRisk = document.getElementById("floorRisk");
  const soilRisk = document.getElementById("soilRisk");

  const map = L.map("map").setView([41.0082, 28.9784], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let marker = null;
  const coordinateCache = {};

  async function focusDistrictOnMap(district) {
    if (!district) return;

    if (coordinateCache[district]) {
      const { lat, lon } = coordinateCache[district];
      map.setView([lat, lon], 13);
      if (marker) marker.remove();
      marker = L.marker([lat, lon]).addTo(map).bindPopup(`<strong>${district}</strong>`).openPopup();
      return;
    }

    try {
      const query = encodeURIComponent(`${district}, Istanbul, Turkey`);
      const geoResp = await fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=json&limit=1`);

      if (!geoResp.ok) throw new Error("Harita servisine ulaşılamadı.");

      const geoData = await geoResp.json();
      if (!geoData.length) return;

      const lat = Number(geoData[0].lat);
      const lon = Number(geoData[0].lon);

      coordinateCache[district] = { lat, lon };
      map.setView([lat, lon], 13);

      if (marker) marker.remove();
      marker = L.marker([lat, lon]).addTo(map).bindPopup(`<strong>${district}</strong>`).openPopup();
    } catch (error) {
      console.error("Harita yükleme hatası:", error);
    }
  }

  districtButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      districtButtons.forEach(btn => btn.classList.remove("active"));
      button.classList.add("active");

      const district = button.dataset.district;
      districtInput.value = district;

      selectedDistrictName.textContent = district;
      selectedTextContainer.classList.remove("d-none");

      await focusDistrictOnMap(district);
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!districtInput.value) {
      alert("Lütfen harita üzerinden veya listeden bir ilçe seçin!");
      return;
    }

    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Hesaplanıyor...";

    const payload = {
      district: districtInput.value,
      buildingAge: Number(document.getElementById("buildingAge").value),
      floors: Number(document.getElementById("floors").value),
    };

    try {
      const response = await fetch("/api/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        alert(data.error || "Hesaplama sırasında hata oluştu.");
        return;
      }

      scoreText.textContent = data.totalScore;
      recommendationText.textContent = data.recommendation;
      ageRisk.textContent = data.breakdown.buildingAgeRisk + " Puan";
      floorRisk.textContent = data.breakdown.floorRisk + " Puan";
      soilRisk.textContent = data.breakdown.soilRisk + " Puan";

      const riskLevelInfo = data.level.toLowerCase();
      riskBadge.className = "badge fs-6 mb-3 p-2";

      if (riskLevelInfo.includes("dusuk") || riskLevelInfo.includes("düşük")) {
        riskBadge.classList.add("bg-success");
      } else if (riskLevelInfo.includes("profesyonel")) {
        riskBadge.classList.add("bg-warning", "text-dark");
      } else {
        riskBadge.classList.add("bg-danger");
      }

      riskBadge.textContent = data.level;
      resultCard.classList.remove("d-none");
      resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (error) {
      console.error("API Bağlantı Hatası:", error);
      alert("Sunucuya bağlanılamadı. Backend'in (Python) çalıştığından emin ol.");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = originalText;
    }
  });
});