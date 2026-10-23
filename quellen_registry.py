# -*- coding: utf-8 -*-
"""
M.E.R. Regional-Radar - Quellen-Registry (quellen_registry.py)
Zentrale, deduplizierte Sammlung aller amtlichen Primärquellen und Fachportale
für den Nordschwarzwald und die definierten Grenzgürtel.
"""

QUELLEN_REGISTRY = {
    # Gesetzgebung & Übergeordnete Behörden
    "gbl_2025_136": "https://www.baden-wuerttemberg.de/index.php?eID=dumpFile&t=r&r=458865&dl=1&fn=GBl._2025_Nr._136_vom_15.12.2025_signed.pdf&token=9111113aed70c3b2ecb8cea961312387289021b0",
    "rp_baden": "https://rp.baden-wuerttemberg.de/themen/sicherheit/katastrophen-und-zivilschutz/",
    "regionalverband_nordschwarzwald": "https://nordschwarzwald-region.de/",
    "rpk_karlsruhe": "https://rpk.baden-wuerttemberg.de/wir/seiten/abteilungen/",
    "im_kats_novelle": "https://im.baden-wuerttemberg.de/de/service/presse-und-oeffentlichkeitsarbeit/pressemitteilung/pid/novellierung-des-landeskatastrophenschutzgesetzes-im-landtag-beschlossen",
    
    # Klimawandel, Wasser & Umwelt (LUBW / Starkregen)
    "bbk_klimawandel": "https://www.bbk.bund.de/DE/Themen/Klimawandel/klimawandel_node.html",
    "starkregen_hoefen": "https://www.starkregen.de/starkregen/hoefen-an-der-enz",
    "umwelt_bw_extremwasser": "https://um.baden-wuerttemberg.de/de/presse-service/presse/pressemitteilung/pid/land-ruestet-sich-fuer-extremwasserereignisse-1",
    "gwf_wasser": "https://gwf-wasser.de/branche/baden-wuerttemberg-staerkt-hochwasserschutz-und-klimaanpassung/",
    "nagold_starkregen": "https://www.nagold.de/de/Wirtschaft-Bauen/Bauen-Energie/Starkregenrisikomanagement",
    "muehlacker_starkregen": "https://www.muehlacker.de/stadt/aktuelles/meldungen/meldungsarchiv/starkregenmanagement-nordschwarzwald.php",
    "rv_nordschwarzwald_srrm": "https://nordschwarzwald-region.de/projekte/srrm/",
    "lubw_udo_uf": "https://udo.lubw.baden-wuerttemberg.de/public/p/hwrm_hwgk_uf",
    "lubw_kartendienste": "https://www.lubw.baden-wuerttemberg.de/umweltinformationssystem/kartendienste-der-lubw",
    "hvz_pegel": "https://www.hvz.baden-wuerttemberg.de/pegel.html?id=00039",
    "klimapakt": "https://www.agentur-fuer-klimaschutz.de/aktuelles-details/klimaschutzpakt-2025-2026-land-und-landesverbaende-setzen-starkes-zeichen-fuer-klimaschutz-und-klimafolgenanpassung",

    # Nationalpark & Forstwirtschaft
    "nationalpark_sw": "https://www.nationalpark-schwarzwald.de/",
    "nationalpark_standorte": "https://www.nationalpark-schwarzwald.de/nationalpark/organisation/standorte",
    "totholz_fnr": "https://wald.fnr.de/wissen/themendossiers/biodiversitaet/details/totholz-fuer-biodiversitaet-und-klimaschutz",
    "waldwissen_waldbrand": "https://www.waldwissen.net/de/waldwirtschaft/schadensmanagement/waldbrand/totholz-und-waldbrand-in-bw",
    "rpk_natura2000": "https://rpk.baden-wuerttemberg.de/abt5/referat-56-naturschutz-und-landschaftspflege/natura2000/nordschwarzwald-vogelschutzgebiet-7415-441/",

    # Warninfrastruktur (MoWaS, Cell Broadcast, Sirenen)
    "mowas_bbk": "https://www.bbk.bund.de/DE/Warnung-Vorsorge/Warnung-in-Deutschland/MoWaS/mowas_node.html",
    "nina_update": "https://www.bbk.bund.de/SharedDocs/Kurzmeldungen/DE/2025/07/om-07-nina-polizei.html",
    "cell_broadcast_bw": "https://www.baden-wuerttemberg.de/de/service/presse/pressemitteilung/pid/ein-jahr-cell-broadcast-in-baden-wuerttemberg-1",
    "im_sirenen": "https://im.baden-wuerttemberg.de/de/service/presse-und-oeffentlichkeitsarbeit/pressemitteilung/pid/startschuss-fuer-das-sirenenfoerderprogramm",
    "feuerwehr_pforzheim_faq": "https://www.feuerwehr-pforzheim.de/bevoelkerungsschutz/informationen-zum-bevoelkerungsschutz/faq-bevoelkerungsschutz.html",
    "notfalltreffpunkt_bw": "https://www.notfalltreffpunkt-bw.de/",

    # BOS-Digitalfunk & Notfunk (DARC)
    "bdbos_krisenfest": "https://www.bdbos.bund.de/DE/Aufgaben/DigitalfunkBOS/Krisenfestigkeit/krisenfestigkeit_node.html",
    "digitalfunk_pmd2030": "https://digitalfunk.baden-wuerttemberg.de/informationen/digitalfunk-allgemein/modernisierung-digitalfunk-2030",
    "darc_notfunk": "https://www.darc.de/der-club/distrikte/b/notfunk/",
    "relais_db0skf": "https://www.darc.de/der-club/distrikte/p/ortsverbaende/19/relais-db0skf/",
    "relais_db0tfm": "https://www.darc.de/der-club/distrikte/a/ortsverbaende/50/teufelsmuehle/",

    # Bergwacht & Spezialkräfte
    "bergwacht_bilanz": "https://www.bergwacht-schwarzwald.de/aktuelles/neuigkeiten/1009/jahresrueckblick-2025-der-bergwacht-schwarzwald",
    "thwiki_calw": "https://thwiki.org/t=Ortsverband_Calw",
    "bundeswehr_amtshilfe": "https://www.bundeswehr.de/de/organisation/operatives-fuehrungskommando-der-bundeswehr/auftrag-und-aufgaben/amtshilfe",
    
    # Veterinärwesen & PSNV
    "enzkreis_vet": "https://www.enzkreis.de/Landratsamt/%C3%84mter-Dezernate/Dezernat-3-Landwirtschaft-Forsten-%C3%B6ffentliche-Ordnung/Verbraucherschutz-und-Veterin%C3%A4ramt/",
    "calw_vet": "https://www.kreis-calw.de/Service-Verwaltung/Verwaltung/Dezernate-und-Abteilungen/Dezernat-2-Umwelt-Bauen-Naturschutz-Land-und-Forstwirtschaft/Verbraucherschutz-und-Veterin%C3%A4rdienst/",
    "notfallseelsorge_bw": "https://www.nfs-bw.de/landkreise/calw/"
}
