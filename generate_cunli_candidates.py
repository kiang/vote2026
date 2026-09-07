#!/usr/bin/env python3
"""Generate per-cunli JSON files with all relevant election candidates."""

import csv
import json
import glob
import os
import re

VOTE2026_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(VOTE2026_DIR, 'csv')
OUTPUT_DIR = os.path.join(VOTE2026_DIR, 'docs', 'candidates')
GEOJSON_DIR = '/home/kiang/public_html/db.cec.gov.tw/data/elections/2026'
TPP_DIR = '/home/kiang/public_html/tainan.olc.tw/docs/p/2026'
AREA_NAMES_PATH = os.path.join(TPP_DIR, 'data', 'area_names.json')
TPP_CANDIDATES_PATH = os.path.join(TPP_DIR, 'data', 'candidates.json')

CSV_FILES = {
    '直轄市長': '1-1(115年直轄市長選舉候選人登記彙總表).csv',
    '直轄市議員': '2-1(115年直轄市議員選舉候選人登記彙總表).csv',
    '縣市長': '3-1(115年縣市長選舉候選人登記彙總表).csv',
    '縣市議員': '4-1(115年縣市議員選舉候選人登記情形彙總表).csv',
    '山地原住民區長': '5-(115年直轄市山地原住民區長選舉候選人登記彙總表).csv',
    '山地原住民區民代表': '6-(115年直轄市山地原住民區民代表選舉候選人登記彙總表).csv',
    '鄉鎮市長': '7-(115年鄉鎮市長選舉候選人登記彙總表).csv',
    '鄉鎮市民代表': '8-(115年鄉鎮市民代表選舉候選人登記彙總表).csv',
    '村里長': '9-(115年村里長選舉候選人登記彙總表).csv',
}

MUNICIPAL_CODES = {'63000', '64000', '65000', '66000', '67000', '68000'}


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def build_geo_mappings():
    """Build mappings from GeoJSON zone files."""
    county_map = {}
    town_map = {}
    cunli_zones = {}
    cunli_info = {}

    for path in glob.glob(os.path.join(GEOJSON_DIR, '*.json')):
        fname = os.path.basename(path)
        zone_code = fname.replace('.json', '')
        fc = load_json(path)
        for feat in fc['features']:
            p = feat['properties']
            cn = p.get('COUNTYNAME', '')
            cc = p.get('COUNTYCODE', '')
            tn = p.get('TOWNNAME', '')
            tc = p.get('TOWNCODE', '')
            vn = p.get('VILLNAME', '')
            vc = p.get('VILLCODE', '')

            if cn and cc:
                county_map[cn] = cc
            if cn and tn and tc:
                town_map[cn + tn] = tc
            if vc:
                cunli_zones.setdefault(vc, set()).add(zone_code)
                cunli_info[vc] = {
                    'countyName': cn, 'countyCode': cc,
                    'townName': tn, 'townCode': tc,
                    'villName': vn,
                }

    return county_map, town_map, cunli_zones, cunli_info


def load_zone_list():
    """Load zone code -> zone name from list.csv."""
    result = {}
    csv_path = os.path.join(GEOJSON_DIR, 'list.csv')
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            result[row['code']] = {
                'name': row['name'],
                'type_name': row['type_name'],
            }
    return result


def load_csv_candidates():
    """Load all candidates from CSV files, grouped by election type."""
    all_candidates = {}
    for election_type, filename in CSV_FILES.items():
        path = os.path.join(CSV_DIR, filename)
        if not os.path.exists(path):
            print(f"WARNING: {path} not found")
            continue
        candidates = []
        with open(path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidates.append({
                    'name': row['姓名'],
                    'party': row['推薦之政黨'],
                    'date': row['登記日期'],
                    'district': row['選舉區'],
                    'note': row.get('備註', ''),
                })
        all_candidates[election_type] = candidates
    return all_candidates


def load_tpp_candidates():
    """Load TPP candidate data with rich info."""
    if not os.path.exists(TPP_CANDIDATES_PATH):
        return []
    data = load_json(TPP_CANDIDATES_PATH)
    return data.get('candidates', [])


def build_district_key(district_text):
    """Normalize a district text for matching."""
    return district_text.replace('臺', '臺').replace('台', '臺').strip()


def build_candidate_index(all_candidates, county_map, town_map):
    """Index candidates by zone-matchable keys.

    Returns:
        mayor_by_county: county_code -> [candidates]   (for 直轄市長/縣市長)
        mayor_by_town: town_code -> [candidates]        (for 鄉鎮市長/山地原住民區長)
        council_by_zone: zone_display_key -> [candidates]  (for 議員/代表)
        village_by_key: (county+town+vill text) -> [candidates]
    """
    mayor_by_county = {}
    mayor_by_town = {}
    council_by_zone = {}
    village_by_key = {}

    for etype, candidates in all_candidates.items():
        for c in candidates:
            dist = build_district_key(c['district'])
            entry = {
                'election': etype,
                'name': c['name'],
                'party': c['party'],
                'date': c['date'],
            }
            if c.get('note'):
                entry['note'] = c['note']

            if etype in ('直轄市長', '縣市長'):
                cc = county_map.get(dist)
                if cc:
                    mayor_by_county.setdefault(cc, []).append(entry)
                else:
                    print(f"WARNING: cannot map county '{dist}'")

            elif etype in ('鄉鎮市長', '山地原住民區長'):
                tc = town_map.get(dist)
                if tc:
                    mayor_by_town.setdefault(tc, []).append(entry)
                else:
                    print(f"WARNING: cannot map town '{dist}'")

            elif etype in ('直轄市議員', '縣市議員', '鄉鎮市民代表', '山地原住民區民代表'):
                council_by_zone.setdefault(dist, []).append(entry)

            elif etype == '村里長':
                village_by_key.setdefault(dist, []).append(entry)

    return mayor_by_county, mayor_by_town, council_by_zone, village_by_key


def zone_code_to_district_text(zone_code, zone_list, cunli_info_entry, county_map):
    """Convert a zone code like T1-63000-01 to CSV district text like '臺北市第1選舉區'."""
    parts = zone_code.split('-')
    prefix = parts[0]
    rev_county = {v: k for k, v in county_map.items()}

    if prefix in ('T1', 'T2', 'T3'):
        county_code = parts[1]
        dist_num = int(parts[2])
        county_name = rev_county.get(county_code, '')
        return f'{county_name}第{dist_num}選舉區'

    elif prefix in ('R1', 'R2'):
        town_code = parts[1]
        dist_num = int(parts[2])
        county_code = town_code[:5]
        county_name = rev_county.get(county_code, '')
        town_name = cunli_info_entry.get('townName', '')
        return f'{county_name}{town_name}第{dist_num}選舉區'

    elif prefix == 'R3':
        town_code = parts[1]
        dist_num = int(parts[2])
        county_code = town_code[:5]
        county_name = rev_county.get(county_code, '')
        town_name = cunli_info_entry.get('townName', '')
        return f'{county_name}{town_name}第{dist_num}選舉區'

    return None


def match_tpp_to_zone(tpp_candidates, county_map, town_map, zone_list):
    """Index TPP candidates by zone matching key (same as CSV district text)."""
    tpp_by_key = {}
    rev_county = {v: k for k, v in county_map.items()}

    for c in tpp_candidates:
        election = c.get('election', '')
        county_name = c.get('countyName', '')
        district = c.get('district', '')

        if election in ('直轄市議員', '縣市議員'):
            m = re.search(r'(\d+)', district)
            if m:
                key = f'{county_name}第{int(m.group(1))}選舉區'
                tpp_by_key.setdefault(key, []).append(c)

        elif election == '鄉鎮市民代表':
            town_name = c.get('townName', '')
            m = re.search(r'(\d+)', district)
            if m:
                key = f'{county_name}{town_name}第{int(m.group(1))}選舉區'
                tpp_by_key.setdefault(key, []).append(c)

        elif election == '直轄市山地原住民區區民代表':
            town_name = c.get('townName', '')
            m = re.search(r'(\d+)', district)
            if m:
                key = f'{county_name}{town_name}第{int(m.group(1))}選舉區'
                tpp_by_key.setdefault(key, []).append(c)

        elif election in ('直轄市市長', '縣市首長'):
            tpp_by_key.setdefault(f'mayor:{county_name}', []).append(c)

        elif election == '鄉鎮市長':
            town_name = c.get('townName', '')
            tpp_by_key.setdefault(f'townmayor:{county_name}{town_name}', []).append(c)

        elif election == '直轄市山地原住民區區長':
            town_name = c.get('townName', '')
            tpp_by_key.setdefault(f'townmayor:{county_name}{town_name}', []).append(c)

        elif election == '村里長':
            vill_name = c.get('villName', '')
            town_name = c.get('townName', '')
            key = f'{county_name}{town_name}{vill_name}'
            tpp_by_key.setdefault(f'village:{key}', []).append(c)

    return tpp_by_key


def enrich_with_tpp(candidates_list, tpp_matches):
    """Merge TPP rich data into candidate entries where names match."""
    tpp_by_name = {c['name']: c for c in tpp_matches}
    for cand in candidates_list:
        tpp = tpp_by_name.get(cand['name'])
        if tpp:
            for field in ('photo', 'facebook', 'instagram', 'youtube',
                          'donate', 'gender', 'education', 'experience',
                          'platform', 'nameEn'):
                val = tpp.get(field)
                if val:
                    cand[field] = val


def generate():
    print("Building geo mappings...")
    county_map, town_map, cunli_zones, cunli_info = build_geo_mappings()
    zone_list = load_zone_list()

    print("Loading CSV candidates...")
    all_candidates = load_csv_candidates()

    print("Loading TPP candidates...")
    tpp_candidates = load_tpp_candidates()
    tpp_by_key = match_tpp_to_zone(tpp_candidates, county_map, town_map, zone_list)

    print("Building candidate index...")
    mayor_by_county, mayor_by_town, council_by_zone, village_by_key = \
        build_candidate_index(all_candidates, county_map, town_map)

    rev_county = {v: k for k, v in county_map.items()}

    print(f"Generating per-cunli JSON files for {len(cunli_info)} cunli...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    count = 0
    for villcode, info in sorted(cunli_info.items()):
        county_code = info['countyCode']
        town_code = info['townCode']
        county_name = info['countyName']
        town_name = info['townName']
        vill_name = info['villName']

        elections = {}

        # 1. Mayor election
        if county_code in MUNICIPAL_CODES:
            etype = '直轄市長'
        else:
            etype = '縣市長'
        mayor_cands = mayor_by_county.get(county_code, [])
        if mayor_cands:
            elections[etype] = {
                'district': county_name,
                'candidates': list(mayor_cands),
            }
            tpp_key = f'mayor:{county_name}'
            if tpp_key in tpp_by_key:
                enrich_with_tpp(elections[etype]['candidates'], tpp_by_key[tpp_key])

        # 2. Town mayor (鄉鎮市長 or 山地原住民區長)
        town_mayor_cands = mayor_by_town.get(town_code, [])
        if town_mayor_cands:
            etype_town = town_mayor_cands[0]['election']
            elections[etype_town] = {
                'district': county_name + town_name,
                'candidates': list(town_mayor_cands),
            }
            tpp_key = f'townmayor:{county_name}{town_name}'
            if tpp_key in tpp_by_key:
                enrich_with_tpp(elections[etype_town]['candidates'], tpp_by_key[tpp_key])

        # 3. Council/representative elections from zone mapping
        zones = cunli_zones.get(villcode, set())
        for zone_code in sorted(zones):
            dist_text = zone_code_to_district_text(zone_code, zone_list, info, county_map)
            if not dist_text:
                continue

            cands = council_by_zone.get(dist_text, [])
            if not cands:
                continue

            prefix = zone_code.split('-')[0]
            if prefix == 'T1':
                if county_code in MUNICIPAL_CODES:
                    etype_c = '直轄市議員'
                else:
                    etype_c = '縣市議員'
            elif prefix == 'T2':
                etype_c = '平地原住民議員'
            elif prefix == 'T3':
                etype_c = '山地原住民議員'
            elif prefix in ('R1', 'R2'):
                etype_c = '鄉鎮市民代表'
            elif prefix == 'R3':
                etype_c = '山地原住民區民代表'
            else:
                continue

            zone_info = zone_list.get(zone_code, {})
            zone_display = zone_info.get('name', dist_text)

            elections[etype_c] = {
                'district': dist_text,
                'zone': zone_code,
                'candidates': list(cands),
            }
            if dist_text in tpp_by_key:
                enrich_with_tpp(elections[etype_c]['candidates'], tpp_by_key[dist_text])

        # 4. Village chief
        vill_key = f'{county_name}{town_name}{vill_name}'
        vill_cands = village_by_key.get(vill_key, [])
        if vill_cands:
            elections['村里長'] = {
                'district': vill_key,
                'candidates': list(vill_cands),
            }
            tpp_vill_key = f'village:{vill_key}'
            if tpp_vill_key in tpp_by_key:
                enrich_with_tpp(elections['村里長']['candidates'], tpp_by_key[tpp_vill_key])

        if not elections:
            continue

        output = {
            'villcode': villcode,
            'countyName': county_name,
            'townName': town_name,
            'villName': vill_name,
            'elections': elections,
        }

        save_json(os.path.join(OUTPUT_DIR, f'{villcode}.json'), output)
        count += 1

    print(f"Done. Generated {count} cunli JSON files in {OUTPUT_DIR}")


if __name__ == '__main__':
    generate()
