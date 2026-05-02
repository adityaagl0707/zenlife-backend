"""Maps each of the 15 organ systems to the parameter names that belong to it.

Single source of truth: ZenLife_health_parameters_final.xlsx
(Health Parameters sheet, columns D–R for organ flags).
"""

ORGAN_DEFINITIONS = [
    {
        "organ_name": 'Heart Health',
        "icon": '❤️',
        "display_order": 1,
        "gender": 'U',
        "params": [
            # Coronary calcium / cardiac chamber / ECG
            "agaston score", "agatston score", "st segment", "pericardium",
            "heart rate", "qt interval (qtc)", "rhythm", "qrs duration",
            "pr interval", "p-wave duration",
            # Cardiac risk markers (lipid panel + cardiac proteins + homocysteine)
            "ldl cholesterol", "homocysteine levels", "total cholesterol",
            "hdl cholesterol", "triglycerides", "non-hdl cholesterol", "vldl cholesterol",
            "triglycerides / hdl", "total cholesterol / hdl", "hdl/ldl ratio", "lipoprotein (a)",
            "apolipoprotein b", "ldl/hdl ratio", "apoa1", "nt-probnp",
            # Rollup category headers
            "heart health: degenerative", "heart health: post-infective",
            "heart health: inflammation", "heart health: traumatic issues",
            "heart health: tumours", "heart health: infective-active",
            "heart health: ischemic causes", "heart health: congenital causes",
        ],
    },
    {
        # Merged: Endocrine & Metabolic + Hormonal & Vitality
        "organ_name": 'Endocrine & Hormonal Health',
        "icon": '⚡',
        "display_order": 2,
        "gender": 'U',
        "params": [
            # Metabolic / body composition (canonical home for all DEXA fat/lean)
            "gynoid fat", "visceral fat mass", "visceral fat level",
            "android:gynoid ratio", "android fat", "bmi", "body fat",
            "fat mass index", "fat free mass", "total fat mass",
            "trunk fat mass", "trunk:limb fat ratio",
            # Glucose / insulin axis
            "fasting blood glucose test", "fasting blood sugar", "fasting glucose", "fbs", "glucose",
            "average blood glucose", "hba1c", "insulin", "c-peptide", "homa-ir", "ketone",
            # Thyroid axis
            "tsh", "thyroxine (t4) free", "triiodothyronine (t3) free", "reverse t3",
            "tpo", "anti-tg", "thyroid", "thyroid lesions", "thyroid volume",
            # Adrenal / growth (sex hormones live in Men's / Women's; lipids in Heart;
            # liver-fat in Liver; PSA / E2 / testosterone moved to sex-specific cards)
            "adrenals", "cortisol", "dhea", "igf-1",
            # Rollup labels
            "endocrine and metabolic health: degenerative", "endocrine and metabolic health: post-infective",
            "endocrine and metabolic health: inflammation", "endocrine and metabolic health: traumatic issues",
            "endocrine and metabolic health: tumours", "endocrine and metabolic health: infective-active",
            "endocrine and metabolic health: ischemic causes", "endocrine and metabolic health: congenital causes",
        ],
    },
    {
        "organ_name": 'Liver & Digestive Health',
        "icon": '🫀',
        "display_order": 3,
        "gender": 'U',
        "params": [
            "ast", "total protein", "globulin", "alt",
            "abdominal wall", "ggt", "bilirubin (indirect)", "serum albumin/globulin",
            "albumin", "total bilirubin", "bilirubin direct", "alp",
            "lipase", "amylase", "ast/alt ratio",
            "peritoneum", "cardia", "peri-rectal fat",
            "rectum & rectosigmoid", "perisplenic region", "peripancreatic region",
            "liver parenchyma", "extrahepatic biliary tree", "liver and digestive health: degenerative", "liver and digestive health: traumatic issues",
            "liver and digestive health: post-infective", "liver and digestive health: inflammation", "pancreatic parenchyma", "bowel",
            "splenic hilum", "spleen parenchyma", "spleen size & outline", "pancreas outline",
            "pancreas duct", "gallbladder pericholecystic region", "gall bladder content", "periportal region",
            "hepatic veins", "oesophagus", "parotid glands", "oropharynx",
            "nasopharynx", "liver and digestive health: tumours", "liver and digestive health: infective-active", "liver and digestive health: ischemic causes",
            "liver and digestive health: congenital causes", "intrahepatic biliary radicals", "alk phos", "alkaline phosphatase",
            "pt / inr", "afp", "cea", "liver steatosis grade",
            "liver fat %",
        ],
    },
    {
        # Merged: Brain & Cognitive + Mental & Stress Resilience
        "organ_name": 'Brain & Mental Health',
        "icon": '🧠',
        "display_order": 4,
        "gender": 'U',
        "params": [
            "brain: ischemic causes", "cerebral white matter", "brain: degenerative",
            "brain: post-infective", "brain: infective-active", "brain: congenital causes", "lacrimal glands",
            "orbital fat", "optic nerve", "globes", "orbits",
            "maxillary sinuses", "frontal sinuses", "paranasal sinuses", "veins",
            "meninges", "pons", "midbrain", "ventricles",
            "basal ganglia", "white matter hyperintensity", "brain: tumours",
        ],
    },
    {
        "organ_name": 'Kidney & Urinary Health',
        "icon": '\U0001fad8',
        "display_order": 5,
        "gender": 'U',
        "params": [
            "creatinine", "ua (uric acid)", "urinary bladder walls", "urine albumin/creatinine",
            "blood urea nitrogen (bun)", "sodium", "potassium", "bun / creatinine ratio",
            "chloride", "egfr", "urea/creatinine ratio", "urea (calculated)",
            "urinary microalbumin", "urinary leucocytes", "mucus", "parasite",
            "urine ketone", "epithelial cells", "crystals", "colour",
            "casts", "bile salt", "bile pigment", "ph",
            "urinary protein", "red blood cells", "yeast", "bacteria",
            "urinary bilirubin", "urine blood", "urinary glucose", "creatinine urine",
            "leucocyte esterase", "nitrite", "specific gravity", "appearance",
            "pelvic lymphnodes", "pelvic cavity", "pelvic soft tissues", "other pelvic viscera",
            "retroperitoneum", "urinary bladder contents",
            "ureters", "peri-renal fat", "cortico-sinus signals", "kidney & urinary health: degenerative",
            "kidney & urinary health: post-infective", "kidney & urinary health: inflammation", "kidney & urinary health: congenital causes", "urinary bladder perivesical fat",
            "urinary bladder contour", "peri-renal spaces", "collecting system",
            "kidneys size, outline", "kidney & urinary health: tumours", "kidney & urinary health: infective-active", "kidney & urinary health: ischemic causes",
            "kidney & urinary health: traumatic issues", "cystatin c", "pth", "renal cortical thickness",
        ],
    },
    {
        # Merged: General Health, Blood & Nutrients + Inflammation & Immune Health
        "organ_name": 'Blood, Immunity & Nutrition',
        "icon": '🩸',
        "display_order": 6,
        "gender": 'U',
        "params": [
            # CBC (counts + diff %)
            "rbc", "wbc", "leukocytes", "hemoglobin", "hematocrit", "mcv", "rdw", "mch", "mchc",
            "platelet count", "plateletcrit (pct)", "mpv", "pdw", "plcr", "rdw-sd",
            "nucleated rbc", "nucleated rbc %", "immature granulocytes", "immature granulocytes %",
            "basophils", "basophils - count", "eosinophils", "eosinophils - count",
            "lymphocytes", "lymphocytes - count", "monocytes", "monocytes - count",
            "neutrophils", "neutrophils - count",
            "lymph %", "lymphocyte %", "lymphocyte percentage", "lymphocytes %",
            # Inflammation / immunity markers (clotting markers moved to Vascular)
            "hs-crp", "c reactive protein", "c-reactive protein", "crp",
            "esr", "ige", "neck lymphnodes",
            # Nutrients
            "iron", "iron % saturation", "tibc", "uibc", "ferritin",
            "vitamin a", "vitamin b12", "vitamin d", "vitamin e",
            "folate (b9)", "copper", "zinc", "selenium", "magnesium, rbc",
            "calcium",
            # Tumour markers
            "ldh",
            "general health, blood and nutrients",
        ],
    },
    {
        # Reproductive Health removed — superseded by sex-specific
        # Women's Health and Men's Health cards. All reproductive
        # parameters now live exclusively in those two organs.
        "organ_name": 'Bone, Muscle & Joint Health',
        "icon": '🦴',
        "display_order": 7,
        "gender": 'U',
        "params": [
            "spine: discs", "spine curvature", "mineral bone density(z-score)", "mineral bone density(t-score)",
            "rsmi", "lean mass", "psoas muscles", "mandible",
            "maxilla", "bone, muscle & joint health: post-infective", "bone, muscle & joint health: inflammation", "bone, muscle & joint health: traumatic issues",
            "bone, muscle & joint health: degenerative", "bone, muscle & joint health: tumours", "bone, muscle & joint health: infective-active", "bone, muscle & joint health: ischemic causes",
            "bone, muscle & joint health: congenital causes", "cord, conus", "paravertebral muscles", "facets",
            "spine: ligaments", "marrow signals", "vertebral body alignment", "vertebral bodies",
            "spinal canal", "foramina", "spine: signal intensities",
            "phosphorus", "asmi",
        ],
    },
    {
        "organ_name": 'Lung & Respiratory Health',
        "icon": '🫁',
        "display_order": 8,
        "gender": 'U',
        "params": [
            "pulmonary fibrosis", "copd / emphysema", "lung vasculature",
            "airway condition", "lung volume", "pneumonia / infection", "mediastinum & lymph nodes",
            "pleural space", "lung nodules & masses", "lung parenchyma", "mediastinal lymph nodes",
            "subglottis", "lung and respiratory health: degenerative", "lung and respiratory health: post-infective", "lung and respiratory health: inflammation",
            "lung and respiratory health: congenital causes", "pleural cavities", "glottis", "supra-glottis",
            "lung and respiratory health: tumours", "lung and respiratory health: infective-active", "lung and respiratory health: ischemic causes", "lung and respiratory health: traumatic issues",
        ],
    },
    {
        "organ_name": 'Vascular Health',
        "icon": '🩺',
        "display_order": 9,
        "gender": 'U',
        "params": [
            # Peripheral vessels — coronary calcium lives under Heart Health
            "mesentric vessels", "renal vessels", "iliac vessels", "aorta & branches",
            "superior venacava", "ivc and tributaries", "other major vessels",
            "aorta and branches", "neck vessels", "splenic vessels",
            "carotid cimt", "carotid plaque score",
            # Clotting / thrombosis markers
            "fibrinogen", "d-dimer",
        ],
    },
    # Hormonal & Vitality Health merged into Endocrine & Hormonal Health
    # Mental & Stress Resilience merged into Brain & Mental Health
    # Inflammation & Immune Health merged into Blood, Immunity & Nutrition
    {
        "organ_name": "Women's Health",
        "icon": '🌸',
        "display_order": 10,
        "gender": 'F',
        "params": [
            "estradiol (e2)", "ca-125", "fsh", "lh",
            "progesterone", "prolactin", "amh", "he4",
            "ca 15-3", "dhea-s", "breast ultrasound", "transvaginal ultrasound",
            "endometrial thickness", "mammography", "pap smear", "hpv dna test",
            "pelvic ultrasound", "uterus", "ovaries", "cervix",
            "endometrium", "breast",
        ],
    },
    {
        "organ_name": "Men's Health",
        "icon": '🔵',
        "display_order": 11,
        "gender": 'M',
        "params": [
            "psa", "testosterone", "free testosterone", "shbg",
            "prostate volume", "prostate", "seminal vesicles",
        ],
    },
]

RISK_LABELS = {
    "critical": "Urgent Medical Attention",
    "major": "High Health Risk",
    "minor": "Mild Health Concern",
    "normal": "Healthy and Stable",
}
