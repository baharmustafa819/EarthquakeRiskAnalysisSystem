from __future__ import annotations
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, jsonify, render_template, request

# Loglama yapılandırması (Hataları takip etmek için)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "istanbul_district_soil_scores.csv"

@dataclass
class RiskBreakdown:
    total_score: int
    age_risk: int
    floor_risk: int
    soil_risk: int
    level: str
    recommendation: str

def load_soil_scores() -> Dict[str, int]:
    """CSV dosyasından ilçe zemin risk skorlarını yükler."""
    district_scores: Dict[str, int] = {}
    try:
        if not DATA_FILE.exists():
            logger.error(f"Veri dosyası bulunamadı: {DATA_FILE}")
            return {}
            
        with DATA_FILE.open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if "district" in row and "soil_risk" in row:
                    district_scores[row["district"]] = int(row["soil_risk"])
        logger.info(f"{len(district_scores)} ilçe verisi başarıyla yüklendi.")
    except Exception as e:
        logger.error(f"Dosya okunurken hata oluştu: {e}")
    return district_scores

def normalize_district_name(name: str) -> str:
    """Türkçe karakterleri temizler ve ismi standartlaştırır."""
    translation = str.maketrans(
        "çğıöşüÇĞİIÖŞÜ",
        "cgiosucgiiosu"
    )
    return name.strip().translate(translation).lower()

def age_to_risk(age: int) -> int:
    """Bina yaşına göre risk puanı döner."""
    if age <= 5: return 8
    if age <= 15: return 22
    if age <= 30: return 48
    if age <= 45: return 72
    return 90

def floors_to_risk(floors: int) -> int:
    """Kat sayısına göre risk puanı döner."""
    if floors <= 2: return 15
    if floors <= 5: return 35
    if floors <= 8: return 58
    if floors <= 12: return 78
    return 92

def classify(total_score: int) -> Tuple[str, str]:
    """Toplam skora göre risk seviyesi ve tavsiye oluşturur."""
    if total_score < 35:
        return "Düşük Risk", "Binanız göreceli olarak iyi durumda. Periyodik denetim yeterli olabilir."
    if total_score < 65:
        return "Profesyonel İnceleme Gerekli", "Yetkili mühendislik firması ile performans analizi yaptırmanız önerilir."
    return "Acil Güçlendirme Gerekli", "Kapsamlı yapısal inceleme ve güçlendirme planı acilen değerlendirilmelidir."

def compute_score(age: int, floors: int, soil_risk: int) -> RiskBreakdown:
    """Ağırlıklı risk puanını hesaplar."""
    age_risk = age_to_risk(age)
    floor_risk = floors_to_risk(floors)

    total = int(round(age_risk * 0.35 + floor_risk * 0.25 + soil_risk * 0.40))
    level, recommendation = classify(total)

    return RiskBreakdown(
        total_score=total,
        age_risk=age_risk,
        floor_risk=floor_risk,
        soil_risk=soil_risk,
        level=level,
        recommendation=recommendation,
    )

app = Flask(__name__)

SOIL_SCORES = load_soil_scores()
SOIL_SCORES_NORMALIZED = {normalize_district_name(k): v for k, v in SOIL_SCORES.items()}
DISTRICT_CANONICAL_NAMES = {normalize_district_name(k): k for k in SOIL_SCORES.keys()}

@app.route("/")
def index():
    districts: List[str] = sorted(SOIL_SCORES.keys())
    return render_template("index.html", districts=districts)

@app.route("/api/calculate", methods=["POST"])
def calculate():
    payload = request.get_json(silent=True) or {}

    district = str(payload.get("district", "")).strip()
    try:
        age = int(payload.get("buildingAge", 0))
        floors = int(payload.get("floors", 0))
    except ValueError:
        return jsonify({"error": "Lütfen sayısal değerler giriniz."}), 400

    district_key = normalize_district_name(district)
    
    if district_key not in SOIL_SCORES_NORMALIZED:
        return jsonify({"error": "Geçerli bir ilçe seçmelisiniz."}), 400
    if not (0 <= age <= 150):
        return jsonify({"error": "Bina yaşı 0-150 aralığında olmalı."}), 400
    if not (1 <= floors <= 80):
        return jsonify({"error": "Kat sayısı 1-80 aralığında olmalı."}), 400

    soil_risk = SOIL_SCORES_NORMALIZED[district_key]
    canonical_district = DISTRICT_CANONICAL_NAMES[district_key]
    result = compute_score(age=age, floors=floors, soil_risk=soil_risk)

    return jsonify({
        "district": canonical_district,
        "totalScore": result.total_score,
        "level": result.level,
        "recommendation": result.recommendation,
        "breakdown": {
            "buildingAgeRisk": result.age_risk,
            "floorRisk": result.floor_risk,
            "soilRisk": result.soil_risk,
        },
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)