name: Auto Update Bridge History

on:
  schedule:
    - cron: '0 */3 * * *' # Запуск кожні 3 години
  workflow_dispatch: # Дозволяє запустити вручну з вкладки Actions

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install requests pandas openpyxl

      - name: Run update script
        env:
          GOOGLE_MAPS_API_KEY: ${{ secrets.GOOGLE_MAPS_API_KEY }}
        run: |
          python update_script.py

      - name: Commit and push changes
        run: |
          git config --global user.name "GitHub Action Bot"
          git config --global user.email "action@github.com"
          git add bridge_history.csv
          git diff --quiet && git diff --staged --quiet || (git commit -m "Auto-update bridge history [skip ci]" && git push)
