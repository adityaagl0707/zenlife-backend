"""Parameter definitions for each report section type."""

SECTION_PARAMETERS = {
    "blood": [
        # Glucose / Diabetes
        {"name": "Fasting Blood Glucose", "unit": "mg/dL", "normal": "70–100"},
        {"name": "HbA1c", "unit": "%", "normal": "<5.7"},
        {"name": "Average Blood Glucose", "unit": "mg/dL", "normal": "<117"},
        {"name": "Insulin", "unit": "µIU/mL", "normal": "2.6–24.9"},
        {"name": "Ketone", "unit": "", "normal": "Negative"},
        # Lipid Panel
        {"name": "Total Cholesterol", "unit": "mg/dL", "normal": "<200"},
        {"name": "LDL Cholesterol", "unit": "mg/dL", "normal": "<100"},
        {"name": "HDL Cholesterol", "unit": "mg/dL", "normal": ">50(F) / >40(M)"},
        {"name": "Triglycerides", "unit": "mg/dL", "normal": "<150"},
        {"name": "VLDL Cholesterol", "unit": "mg/dL", "normal": "<30"},
        {"name": "Non-HDL Cholesterol", "unit": "mg/dL", "normal": "<130"},
        {"name": "LDL/HDL Ratio", "unit": "", "normal": "<3.0"},
        {"name": "HDL/LDL Ratio", "unit": "", "normal": ">0.3"},
        {"name": "Total Cholesterol / HDL", "unit": "", "normal": "<5.0"},
        {"name": "Triglycerides / HDL", "unit": "", "normal": "<3.0"},
        {"name": "Lipoprotein (a)", "unit": "mg/dL", "normal": "<30"},
        {"name": "Apolipoprotein B", "unit": "mg/dL", "normal": "<100"},
        {"name": "Homocysteine Levels", "unit": "µmol/L", "normal": "<15"},
        # Liver Function
        {"name": "AST", "unit": "U/L", "normal": "<35"},
        {"name": "ALT", "unit": "U/L", "normal": "<45"},
        {"name": "GGT", "unit": "U/L", "normal": "<55"},
        {"name": "ALP", "unit": "U/L", "normal": "44–147"},
        {"name": "Total Bilirubin", "unit": "mg/dL", "normal": "0.2–1.2"},
        {"name": "Bilirubin Direct", "unit": "mg/dL", "normal": "0–0.3"},
        {"name": "Bilirubin (Indirect)", "unit": "mg/dL", "normal": "0.2–0.9"},
        {"name": "Albumin", "unit": "g/dL", "normal": "3.5–5.0"},
        {"name": "Total Protein", "unit": "g/dL", "normal": "6.0–8.3"},
        {"name": "Globulin", "unit": "g/dL", "normal": "2.0–3.5"},
        {"name": "Serum Albumin/Globulin", "unit": "", "normal": "1.2–2.2"},
        {"name": "AST/ALT Ratio", "unit": "", "normal": "<1"},
        {"name": "Lipase", "unit": "U/L", "normal": "13–60"},
        {"name": "Amylase", "unit": "U/L", "normal": "30–110"},
        # Kidney Function
        {"name": "Creatinine", "unit": "mg/dL", "normal": "0.7–1.2"},
        {"name": "Blood Urea Nitrogen (BUN)", "unit": "mg/dL", "normal": "7–20"},
        {"name": "Urea (Calculated)", "unit": "mg/dL", "normal": "14–43"},
        {"name": "eGFR", "unit": "mL/min/1.73m²", "normal": ">60"},
        {"name": "BUN / Creatinine Ratio", "unit": "", "normal": "10–20"},
        {"name": "Urea/Creatinine Ratio", "unit": "", "normal": "20–40"},
        {"name": "UA (Uric Acid)", "unit": "mg/dL", "normal": "3.5–7.2"},
        # Electrolytes
        {"name": "Sodium", "unit": "mEq/L", "normal": "136–145"},
        {"name": "Potassium", "unit": "mEq/L", "normal": "3.5–5.1"},
        {"name": "Chloride", "unit": "mEq/L", "normal": "98–107"},
        {"name": "Calcium", "unit": "mg/dL", "normal": "8.5–10.5"},
        {"name": "Phosphorus", "unit": "mg/dL", "normal": "2.5–4.5"},
        {"name": "Magnesium, RBC", "unit": "mg/dL", "normal": "4.2–6.8"},
        # Thyroid
        {"name": "TSH", "unit": "µIU/mL", "normal": "0.4–4.0"},
        {"name": "Thyroxine (T4) Free", "unit": "ng/dL", "normal": "0.8–1.8"},
        {"name": "Triiodothyronine (T3) Free", "unit": "pg/mL", "normal": "2.3–4.2"},
        {"name": "TPO", "unit": "IU/mL", "normal": "<35"},
        # CBC
        {"name": "WBC", "unit": "×10³/µL", "normal": "4.5–11.0"},
        {"name": "RBC", "unit": "×10⁶/µL", "normal": "4.5–5.9(M) / 4.0–5.2(F)"},
        {"name": "Hemoglobin", "unit": "g/dL", "normal": "13.5–17.5(M) / 12–16(F)"},
        {"name": "Hematocrit", "unit": "%", "normal": "41–53(M) / 36–46(F)"},
        {"name": "MCV", "unit": "fL", "normal": "80–100"},
        {"name": "MCH", "unit": "pg", "normal": "27–33"},
        {"name": "MCHC", "unit": "g/dL", "normal": "32–36"},
        {"name": "RDW", "unit": "%", "normal": "11.5–14.5"},
        {"name": "RDW-SD", "unit": "fL", "normal": "39–46"},
        {"name": "Platelet Count", "unit": "×10³/µL", "normal": "150–400"},
        {"name": "MPV", "unit": "fL", "normal": "7.5–12.5"},
        {"name": "Plateletcrit (PCT)", "unit": "%", "normal": "0.2–0.4"},
        {"name": "PDW", "unit": "fL", "normal": "9–17"},
        {"name": "PLCR", "unit": "%", "normal": "13–43"},
        {"name": "Neutrophils", "unit": "%", "normal": "50–70"},
        {"name": "Neutrophils - Count", "unit": "×10³/µL", "normal": "1.8–7.7"},
        {"name": "Lymphocytes", "unit": "%", "normal": "20–40"},
        {"name": "Lymphocytes - Count", "unit": "×10³/µL", "normal": "1.0–4.8"},
        {"name": "Monocytes", "unit": "%", "normal": "2–8"},
        {"name": "Monocytes - Count", "unit": "×10³/µL", "normal": "0.2–0.9"},
        {"name": "Eosinophils", "unit": "%", "normal": "1–4"},
        {"name": "Eosinophils - Count", "unit": "×10³/µL", "normal": "0.0–0.45"},
        {"name": "Basophils", "unit": "%", "normal": "0–1"},
        {"name": "Basophils - Count", "unit": "×10³/µL", "normal": "0.0–0.1"},
        {"name": "Immature Granulocytes", "unit": "×10³/µL", "normal": "0–0.03"},
        {"name": "Immature Granulocytes %", "unit": "%", "normal": "0–0.5"},
        {"name": "Nucleated RBC", "unit": "/100 WBC", "normal": "0"},
        {"name": "Nucleated RBC %", "unit": "%", "normal": "0"},
        # Iron Studies
        {"name": "Iron", "unit": "µg/dL", "normal": "60–170"},
        {"name": "TIBC", "unit": "µg/dL", "normal": "250–370"},
        {"name": "UIBC", "unit": "µg/dL", "normal": "111–343"},
        {"name": "Iron % Saturation", "unit": "%", "normal": "20–50"},
        {"name": "Ferritin", "unit": "ng/mL", "normal": "12–300"},
        # Vitamins & Minerals
        {"name": "Vitamin D", "unit": "ng/mL", "normal": "30–100"},
        {"name": "Vitamin B12", "unit": "pg/mL", "normal": "200–900"},
        {"name": "Vitamin A", "unit": "µg/dL", "normal": "30–80"},
        {"name": "Folate (B9)", "unit": "ng/mL", "normal": ">5.9"},
        {"name": "Zinc", "unit": "µg/dL", "normal": "70–120"},
        {"name": "Selenium", "unit": "µg/dL", "normal": "70–150"},
        {"name": "Copper", "unit": "µg/dL", "normal": "70–140"},
        # Hormones
        {"name": "Cortisol", "unit": "µg/dL", "normal": "6–23"},
        {"name": "DHEA", "unit": "µg/dL", "normal": "80–560(M) / 35–430(F)"},
        {"name": "Testosterone", "unit": "ng/dL", "normal": "270–1070(M) / 15–70(F)"},
        {"name": "PSA", "unit": "ng/mL", "normal": "<4.0", "gender": "M"},
        # Inflammation
        {"name": "hs-CRP", "unit": "mg/L", "normal": "<1.0"},
        {"name": "IgE", "unit": "IU/mL", "normal": "<100"},
        # Advanced Cardiovascular
        {"name": "ApoA1", "unit": "mg/dL", "normal": "120–160"},
        {"name": "NT-proBNP", "unit": "pg/mL", "normal": "<125"},
        {"name": "Fibrinogen", "unit": "mg/dL", "normal": "200–400"},
        {"name": "D-Dimer", "unit": "µg/mL FEU", "normal": "<0.5"},
        {"name": "PT / INR", "unit": "INR", "normal": "0.8–1.1"},
        # Hormonal markers
        {"name": "Free Testosterone", "unit": "pg/mL", "normal": "9–30(M) / 0.3–1.9(F)"},
        {"name": "SHBG", "unit": "nmol/L", "normal": "10–57(M) / 18–144(F)"},
        {"name": "Estradiol (E2)", "unit": "pg/mL", "normal": "20–150(M) / varies(F)"},
        {"name": "IGF-1", "unit": "ng/mL", "normal": "100–250"},
        {"name": "Reverse T3", "unit": "ng/dL", "normal": "10–24"},
        {"name": "Anti-TG", "unit": "IU/mL", "normal": "<115"},
        # Metabolic / Insulin
        {"name": "C-Peptide", "unit": "ng/mL", "normal": "0.8–3.5"},
        {"name": "HOMA-IR", "unit": "index", "normal": "<1.5"},
        # Kidney (advanced)
        {"name": "Cystatin C", "unit": "mg/L", "normal": "0.5–1.0"},
        {"name": "PTH", "unit": "pg/mL", "normal": "15–65"},
        # Vitamins (advanced)
        {"name": "Vitamin E", "unit": "mg/L", "normal": "5.5–17"},
        # Tissue & Organ Stress
        {"name": "LDH", "unit": "U/L", "normal": "140–280"},
        {"name": "ESR", "unit": "mm/hr", "normal": "0–20"},
        # Tumour Markers
        {"name": "AFP", "unit": "ng/mL", "normal": "<10"},
        {"name": "CEA", "unit": "ng/mL", "normal": "<3"},
        {"name": "CA-125", "unit": "U/mL", "normal": "<35"},
        # Female-specific hormones & markers
        {"name": "FSH", "unit": "mIU/mL", "normal": "3–10", "gender": "F"},
        {"name": "LH", "unit": "mIU/mL", "normal": "2–15", "gender": "F"},
        {"name": "Progesterone", "unit": "ng/mL", "normal": "0.2–1.5 (follicular) / 5–20 (luteal)", "gender": "F"},
        {"name": "Prolactin", "unit": "ng/mL", "normal": "2–29", "gender": "F"},
        {"name": "AMH", "unit": "ng/mL", "normal": "1.0–3.5", "gender": "F"},
        {"name": "HE4", "unit": "pmol/L", "normal": "<70", "gender": "F"},
        {"name": "CA 15-3", "unit": "U/mL", "normal": "<25", "gender": "F"},
        {"name": "DHEA-S", "unit": "µg/dL", "normal": "35–430", "gender": "F"},
        # Female cervical screening (recorded as part of women's blood/lab panel)
        {"name": "Pap Smear", "unit": "", "normal": "Negative for malignancy", "gender": "F"},
        {"name": "HPV DNA Test", "unit": "", "normal": "Negative", "gender": "F"},
    ],

    "urine": [
        {"name": "Urine Albumin/Creatinine", "unit": "mg/g", "normal": "<30"},
        {"name": "Urinary Microalbumin", "unit": "mg/L", "normal": "<20"},
        {"name": "Urinary Leucocytes", "unit": "", "normal": "Negative"},
        {"name": "Urinary Protein", "unit": "", "normal": "Negative"},
        {"name": "Urine Blood", "unit": "", "normal": "Negative"},
        {"name": "Urinary Glucose", "unit": "", "normal": "Negative"},
        {"name": "Urinary Bilirubin", "unit": "", "normal": "Negative"},
        {"name": "Urine Ketone", "unit": "", "normal": "Negative"},
        {"name": "Creatinine Urine", "unit": "mg/dL", "normal": "40–300"},
        {"name": "Leucocyte Esterase", "unit": "", "normal": "Negative"},
        {"name": "Nitrite", "unit": "", "normal": "Negative"},
        {"name": "Specific Gravity", "unit": "", "normal": "1.005–1.030"},
        {"name": "pH", "unit": "", "normal": "4.5–8.0"},
        {"name": "Appearance", "unit": "", "normal": "Clear"},
        {"name": "Colour", "unit": "", "normal": "Pale Yellow"},
        {"name": "Red Blood Cells", "unit": "/hpf", "normal": "0–3"},
        {"name": "Epithelial Cells", "unit": "/hpf", "normal": "0–5"},
        {"name": "Casts", "unit": "", "normal": "None"},
        {"name": "Crystals", "unit": "", "normal": "None"},
        {"name": "Mucus", "unit": "", "normal": "None"},
        {"name": "Yeast", "unit": "", "normal": "Absent"},
        {"name": "Bacteria", "unit": "", "normal": "None"},
        {"name": "Bile Salt", "unit": "", "normal": "Absent"},
        {"name": "Bile Pigment", "unit": "", "normal": "Absent"},
        {"name": "Parasite", "unit": "", "normal": "None"},
    ],

    "dexa": [
        {"name": "BMI", "unit": "kg/m²", "normal": "18.5–24.9"},
        {"name": "Body Fat", "unit": "%", "normal": "<25(M) / <32(F)"},
        {"name": "Total Fat Mass", "unit": "kg", "normal": "—"},
        {"name": "Visceral Fat Mass", "unit": "g", "normal": "<1000"},
        {"name": "Visceral Fat Level", "unit": "", "normal": "<1.0"},
        {"name": "Android Fat", "unit": "%", "normal": "<35(M) / <45(F)"},
        {"name": "Gynoid Fat", "unit": "%", "normal": "<30(M) / <40(F)"},
        {"name": "Android:Gynoid Ratio", "unit": "", "normal": "<0.8(F) / <1.0(M)"},
        {"name": "Trunk Fat Mass", "unit": "kg", "normal": "—"},
        {"name": "Total Lean Mass", "unit": "kg", "normal": "—"},
        {"name": "Lean Mass", "unit": "kg", "normal": "—"},
        {"name": "Trunk Lean", "unit": "kg", "normal": "—"},
        {"name": "Appendicular Lean Mass", "unit": "kg", "normal": "—"},
        {"name": "RSMI", "unit": "kg/m²", "normal": ">7.26(M) / >5.5(F)"},
        {"name": "Fat Free Mass", "unit": "kg", "normal": "—"},
        {"name": "Mineral Bone Density (T-Score)", "unit": "", "normal": "> -1.0"},
        {"name": "Mineral Bone Density (Z-Score)", "unit": "", "normal": "> -2.0"},
        {"name": "ASMI", "unit": "kg/m²", "normal": ">7.0(M) / >5.5(F)"},
        {"name": "Fat Mass Index", "unit": "kg/m²", "normal": "<9(M) / <13(F)"},
        {"name": "Trunk:Limb Fat Ratio", "unit": "", "normal": "<1.2"},
    ],

    "calcium_score": [
        {"name": "Agatston Score (Total)", "unit": "", "normal": "0"},
        {"name": "LM Agatston Score", "unit": "", "normal": "0"},
        {"name": "LCK Agatston Score", "unit": "", "normal": "0"},
        {"name": "LAD Agatston Score", "unit": "", "normal": "0"},
        {"name": "RCA Agatston Score", "unit": "", "normal": "0"},
        {"name": "LM Calcified Plaques", "unit": "", "normal": "None"},
        {"name": "LCK Calcified Plaques", "unit": "", "normal": "None"},
        {"name": "LAD Calcified Plaques", "unit": "", "normal": "None"},
        {"name": "RCA Calcified Plaques", "unit": "", "normal": "None"},
        {"name": "LM Volume (mm³)", "unit": "mm³", "normal": "0"},
        {"name": "LCK Volume (mm³)", "unit": "mm³", "normal": "0"},
        {"name": "LAD Volume (mm³)", "unit": "mm³", "normal": "0"},
        {"name": "RCA Volume (mm³)", "unit": "mm³", "normal": "0"},
    ],

    "ecg": [
        {"name": "Heart Rate", "unit": "bpm", "normal": "60–100"},
        {"name": "Rhythm", "unit": "", "normal": "Sinus Rhythm"},
        {"name": "PR Interval", "unit": "ms", "normal": "120–200"},
        {"name": "QRS Duration", "unit": "ms", "normal": "70–100"},
        {"name": "QT Interval (QTc)", "unit": "ms", "normal": "<440(M) / <460(F)"},
        {"name": "ST Segment", "unit": "", "normal": "Normal"},
        {"name": "P-Wave Duration", "unit": "ms", "normal": "<120"},
    ],

    "chest_xray": [
        {"name": "Lung Parenchyma", "unit": "", "normal": "Normal"},
        {"name": "Lung Nodules & Masses", "unit": "", "normal": "None"},
        {"name": "Pulmonary Fibrosis", "unit": "", "normal": "Absent"},
        {"name": "COPD / Emphysema", "unit": "", "normal": "Absent"},
        {"name": "Pneumonia / Infection", "unit": "", "normal": "Absent"},
        {"name": "Lung Volume", "unit": "", "normal": "Normal"},
        {"name": "Lung Vasculature", "unit": "", "normal": "Normal"},
        {"name": "Airway Condition", "unit": "", "normal": "Normal"},
        {"name": "Pleural Space", "unit": "", "normal": "Normal"},
        {"name": "Mediastinum & Lymph Nodes", "unit": "", "normal": "Normal"},
        {"name": "Mediastinal Lymph Nodes", "unit": "", "normal": "Normal"},
        {"name": "Pleural cavities", "unit": "", "normal": "Normal"},
    ],

    "usg": [
        # Liver
        {"name": "Liver Parenchyma", "unit": "", "normal": "Normal"},
        {"name": "Liver Outline & Size", "unit": "", "normal": "Normal"},
        {"name": "Liver: Focal changes", "unit": "", "normal": "None"},
        {"name": "Liver: Portal vein", "unit": "", "normal": "Normal"},
        {"name": "Liver: Hepatic veins", "unit": "", "normal": "Normal"},
        {"name": "Intrahepatic biliary Radicals", "unit": "", "normal": "Normal"},
        {"name": "Extrahepatic biliary tree", "unit": "", "normal": "Normal"},
        {"name": "Periportal region", "unit": "", "normal": "Normal"},
        # Gallbladder
        {"name": "Gallbladder size", "unit": "", "normal": "Normal"},
        {"name": "Gallbladder wall", "unit": "", "normal": "Normal"},
        {"name": "Gall Bladder Content", "unit": "", "normal": "Clear"},
        {"name": "Gallbladder Pericholecystic Region", "unit": "", "normal": "Normal"},
        # Bile Ducts
        {"name": "CBD (Common Bile Duct)", "unit": "mm", "normal": "<6"},
        # Pancreas
        {"name": "Pancreas Outline", "unit": "", "normal": "Normal"},
        {"name": "Pancreatic Parenchyma", "unit": "", "normal": "Normal"},
        {"name": "Pancreas Duct", "unit": "", "normal": "Normal"},
        {"name": "Peripancreatic region", "unit": "", "normal": "Normal"},
        # Spleen
        {"name": "Spleen Size & Outline", "unit": "", "normal": "Normal"},
        {"name": "Spleen Parenchyma", "unit": "", "normal": "Normal"},
        {"name": "Splenic Hilum", "unit": "", "normal": "Normal"},
        {"name": "Splenic Vessels", "unit": "", "normal": "Normal"},
        {"name": "Perisplenic Region", "unit": "", "normal": "Normal"},
        # Kidneys
        {"name": "Kidneys Size, outline", "unit": "", "normal": "Normal"},
        {"name": "Cortico-sinus signals", "unit": "", "normal": "Normal"},
        {"name": "Collecting system", "unit": "", "normal": "Normal"},
        {"name": "Renal vessels", "unit": "", "normal": "Normal"},
        {"name": "Peri-renal fat", "unit": "", "normal": "Normal"},
        {"name": "Peri-renal spaces", "unit": "", "normal": "Normal"},
        # Urinary Bladder
        {"name": "Urinary Bladder Walls", "unit": "", "normal": "Normal"},
        {"name": "Urinary Bladder Contour", "unit": "", "normal": "Normal"},
        {"name": "Urinary Bladder Contents", "unit": "", "normal": "Clear"},
        {"name": "Urinary Bladder Perivesical Fat", "unit": "", "normal": "Normal"},
        {"name": "Ureters", "unit": "", "normal": "Normal"},
        # Vascular
        {"name": "Aorta & branches", "unit": "", "normal": "Normal"},
        {"name": "Iliac vessels", "unit": "", "normal": "Normal"},
        {"name": "Mesentric vessels", "unit": "", "normal": "Normal"},
        # Abdominal / Other
        {"name": "Abdominal wall", "unit": "", "normal": "Normal"},
        {"name": "Peritoneum", "unit": "", "normal": "Normal"},
        {"name": "Retroperitoneum", "unit": "", "normal": "Normal"},
        {"name": "Psoas Muscles", "unit": "", "normal": "Normal"},
        {"name": "Bowel", "unit": "", "normal": "Normal"},
        {"name": "Rectum & Rectosigmoid", "unit": "", "normal": "Normal"},
        {"name": "Oesophagus", "unit": "", "normal": "Normal"},
        # Lymph Nodes
        {"name": "Abdominal Lymph nodes", "unit": "", "normal": "Normal"},
        {"name": "Neck Lymphnodes", "unit": "", "normal": "Normal"},
        {"name": "Pelvic lymphnodes", "unit": "", "normal": "Normal"},
        # Neck / Thyroid
        {"name": "Thyroid Volume", "unit": "", "normal": "Normal"},
        {"name": "Thyroid Lesions", "unit": "", "normal": "None"},
        {"name": "Adrenals", "unit": "", "normal": "Normal"},
        # Reproductive
        {"name": "Prostate Size (if male)", "unit": "cc", "normal": "<30", "gender": "M"},
        {"name": "Pelvic cavity", "unit": "", "normal": "Normal"},
        {"name": "Pelvic soft tissues", "unit": "", "normal": "Normal"},
        {"name": "Other pelvic viscera", "unit": "", "normal": "Normal"},
        # Neck / other
        {"name": "Parotid Glands", "unit": "", "normal": "Normal"},
        {"name": "Neck Vessels", "unit": "", "normal": "Normal"},
        # Vascular Assessment
        {"name": "Carotid CIMT", "unit": "mm", "normal": "<0.9"},
        {"name": "Carotid Plaque Score", "unit": "", "normal": "0 / None"},
        # Liver (quantitative)
        {"name": "Liver Steatosis Grade", "unit": "", "normal": "Grade 0"},
        # Kidney (structural)
        {"name": "Renal Cortical Thickness", "unit": "mm", "normal": ">10"},
        # Female-specific imaging
        {"name": "Breast Ultrasound", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Transvaginal Ultrasound", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Endometrial Thickness", "unit": "mm", "normal": "<12", "gender": "F"},
        {"name": "Mammography", "unit": "", "normal": "BIRADS 1", "gender": "F"},
        # Female-specific organs (USG visualisation)
        {"name": "Pelvic Ultrasound", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Uterus", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Ovaries", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Cervix", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Endometrium", "unit": "", "normal": "Normal", "gender": "F"},
        {"name": "Breast", "unit": "", "normal": "Normal", "gender": "F"},
        # Male-specific
        {"name": "Seminal Vesicles", "unit": "", "normal": "Normal", "gender": "M"},
        # Misc abdomen / vascular
        {"name": "Peri-rectal Fat", "unit": "", "normal": "Normal"},
        {"name": "Other major vessels", "unit": "", "normal": "Normal"},
    ],

    "mri": [
        # Larynx / upper airway (MRI neck)
        {"name": "Subglottis", "unit": "", "normal": "Normal"},
        {"name": "Glottis", "unit": "", "normal": "Normal"},
        {"name": "Supra-glottis", "unit": "", "normal": "Normal"},
        # Brain
        {"name": "Brain: Ischemic causes", "unit": "", "normal": "Normal"},
        {"name": "Cerebral white matter", "unit": "", "normal": "Normal"},
        {"name": "White Matter Hyperintensity", "unit": "", "normal": "None"},
        {"name": "Basal Ganglia", "unit": "", "normal": "Normal"},
        {"name": "Ventricles", "unit": "", "normal": "Normal"},
        {"name": "Midbrain", "unit": "", "normal": "Normal"},
        {"name": "Pons", "unit": "", "normal": "Normal"},
        {"name": "Meninges", "unit": "", "normal": "Normal"},
        {"name": "Orbits", "unit": "", "normal": "Normal"},
        {"name": "Optic nerve", "unit": "", "normal": "Normal"},
        {"name": "Globes", "unit": "", "normal": "Normal"},
        {"name": "Lacrimal glands", "unit": "", "normal": "Normal"},
        {"name": "Orbital fat", "unit": "", "normal": "Normal"},
        {"name": "Paranasal Sinuses", "unit": "", "normal": "Normal"},
        {"name": "Maxillary Sinuses", "unit": "", "normal": "Normal"},
        {"name": "Frontal Sinuses", "unit": "", "normal": "Normal"},
        {"name": "Veins", "unit": "", "normal": "Normal"},
        {"name": "Brain: Degenerative", "unit": "", "normal": "Normal"},
        {"name": "Brain: Post-infective", "unit": "", "normal": "Normal"},
        {"name": "Brain: Infective-active", "unit": "", "normal": "Normal"},
        {"name": "Brain: Congenital Causes", "unit": "", "normal": "Normal"},
        {"name": "Brain: Tumours", "unit": "", "normal": "None"},
        # Spine
        {"name": "Spine: Discs", "unit": "", "normal": "Normal"},
        {"name": "Spine Curvature", "unit": "", "normal": "Normal"},
        {"name": "Cord, conus", "unit": "", "normal": "Normal"},
        {"name": "Paravertebral muscles", "unit": "", "normal": "Normal"},
        {"name": "Facets", "unit": "", "normal": "Normal"},
        {"name": "Spine: Ligaments", "unit": "", "normal": "Normal"},
        {"name": "Marrow signals", "unit": "", "normal": "Normal"},
        {"name": "Vertebral body alignment", "unit": "", "normal": "Normal"},
        {"name": "Vertebral bodies", "unit": "", "normal": "Normal"},
        {"name": "Spinal canal", "unit": "", "normal": "Normal"},
        {"name": "Foramina", "unit": "", "normal": "Normal"},
        {"name": "Spine: Signal intensities", "unit": "", "normal": "Normal"},
        # Heart & Vessels (MRI)
        {"name": "Pericardium", "unit": "", "normal": "Normal"},
        {"name": "Heart Health: Degenerative", "unit": "", "normal": "Normal"},
        {"name": "Heart Health: Post-infective", "unit": "", "normal": "Normal"},
        {"name": "Heart Health: Inflammation", "unit": "", "normal": "Normal"},
        {"name": "Heart Health: Tumours", "unit": "", "normal": "None"},
        {"name": "Heart Health: Infective-active", "unit": "", "normal": "Normal"},
        {"name": "Heart Health: Ischemic Causes", "unit": "", "normal": "Normal"},
        {"name": "Heart Health: Congenital Causes", "unit": "", "normal": "Normal"},
        {"name": "IVC and tributaries", "unit": "", "normal": "Normal"},
        {"name": "Aorta and branches", "unit": "", "normal": "Normal"},
        {"name": "Superior venacava", "unit": "", "normal": "Normal"},
        {"name": "Neck Vessels", "unit": "", "normal": "Normal"},
        {"name": "Cardia", "unit": "", "normal": "Normal"},
        # Kidney (MRI)
        {"name": "Kidney & Urinary Health: Degenerative", "unit": "", "normal": "Normal"},
        {"name": "Kidney & Urinary Health: Post-infective", "unit": "", "normal": "Normal"},
        {"name": "Kidney & Urinary Health: Inflammation", "unit": "", "normal": "Normal"},
        {"name": "Kidney & Urinary Health: Congenital Causes", "unit": "", "normal": "Normal"},
        {"name": "Kidney & Urinary Health: Tumours", "unit": "", "normal": "None"},
        {"name": "Kidney & Urinary Health: Infective-active", "unit": "", "normal": "Normal"},
        {"name": "Kidney & Urinary Health: Ischemic Causes", "unit": "", "normal": "Normal"},
        {"name": "Kidney & Urinary Health: Traumatic Issues", "unit": "", "normal": "Normal"},
        # Liver (MRI)
        {"name": "Liver Parenchyma", "unit": "", "normal": "Normal"},
        {"name": "Extrahepatic biliary tree", "unit": "", "normal": "Normal"},
        {"name": "Intrahepatic biliary Radicals", "unit": "", "normal": "Normal"},
        {"name": "Periportal region", "unit": "", "normal": "Normal"},
        {"name": "Liver and Digestive Health: Degenerative", "unit": "", "normal": "Normal"},
        {"name": "Liver and Digestive Health: Post-infective", "unit": "", "normal": "Normal"},
        {"name": "Liver and Digestive Health: Inflammation", "unit": "", "normal": "Normal"},
        {"name": "Liver and Digestive Health: Tumours", "unit": "", "normal": "None"},
        {"name": "Liver and Digestive Health: Infective-active", "unit": "", "normal": "Normal"},
        {"name": "Liver and Digestive Health: Ischemic Causes", "unit": "", "normal": "Normal"},
        {"name": "Liver and Digestive Health: Congenital Causes", "unit": "", "normal": "Normal"},
        # Bone / Muscle (MRI)
        {"name": "Mandible", "unit": "", "normal": "Normal"},
        {"name": "Maxilla", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Degenerative", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Post-infective", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Inflammation", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Traumatic Issues", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Tumours", "unit": "", "normal": "None"},
        {"name": "Bone, Muscle & Joint Health: Infective-active", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Ischemic Causes", "unit": "", "normal": "Normal"},
        {"name": "Bone, Muscle & Joint Health: Congenital Causes", "unit": "", "normal": "Normal"},
        # Endocrine (MRI)
        {"name": "Adrenals", "unit": "", "normal": "Normal"},
        {"name": "Thyroid", "unit": "", "normal": "Normal"},
        {"name": "Endocrine and Metabolic Health: Degenerative", "unit": "", "normal": "Normal"},
        {"name": "Endocrine and Metabolic Health: Post-infective", "unit": "", "normal": "Normal"},
        {"name": "Endocrine and Metabolic Health: Inflammation", "unit": "", "normal": "Normal"},
        {"name": "Endocrine and Metabolic Health: Tumours", "unit": "", "normal": "None"},
        {"name": "Endocrine and Metabolic Health: Infective-active", "unit": "", "normal": "Normal"},
        {"name": "Endocrine and Metabolic Health: Ischemic Causes", "unit": "", "normal": "Normal"},
        {"name": "Endocrine and Metabolic Health: Congenital Causes", "unit": "", "normal": "Normal"},
        # Pelvic structures (MRI) — categorised under Kidney & Urinary Health
        # since the Reproductive Health organ was removed; sex-specific
        # reproductive parameters live under Women's / Men's Health.
        {"name": "Pelvic cavity", "unit": "", "normal": "Normal"},
        {"name": "Pelvic soft tissues", "unit": "", "normal": "Normal"},
        {"name": "Other pelvic viscera", "unit": "", "normal": "Normal"},
        {"name": "Pelvic lymphnodes", "unit": "", "normal": "Normal"},
        # General abdominal (MRI)
        {"name": "Peritoneum", "unit": "", "normal": "Normal"},
        {"name": "Retroperitoneum", "unit": "", "normal": "Normal"},
        {"name": "Psoas Muscles", "unit": "", "normal": "Normal"},
        {"name": "Bowel", "unit": "", "normal": "Normal"},
        {"name": "Oesophagus", "unit": "", "normal": "Normal"},
        {"name": "Parotid Glands", "unit": "", "normal": "Normal"},
        {"name": "Oropharynx", "unit": "", "normal": "Normal"},
        {"name": "Nasopharynx", "unit": "", "normal": "Normal"},
        {"name": "Liver Fat %", "unit": "%", "normal": "<5"},
        {"name": "Prostate Volume", "unit": "cc", "normal": "<30", "gender": "M"},
    ],
    "mammography": [
        {"name": "Right Breast: Mass", "unit": "", "normal": "None"},
        {"name": "Right Breast: Calcifications", "unit": "", "normal": "None"},
        {"name": "Right Breast: Architectural Distortion", "unit": "", "normal": "None"},
        {"name": "Right Breast: Asymmetry", "unit": "", "normal": "None"},
        {"name": "Right Breast: Skin Thickening", "unit": "", "normal": "None"},
        {"name": "Right Breast: Nipple Retraction", "unit": "", "normal": "None"},
        {"name": "Right Breast: Lymphadenopathy", "unit": "", "normal": "None"},
        {"name": "Right Breast: BI-RADS Category", "unit": "", "normal": "0-2"},
        {"name": "Left Breast: Mass", "unit": "", "normal": "None"},
        {"name": "Left Breast: Calcifications", "unit": "", "normal": "None"},
        {"name": "Left Breast: Architectural Distortion", "unit": "", "normal": "None"},
        {"name": "Left Breast: Asymmetry", "unit": "", "normal": "None"},
        {"name": "Left Breast: Skin Thickening", "unit": "", "normal": "None"},
        {"name": "Left Breast: Nipple Retraction", "unit": "", "normal": "None"},
        {"name": "Left Breast: Lymphadenopathy", "unit": "", "normal": "None"},
        {"name": "Left Breast: BI-RADS Category", "unit": "", "normal": "0-2"},
        {"name": "Breast Density", "unit": "", "normal": "A or B"},
        {"name": "Overall Assessment", "unit": "", "normal": "Negative / Benign"},
    ],
}

SECTION_META = {
    "blood":          {"label": "Blood Report",         "icon": "🩸", "has_key_findings": False},
    "urine":          {"label": "Urine Analysis",       "icon": "🧪", "has_key_findings": False},
    "dexa":           {"label": "DEXA Scan",            "icon": "🦴", "has_key_findings": True},
    "calcium_score":  {"label": "Calcium Score Report", "icon": "💛", "has_key_findings": True},
    "ecg":            {"label": "ECG Report",           "icon": "💓", "has_key_findings": False},
    "chest_xray":     {"label": "Chest X-Ray",          "icon": "🫁", "has_key_findings": True},
    "usg":            {"label": "USG Report",           "icon": "🔊", "has_key_findings": True},
    "mri":            {"label": "MRI Report",           "icon": "🧲", "has_key_findings": True},
    "mammography":    {"label": "Mammography",          "icon": "🎀", "has_key_findings": True, "female_only": True},
}


def _gender_norm(gender):
    """Normalise patient gender to 'M', 'F', or None."""
    if not gender:
        return None
    g = str(gender).strip().upper()
    if g in ("M", "MALE"):
        return "M"
    if g in ("F", "FEMALE"):
        return "F"
    return None


def filter_params_by_gender(params, gender):
    """Drop sex-specific params that don't apply to this patient.
    A param without a 'gender' key applies to everyone.
    A param marked gender='M' is dropped for female patients (and vice versa).
    If the patient gender is unknown, all params are returned.
    """
    g = _gender_norm(gender)
    if g is None:
        return list(params)
    return [p for p in params if p.get("gender") in (None, "U", g)]


def get_section_params(section_type, gender=None):
    """Return the parameter list for a section, filtered by patient gender."""
    return filter_params_by_gender(SECTION_PARAMETERS.get(section_type, []), gender)


# ── Paired CBC differentials ────────────────────────────────────────────────
# Same biological measurement reported twice on every CBC: once as a relative
# percentage and once as an absolute count. Both are stored separately (so
# findings, lab CSV, and PDF exports stay complete), but the UI groups them
# into a single row to avoid the appearance of duplicates. The absolute count
# is the clinically actionable value (e.g. neutropenia is defined by ANC, not
# %), so it's the primary; the % is the secondary.
#
# Format: { "<%-form (secondary)>": "<count-form (primary)>", ... }
PARAM_PAIRS = {
    "Basophils":               "Basophils - Count",
    "Eosinophils":             "Eosinophils - Count",
    "Lymphocytes":             "Lymphocytes - Count",
    "Monocytes":               "Monocytes - Count",
    "Neutrophils":             "Neutrophils - Count",
    "Immature Granulocytes %": "Immature Granulocytes",
    "Nucleated RBC %":         "Nucleated RBC",
}
