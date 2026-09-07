#!/usr/bin/env python3
"""Parse election registration PDF tables into CSV files."""

import csv
import os
import re
import pdfplumber


RAW_DIR = "raw"
CSV_DIR = "csv"


def clean_text(text, use_space=False):
    if text is None:
        return ""
    sep = " " if use_space else ""
    return sep.join(text.split("\n")).strip()


def parse_candidate_list(pdf_path, csv_path):
    """Parse X-1 style PDFs: candidate registration lists.
    Columns: 選舉區, 登記日期, 姓名, 推薦之政黨, 備註
    """
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            for row in table:
                if row[0] and str(row[0]).strip() == "選舉區":
                    continue
                cleaned = [
                    clean_text(cell, use_space=(i == 2))
                    for i, cell in enumerate(row)
                ]
                if not cleaned[0] and not cleaned[2]:
                    continue
                rows.append(cleaned[:5])

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["選舉區", "登記日期", "姓名", "推薦之政黨", "備註"])
        writer.writerows(rows)

    print(f"  -> {len(rows)} candidates written to {csv_path}")


def parse_party_summary(pdf_path, csv_path):
    """Parse X-2 style PDFs: party nomination summary tables.
    Has a two-row merged header with variable party columns.
    """
    all_rows = []
    header = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue

            if header is None:
                header_row1 = table[0]
                header_row2 = table[1]

                cols = ["選舉區"]
                for i in range(1, len(header_row2)):
                    cell = clean_text(header_row2[i])
                    if not cell:
                        cell = clean_text(header_row1[i])
                    if cell:
                        cols.append(cell)
                header = cols
                data_start = 2
            else:
                data_start = 0
                if table[0][0] and "選舉區" in str(table[0][0]):
                    data_start = 2

            for row in table[data_start:]:
                cleaned = [clean_text(cell) for cell in row]
                if not cleaned[0]:
                    continue
                all_rows.append(cleaned)

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in all_rows:
            writer.writerow(row[:len(header)])

    print(f"  -> {len(all_rows)} rows written to {csv_path}")


def main():
    os.makedirs(CSV_DIR, exist_ok=True)

    pdf_files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".pdf"))

    for pdf_file in pdf_files:
        pdf_path = os.path.join(RAW_DIR, pdf_file)
        csv_file = re.sub(r"\.pdf$", ".csv", pdf_file)
        csv_path = os.path.join(CSV_DIR, csv_file)

        print(f"Processing: {pdf_file}")

        is_party_summary = "-2" in pdf_file.split("(")[0]

        if is_party_summary:
            parse_party_summary(pdf_path, csv_path)
        else:
            parse_candidate_list(pdf_path, csv_path)


if __name__ == "__main__":
    main()
