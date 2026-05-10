@echo off
:: ============================================================
::  Deploy missing data files to GitHub
::  Run from C:\InvestingWithSPACE\Scout2\
:: ============================================================
cd C:\InvestingWithSPACE\Scout2

echo.
echo Copying data files...

:: Ensure data folder exists
if not exist data mkdir data

:: Copy the 4 files (assumes they are in the Scout2 root folder)
copy /y scout2_holdings.json data\scout2_holdings.json
copy /y scout2_ladders.json  data\scout2_ladders.json
copy /y scout2_prices.json   data\scout2_prices.json
copy /y scout2_layers.json   data\scout2_layers.json

echo.
echo Pushing to GitHub...

git add data\scout2_holdings.json data\scout2_ladders.json data\scout2_prices.json data\scout2_layers.json
git commit -m "Add missing portfolio data files: holdings, ladders, prices, layers"
git push

echo.
echo Done. Verify files live at:
echo https://raw.githubusercontent.com/StacheHistory/scout2-data/main/data/scout2_holdings.json
echo https://raw.githubusercontent.com/StacheHistory/scout2-data/main/data/scout2_ladders.json
echo https://raw.githubusercontent.com/StacheHistory/scout2-data/main/data/scout2_prices.json
echo https://raw.githubusercontent.com/StacheHistory/scout2-data/main/data/scout2_layers.json
echo.
pause
