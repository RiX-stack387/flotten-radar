import os, re, json
from datetime import datetime

local_root = r"C:\DefconRecht"
skills_root = os.path.join(local_root, "SKILLS")
backup_dir = os.path.join(local_root, "TAG_X_BACKUP")

all_dirs = sorted([d for d in os.listdir(skills_root) if os.path.isdir(os.path.join(skills_root, d))])
part2_dirs = all_dirs[13:]

temp_json_path = os.path.join(backup_dir, "_temp_part1.json")
json_list = json.load(open(temp_json_path, "r", encoding="utf-8")) if os.path.exists(temp_json_path) else []
md_lines = []

for idx, name in enumerate(part2_dirs, start=14):
    s_dir = os.path.join(skills_root, name)
    s_file = os.path.join(s_dir, "SKILL.md")
    r_dir = os.path.join(s_dir, "references")
    
    refs = sorted(os.listdir(r_dir)) if os.path.exists(r_dir) else []
    text = open(s_file, "r", encoding="utf-8").read().strip() if os.path.exists(s_file) else ""
    
    text = re.sub(r"\n{3,}", "\n\n", text)
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
    print(f"   [Etappe 2] Einheit {idx:02d}/26 erfasst: {name} ({len(refs)} References)")

md_target = os.path.join(backup_dir, "TAG_X_FLOTTE_KOMPLETT.md")
with open(md_target, "a", encoding="utf-8") as f:
    f.write("\n" + "\n".join(md_lines))

final_json = {
    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "FlottenStaerke": f"{len(json_list)} von 26 Einheiten (Nur Anleitungen & References)",
    "Hinweis": "Master_Archiv_V23.4_EINSATZ-CHRONIK.md liegt als separate Datei im Ordner TAG_X_BACKUP.",
    "Skills": json_list
}

json_target = os.path.join(backup_dir, "TAG_X_FLOTTE_KOMPLETT.json")
with open(json_target, "w", encoding="utf-8") as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)

if os.path.exists(temp_json_path):
    os.remove(temp_json_path)

md_kb = os.path.getsize(md_target) / 1024
json_kb = os.path.getsize(json_target) / 1024
print(f">>> [OK] ETAPPE 2 ABGESCHLOSSEN! Neue Dateigroessen: MD = {md_kb:.1f} KB | JSON = {json_kb:.1f} KB")
