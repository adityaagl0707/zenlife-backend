"""Seeds demo data for ZenLife — mirrors the Sameer Gupta test account from cent.health.

MongoDB-backed (replaces SQLAlchemy/SQLite). Idempotent: skipped if user already exists.
"""
from datetime import datetime
from ..core import mongo


def seed_demo():
    if mongo.User.find_one({"phone": "9999999999"}):
        return  # already seeded

    # ── User ──────────────────────────────────────────────────────────────
    user = {
        "phone": "9999999999",
        "name": "Arjun Mehta",
        "age": 30,
        "gender": "Male",
        "is_active": True,
        "created_at": mongo.now(),
    }
    mongo.User.insert(user)

    # ── Order ─────────────────────────────────────────────────────────────
    order = {
        "booking_id": "Order000034",
        "user_id": user["id"],
        "patient_name": "Arjun Mehta",
        "patient_age": 30,
        "patient_gender": "Male",
        "scan_type": "ZenScan",
        "status": "completed",
        "scan_date": datetime(2025, 6, 18),
        "next_visit": datetime(2026, 6, 18),
        "amount": 27500,
        "created_at": mongo.now(),
    }
    mongo.Order.insert(order)

    # ── Report ────────────────────────────────────────────────────────────
    report = {
        "order_id": order["id"],
        "coverage_index": 90.0,
        "overall_severity": "critical",
        "report_date": datetime(2025, 6, 18),
        "next_visit": datetime(2026, 6, 18),
        "summary": (
            "Critical cardiovascular findings require immediate attention. "
            "Agatston Score of 550 indicates significant coronary artery disease "
            "for a 30-year-old. Immediate cardiologist referral recommended."
        ),
        "is_published": False,
    }
    mongo.Report.insert(report)
    rid = report["id"]

    # ── Organ Scores ──────────────────────────────────────────────────────
    organs = [
        ("Heart Health", "critical", "Urgent Medical Attention", 1, 10, 0, 27, "❤️", 0),
        ("Endocrine & Metabolic Health", "major", "High Health Risk", 0, 2, 7, 19, "⚡", 1),
        ("Liver & Digestive Health", "minor", "Mild Health Concern", 0, 0, 4, 47, "🫁", 2),
        ("Brain & Cognitive Health", "minor", "Mild Health Concern", 0, 0, 4, 42, "🧠", 3),
        ("Kidney & Urinary Health", "minor", "Mild Health Concern", 0, 0, 3, 49, "🫘", 4),
        ("Inflammation & Immune Health", "minor", "Mild Health Concern", 0, 0, 6, 2, "🛡️", 5),
        ("General Health, Blood & Nutrients", "minor", "Mild Health Concern", 0, 0, 4, 41, "🩸", 6),
        ("Reproductive Health", "normal", "Healthy and Stable", 0, 0, 0, 13, "🌿", 7),
        ("Bone, Muscle & Joint Health", "minor", "Mild Health Concern", 0, 0, 3, 22, "🦴", 8),
        ("Lung & Respiratory Health", "normal", "Healthy and Stable", 0, 0, 1, 18, "🫧", 9),
    ]
    for (name, sev, label, crit, maj, minor, norm, icon, ord_n) in organs:
        mongo.OrganScore.insert({
            "report_id": rid,
            "organ_name": name,
            "severity": sev,
            "risk_label": label,
            "critical_count": crit,
            "major_count": maj,
            "minor_count": minor,
            "normal_count": norm,
            "icon": icon,
            "display_order": ord_n,
        })

    # ── Findings ──────────────────────────────────────────────────────────
    findings = [
        ("calcium_score", "Agatston Score", "critical", "550", "0", "",
         "Measure of calcium buildup in coronary arteries via CT scan.",
         "Significant calcium deposition in all major coronary arteries — suggestive of chronic coronary artery disease.",
         "Cardiologist consultation & DSA",
         {"table": [
             {"artery": "LM",  "agatston": 35},
             {"artery": "LCK", "agatston": 85},
             {"artery": "LAD", "agatston": 396},
             {"artery": "RCA", "agatston": 34},
         ]}),
        ("dexa", "Gynoid Fat", "major", "28.7", "<30", "%",
         "Fat stored around the hips, thighs, and buttocks.",
         "Disproportionate gynoid fat storage may affect hormonal and metabolic health.",
         "Resistance training targeting lower body; review with endocrinologist.", None),
        ("dexa", "Visceral Fat Area", "major", "82.4", "<100", "cm²",
         "Fat deposited around internal organs in the abdominal cavity.",
         "Borderline visceral fat area associated with elevated metabolic risk.",
         "Mediterranean diet; 150 min/week aerobic exercise.", None),
        ("blood_urine", "Triglycerides", "minor", "375", "<150", "mg/dL",
         "Blood fats associated with cardiovascular and metabolic risk.",
         "Severely elevated triglycerides — primary dietary cause suspected.",
         "Eliminate refined sugars and fruit juices; omega-3 supplementation.", None),
        ("blood_urine", "HDL Cholesterol", "minor", "41", ">60", "mg/dL",
         "Good cholesterol that protects against heart disease.",
         "Low HDL combined with high triglycerides significantly elevates cardiovascular risk.",
         "Increase physical activity; add niacin-rich foods.", None),
        ("blood_urine", "Homocysteine", "minor", "24.01", "<15", "µmol/L",
         "Amino acid; elevated levels damage blood vessel walls.",
         "Elevated homocysteine is an independent cardiovascular risk factor.",
         "B6, B9, B12 supplementation; methionine-restricted diet.", None),
        ("blood_urine", "Vitamin D", "minor", "18.2", "30-100", "ng/mL",
         "Critical for bone health, immunity, and cardiovascular function.",
         "Deficient Vitamin D levels found.",
         "Vitamin D3 supplement 2000-4000 IU/day; morning sun exposure.", None),
        ("ecg", "Heart Rate", "normal", "72", "60-100", "bpm",
         "Number of heartbeats per minute.", "Normal sinus rhythm.", "No action required.", None),
        ("mri", "Brain MRI", "normal", None, None, None,
         "High-resolution imaging of brain structures.",
         "No acute intracranial abnormality. Age-appropriate parenchymal volume.",
         "Routine annual screening.", None),
        ("lung_scan", "Lung Fields", "normal", None, None, None,
         "CT-based evaluation of lung parenchyma.",
         "Clear lung fields bilaterally. No nodules or consolidation.",
         "Maintain smoke-free lifestyle.", None),
    ]
    for (test_type, name, severity, value, normal_range, unit, desc, clinical, rec, extra) in findings:
        mongo.Finding.insert({
            "report_id": rid,
            "test_type": test_type,
            "name": name,
            "severity": severity,
            "value": value,
            "normal_range": normal_range,
            "unit": unit,
            "description": desc,
            "clinical_findings": clinical,
            "recommendations": rec,
            "extra_data": extra,
        })

    # ── Health Priorities ─────────────────────────────────────────────────
    mongo.HealthPriority.insert({
        "report_id": rid,
        "priority_order": 1,
        "title": "Address Critical Cardiovascular Risk",
        "why_important": (
            "Confirmed coronary artery disease at age 30, combined with severely elevated "
            "triglycerides (375 mg/dL), low HDL (41 mg/dL), and homocysteine at 24.01 µmol/L, "
            "represents the most urgent and life-threatening finding across all systems."
        ),
        "diet_recommendations": [
            "Eliminate all refined sugars, sugary beverages, and fruit juices immediately",
            "Adopt a Mediterranean-style diet rich in olive oil, nuts, fish, and vegetables",
            "Limit saturated fats; avoid trans fats completely",
            "Include omega-3-rich foods: salmon, sardines, flaxseed 3x/week",
        ],
        "exercise_recommendations": [
            "Start with 30-min brisk walks daily for 2 weeks before increasing intensity",
            "Progress to 150 min/week of moderate aerobic activity",
            "Avoid high-intensity exercise until cardiologist clearance",
        ],
        "sleep_recommendations": [
            "Target 7-8 hours of uninterrupted sleep",
            "Sleep apnea screening recommended",
        ],
        "supplement_recommendations": [
            "Omega-3 (EPA+DHA): 2-4g/day",
            "CoQ10: 200mg/day",
            "Vitamin D3: 4000 IU/day",
            "Magnesium glycinate: 400mg at bedtime",
        ],
    })

    mongo.HealthPriority.insert({
        "report_id": rid,
        "priority_order": 2,
        "title": "Metabolic & Hormonal Rebalancing",
        "why_important": (
            "Elevated visceral fat and borderline gynoid fat percentage indicate early metabolic "
            "dysfunction. Combined with high triglycerides, this suggests insulin resistance risk."
        ),
        "diet_recommendations": [
            "Time-restricted eating (16:8 intermittent fasting)",
            "High-protein diet: 1.6-2g protein per kg bodyweight",
            "Low glycemic-index carbohydrates only",
        ],
        "exercise_recommendations": [
            "Add 3x/week resistance training after cardiologist clearance",
            "HIIT sessions 1-2x/week to improve insulin sensitivity",
        ],
        "sleep_recommendations": ["Consistent sleep-wake schedule; avoid screens 1hr before bed"],
        "supplement_recommendations": ["Berberine 500mg 2x/day with meals", "Chromium picolinate 200mcg/day"],
    })

    # ── Consultation Note ─────────────────────────────────────────────────
    mongo.ConsultationNote.insert({
        "report_id": rid,
        "note_type": "doctor",
        "content": (
            "Patient counselled on cardiovascular risk. Immediate referral to cardiologist arranged. "
            "Lifestyle modifications discussed. Follow-up in 3 months."
        ),
        "author": "Dr. Priya Sharma",
        "created_at": mongo.now(),
    })

    print("✅ Demo data seeded for ZenLife (MongoDB)")
