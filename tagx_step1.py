import os, re, json
from datetime import datetime

local_root = r"C:\DefconRecht"
skills_root = os.path.join(local_root, "SKILLS")
backup_dir = os.path.join(local_root, "TAG_X_BACKUP")
os.makedirs(backup_dir, exist_ok=True)

all_dirs = sorted([d for d in os.listdir(skills_root) if os.path.isdir(os.path.join(skills_root, d))])
part1_dirs = all_dirs[:13]

md_lines = [
    "# 🚨 TAG-X FLOTTEN-KOMPENDIUM: ALLE 26 SKILLS (ANLEITUNGEN & REFERENCES) 🚨",
    f"* **GENERIERUNGS-ZEITSTEMPEL:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "* **INHALT:** Reines 26-Einheiten-Kompendium (Volltext-Anleitungen SKILL.md & verifizierte References-Zuordnung).",
    "* **HINWEIS:** Das Master-Archiv (Master_Archiv_V23.4_EINSATZ-CHRONIK.md) liegt als separate Datei im selben Ordner TAG_X_BACKUP.\n"
]
json_list = []

for idx, name in enumerate(part1_dirs, start=1):
    s_dir = os.path.join(skills_root, name)
    s_file = os.path.join(s_dir, "SKILL.md")
    r_dir = os.path.join(s_dir, "references")
    
    refs = sorted(os.listdir(r_dir)) if os.path.exists(r_dir) else []
    text = open(s_file, "r", encoding="utf-8").read().strip() if os.path.exists(s_file) else ""
    
    # Mehrfache Leerzeilen glätten
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Exakten Referenzen-Block passend zum echten Ordnerinhalt synchronisieren
    ref_bullets = "\n".join([f"- Datei references/{r}" for r in refs])
    new_ref_section = f"## Referenzen & Wissensdatenbank\nNutze vorrangig die im Skill-Paket enthaltene Wissensbasis:\n{ref_bullets}"
    text = re.sub(r"## Referenzen & Wissensdatenbank[\s\S]*?(?=\n## |\n<ElicitationsGroup|$)", new_ref_section + "\n", text)
    
    with open(s_file, "w", encoding="utf-8") as f:
        f.write(text + "\n")
        
    ref_str = ", ".join(refs) if refs else "Keine Referenzen"
    md_lines.append(
        f"======================================================================\n"
        f"🚢 EINHEIT {idx:02d}/26: {name}\n"
        f"======================================================================\n"
        f"[REFERENZEN IM ORDNER /REFERENCES]: {ref_str}\n\n"
        f"[ANLEITUNG (SKILL.MD)]:\n{text}\n"
    )
    json_list.append({
        "UnitNumber": f"{idx:02d}/26",
        "SkillName": name,
        "References": refs,
        "Instructions": text
    })
    print(f"   [Etappe 1] Einheit {idx:02d}/26 erfasst: {name} ({len(refs)} References)")

with open(os.path.join(backup_dir, "TAG_X_FLOTTE_KOMPLETT.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

with open(os.path.join(backup_dir, "_temp_part1.json"), "w", encoding="utf-8") as f:
    json.dump(json_list, f, ensure_ascii=False, indent=2)

print(">>> [OK] ETAPPE 1 (Einheiten 01 bis 13) erfolgreich in TAG_X_BACKUP geschrieben!")
