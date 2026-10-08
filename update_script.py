import os
import requests
import pandas as pd
from datetime import datetime

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

def main():
    excel_filename = "network_model.xlsx"
    if not os.path.exists(excel_filename):
        print("Excel файл не знайдено!")
        return

    df = pd.read_excel(excel_filename)
    print("Колонки в Excel:", list(df.columns))
    print("Кількість рядків:", len(df))
    print("Скрипт успішно виконав перевірку файлу!")

if __name__ == "__main__":
    main()
