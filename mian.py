import pdfplumber
from pdf_annotate import PdfAnnotator, Location, Appearance
import pandas as pd
import numpy as np
import time
import re
import io
import sys


start_time = time.time()
check_version = "developer"
test_times = 1
# Open a PDF file.
if check_version == "developer":
    spec_number = r"acrf_CRAD001Y2301-SPEC"
    pdf_path = r"F:\Novartis\ReaderSpec\files/" + spec_number + '.pdf'
    test_times = test_times + 1
    output_path = r"F:\Novartis\ReaderSpec\result/" + spec_number + "_" + str(test_times) + ".xlsx"
    offset = 1.5
    annotator = PdfAnnotator(pdf_path)
else:
    offset = 1.5

# Read the PDF with pdfplumber.
df = pd.DataFrame()
with pdfplumber.open(pdf_path) as pdf:
    all_pages = pdf.pages
    for curpage in range(len(all_pages)):
        page = all_pages[curpage]
        axis_info_ = page.tmp_find_tables(table_settings={"keep_blank_chars": True})
        counttable = 0
        for table in page.extract_tables(table_settings={"keep_blank_chars": True}):
            axis_info_1 = axis_info_[counttable]
            counttable += 1
            header_index = 0
            variable_column_index = 0
            axis_info = []
            IsNone = [0] * (len(table) * len(table[0]))
            for i in range(len(table)):
                for j in range(len(table[0])):
                    if table[i][j]:
                        table[i][j] = table[i][j].replace("\n", "@@").replace(" ", "_").replace("!", " ")
                    if table[i][j] is None:
                        header_index = i + 1
                        IsNone[j * len(table) + i] = 1
                    if table[i][j] == "Variable":
                        variable_column_index = i + 1
                    if table[i][j] is not None:
                        axis_info.append(axis_info_1[j * len(table) + i - sum(IsNone[:j * len(table) + i])])

            if None in table[0]:
                DatasetName = table[0][0]
                if "(" in DatasetName:
                    DatasetName = DatasetName[: DatasetName.index("(")]
            else:
                DatasetName = "Dataset"

            if variable_column_index != 0:
                variable_column_ = np.array(table[variable_column_index:])[:, 0].repeat(len(table[variable_column_index]))

            columns_name_ = table[header_index] * (len(table) - header_index)

            table = np.array(table).flatten("C").reshape([-1, 1])
            aim_index = np.where(table == None)[0]
            table = np.delete(table, aim_index).reshape([-1, 1])

            if variable_column_index == 0 and DatasetName != "Dataset":
                variable_column = np.array("Codelist").repeat(len(table))
            elif DatasetName == "Dataset":
                variable_column = np.array("DatasetList").repeat(len(table))
            else:
                variable_column = np.concatenate((np.array(" ").repeat(len(table) - len(variable_column_)),
                                 variable_column_), axis=0)

            columns_name = [" "] * (len(table) - len(columns_name_)) + columns_name_

            index_info = np.concatenate((np.array([page.page_number, DatasetName] * len(table)).reshape([-1, 2]),
                          np.array(columns_name).reshape([-1, 1]), variable_column.reshape([-1, 1])), axis=1)

            update_table = np.concatenate((index_info, np.array(table)), axis=1)

            update_table = np.concatenate((update_table, np.array(axis_info)), axis=1)
            df = df.append(pd.DataFrame(update_table))

if check_version == "developer":
    # The path of reader file.
    reader_path = output_path
    # The path of translation file.
    translation_path = r"F:\Novartis\ReaderSpec\result\crad001y2301 spec.xlsx"
    # The path of merged file.
    anotation_path = r"F:\Novartis\ReaderSpec\result/" + spec_number + "_Anotation.xlsx"
else:
    reader_path = " "
    translation_path = " "
    anotation_path = ""


Header = ["Page", "Dataset", "ToColumn", "Variable", "String", "X1", "Y1", "X2", "Y2"]
df.to_excel(output_path, index=True, header=Header)
writer = pd.ExcelWriter(output_path)

# Translation file.
reader_tale_ = pd.read_excel(reader_path)
reader_tale = reader_tale_[(reader_tale_.ToColumn == "Label") & (reader_tale_.Variable != " ")]
reader_tale.iloc[:, -1] = reader_tale.iloc[:, -1] - offset
translation_table = pd.read_excel(translation_path, sheet_name="Variables", usecols=[0, 1, 2, 3])

final_table = pd.merge(reader_tale, translation_table, how="outer", on=["Dataset", "Variable", ])
# Columns name of merged file.
columns_order = ["Page", "ToColumn", "Dataset", "Variable", "Label", "String", "TARGET_LABEL", "X1", "Y1", "X2",
                 "Y2"]

final_table = final_table[columns_order]

# Fine tuning coordinate.
final_table.loc[:, ("X2", "Y2")] = final_table.loc[:, ("X2", "Y2")].copy() - offset
final_table.loc[:, ("X1", "Y1")] = final_table.loc[:, ("X1", "Y1")].copy() + offset

fill_values = {"Page": float('inf'), "TARGET_LABEL": "未被翻译"}
update_table = final_table.fillna(value=fill_values)

if check_version == "developer":
    update_table.to_excel(anotation_path, index=True)
    pd.ExcelWriter(anotation_path)
else:
    update_table["STUDYID"] = "CRAD001Y2301"
    update_table["FORM"] = "INC"
    update_table["PAGE"] = update_table["Page"]
    update_table["SOURCE"] = update_table["String"]
    update_table["TARGET"] = update_table["TARGET_LABEL"]
    update_table["SEQ"] = "1"
    update_table["FLAG"] = "label"
    update_table["STATUS"] = " "
    update_table["LOC"] = " "
    update_table["NOTES"] = " "
    update_table["Y1"] = 792 - update_table["Y1"]
    update_table["Y2"] = 792 - update_table["Y2"]
    update_table["WIDTH"] = update_table["X2"] - update_table["X1"]
    update_table["HEIGHT"] = update_table["Y2"] - update_table["Y1"]
    # Reorder columns.
    Header_obj = ["STUDYID", "PAGE", "FORM", "SEQ", "FLAG", "SOURCE",
                  "TARGET", "STATUS", "X1", "Y1", "X2", "Y2", "WIDTH", "HEIGHT", "LOC", "NOTES"]
    update_table = update_table[Header_obj]

    update_table.to_excel(anotation_path, index=True, header=Header)
    writer = pd.ExcelWriter(anotation_path)





