@echo off
cd C:\InvestingWithSPACE\Scout2
py scout2_fetcher_v3.py --days 3
git add scout2_dump.json scout2_dump.txt data\ archive\ index.html
git commit -m "Update Scout-2 feed data"
git push
